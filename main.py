from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import uuid
import os
import shutil

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our components
from memory.memory_manager import MemoryManager
from agents.classifier_agent import ClassifierAgent
from agents.email_agent import EmailAgent
from agents.json_agent import JSONAgent
from agents.pdf_agent import PDFAgent
from action_router.action_router import ActionRouter
from config import settings

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(
    title="Flowbit-AI Intake Agent System",
    description="A multi-agent AI system for contextual decisioning and chained actions based on multi-format input."
)

# Ensure the temporary upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

class Orchestrator:
    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self.classifier_agent = ClassifierAgent()
        self.email_agent = EmailAgent()
        self.json_agent = JSONAgent()
        self.pdf_agent = PDFAgent()
        self.action_router = ActionRouter(memory)
        logger.info("[Orchestrator] All agents and router initialized.")

    async def process_input(self, raw_input_content: str, source_type: str = "upload") -> Dict[str, Any]:
        """
        Orchestrates the end-to-end processing of an input.
        """
        conversation_id = str(uuid.uuid4())
        logger.info(f"\n[Orchestrator] Starting new conversation: {conversation_id}")

        # 1. Log initial input metadata
        self.memory.save_input_metadata(
            conversation_id,
            {"source_type": source_type, "raw_content_preview": raw_input_content[:200]}
        )
        self.memory.save_extracted_data(conversation_id, "RawInput", {"content": raw_input_content})
        logger.info(f"[{conversation_id}] Raw input logged.")

        # 2. Classify format and intent
        classified_format, classified_intent, classification_raw = self.classifier_agent.classify_input(raw_input_content)
        self.memory.save_extracted_data(conversation_id, "ClassifierAgent", {
            "format": classified_format,
            "intent": classified_intent,
            "raw_output": classification_raw
        })
        logger.info(f"[{conversation_id}] Classified: Format='{classified_format}', Intent='{classified_intent}'")

        agent_output: Optional[Dict[str, Any]] = None
        agent_name = "Agent: None"

        # 3. Route to specialized agent based on classified format
        if classified_format == "Email":
            logger.info(f"[{conversation_id}] Routing to Email Agent...")
            agent_output = self.email_agent.process_email(raw_input_content)
            agent_name = "EmailAgent"
        elif classified_format == "JSON":
            logger.info(f"[{conversation_id}] Routing to JSON Agent...")
            agent_output = self.json_agent.extract_and_format(raw_input_content)
            agent_name = "JSONAgent"
        elif classified_format == "PDF":
            logger.info(f"[{conversation_id}] Routing to PDF Agent (with text content)...")
            agent_output = self.pdf_agent.process_pdf_text_content(raw_input_content)
            agent_name = "PDFAgent"
        else:
            logger.info(f"[{conversation_id}] No specialized agent for format: {classified_format}. Skipping specialized agent processing.")
            agent_output = {"status": "skipped_specialized_agent", "message": "No specific agent for this format.", "classified_format": classified_format, "classified_intent": classified_intent}

        if agent_output:
            self.memory.save_extracted_data(conversation_id, agent_name, agent_output)
            logger.info(f"[{conversation_id}] {agent_name} output logged.")
        else:
            logger.info(f"[{conversation_id}] No output from specialized agent.")


        # 4. Route action based on specialized agent output
        if agent_output and "potential_action_type" in agent_output:
            logger.info(f"[{conversation_id}] Routing to Action Router...")
            action_result = self.action_router.route_action(conversation_id, agent_output)
            logger.info(f"[{conversation_id}] Action Router completed.")
        else:
            action_result = {"action_triggered": "No Action", "action_status": "skipped", "reason": "No agent output or potential_action_type found."}
            logger.info(f"[{conversation_id}] No action triggered.")

        # 5. Retrieve and return full conversation context
        final_context = self.memory.get_conversation_context(conversation_id)
        logger.info(f"[Orchestrator] Completed processing for {conversation_id}.")
        return final_context


def get_memory_manager():
    return MemoryManager()

def get_orchestrator(memory_manager: MemoryManager = Depends(get_memory_manager)):
    return Orchestrator(memory_manager)

# FastAPI Endpoints
app.mount("/static", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
async def read_root():
    return RedirectResponse(url="/static/index.html")

@app.post("/process_input", include_in_schema=True)
async def process_input_endpoint(
    file: UploadFile = File(None),
    raw_text_input: Optional[str] = Form(None),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """
    Processes an input (either text or file upload) through the AI agent system.
    """
    input_content = ""
    source_type = "api_text_input"

    if file:
        source_type = "api_file_upload"
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.pdf', '.json', '.txt', '.eml']:
            raise HTTPException(status_code=400, detail="Unsupported file type. Only .pdf, .json, .txt, .eml are supported.")

        file_location = os.path.join(settings.UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Received file: {file.filename}, saved to {file_location}")

        if file_extension == '.pdf':
            try:
                input_content = orchestrator.pdf_agent._extract_text_from_pdf(file_location)
                if not input_content:
                    raise HTTPException(status_code=400, detail="Could not extract text from PDF. It might be an image-only PDF or corrupted.")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"PDF extraction error: {e}")
            finally:
                # Clean up the temporary PDF file
                if os.path.exists(file_location):
                    os.remove(file_location)
        elif file_extension == '.json' or file_extension == '.txt' or file_extension == '.eml':
            # Read as text for JSON, TXT, or EML (email)
            input_content = (await file.read()).decode('utf-8')
        else:
            raise HTTPException(status_code=400, detail="File type not handled for text extraction.")
    elif raw_text_input:
        input_content = raw_text_input
        logger.info(f"Received raw text input: {input_content[:100]}... (truncated for display)")
    else:
        raise HTTPException(status_code=400, detail="No input provided. Please provide either a file or raw_text_input.")

    if not input_content.strip():
        raise HTTPException(status_code=400, detail="Input content is empty after processing.")

    try:
        # Calling the Orchestrator's core processing logic
        result = await orchestrator.process_input(input_content, source_type=source_type)
        return JSONResponse(content=result)
    except Exception as e:
        logger.info(f"Orchestration Error: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error during orchestration", "details": str(e)})