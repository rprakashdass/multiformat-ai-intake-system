import json
from typing import Dict, Any
import pypdf
import logging

# For file routing
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# LLM helper for classification
from utils.llm_helper import generate_output_from_prompt

# Logger Configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PDFAgent:
    def __init__(self):
        self.model_name = "gemini-1.5-flash-latest"
        self.regulatory_keywords = ["GDPR", "FDA", "HIPAA", "SOX", "PCI DSS", "ISO 27001", "NIST", "CCPA", "DPA"]
        self.document_types = ["invoice", "policy", "report", "other"]

        prompt_file_path = os.path.join(os.path.dirname(__file__), 'pdf_agent_prompt.txt')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
        logger.info(f"PDFAgent: Prompt loaded from {prompt_file_path}")

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Helper method to extract text from a PDF file path using pypdf.
        This method is primarily intended to be called by the FastAPI endpoint in main.py
        when a PDF file is uploaded, before the text is passed to the LLM for processing.
        """
        logger.info(f"started")

        if not os.path.exists(pdf_path):
            logger.error(f"PDFAgent Error: PDF file not found at: {pdf_path}")
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

        text_content = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
            logger.info(f"PDFAgent: Successfully extracted text from {pdf_path}")
            return text_content
        except pypdf.errors.PdfReadError as e:
            logger.error(f"PDFAgent Error: Could not read PDF file {pdf_path}. It might be corrupted or encrypted: {e}")
            raise ValueError(f"Could not read PDF file. It might be corrupted or encrypted: {e}")
        except Exception as e:
            logger.error(f"PDFAgent Error: An unexpected error occurred during PDF text extraction from {pdf_path}: {e}")
            raise Exception(f"An unexpected error occurred during PDF text extraction: {e}")

    def process_pdf_text_content(self, pdf_text_content: str) -> Dict[str, Any]:
        """
        Processes raw text content extracted from a PDF using an LLM.

        Args:
            pdf_text_content (str): The raw text content extracted from a PDF document.

        Returns:
            Dict[str, Any]: A dictionary containing extracted data, flags, and suggested action.
                            Includes error information if extraction fails.
        """

        if not pdf_text_content.strip():
            logger.warning("PDFAgent: Received empty text content for processing.")
            return {
                "error": "Empty or unreadable PDF content provided to agent",
                "potential_action_type": "Flag Unreadable Document"
            }

        formatted_document_types = ', '.join(f'"{d}"' for d in self.document_types)
        formatted_regulatory_keywords = ', '.join(f'"{k}"' for k in self.regulatory_keywords)

        prompt_template = self.prompt_template.format(
            document_types=formatted_document_types,
            regulatory_keywords=formatted_regulatory_keywords,
            pdf_text_content=pdf_text_content.strip(),
        )

        llm_response_raw = generate_output_from_prompt(
            prompt_template,
            model_name=self.model_name,
            temperature=0.2,
        )

        try:
            extracted_data = json.loads(llm_response_raw)
            logger.info("PDFAgent: Data extracted and formatted successfully from text content.")
            required_keys = {"document_type", "document_id", "summary", "potential_action_type"}

            if not required_keys.issubset(extracted_data.keys()):
                raise KeyError("Unexpected response structure: missing required keys.")

            logger.info("PDFAgent: Data extracted and formatted successfully from text content.")
            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"PDFAgent Error: LLM returned malformed JSON. Raw response: '{llm_response_raw}'. Error: {e}")
            return {
                "error": "Malformed JSON from LLM",
                "raw_llm_response": llm_response_raw,
                "details": str(e),
                "potential_action_type": "Flag LLM Output Error"
            }
        except Exception as e:
            logger.error(f"PDFAgent Error: An unexpected error occurred during PDF text processing. Raw response: '{llm_response_raw}'. Error: {e}")
            return {
                "error": f"Unexpected error: {e}",
                "raw_llm_response": llm_response_raw,
                "potential_action_type": "Flag Processing Error"
            }

if __name__ == "__main__":
    pdf_agent = PDFAgent()

    current_dir = os.path.dirname(__file__)
    data_dir = os.path.normpath(os.path.join(current_dir, 'pdf_agent_sample_data'))
    os.makedirs(data_dir, exist_ok=True)

    invoice_pdf_path = os.path.join(data_dir, 'sample_invoice.pdf')
    policy_pdf_path = os.path.join(data_dir, 'sample_policy.pdf')
    report_pdf_path = os.path.join(data_dir, 'sample_report.pdf')
    non_existent_pdf_path = os.path.join(data_dir, 'non_existent.pdf')

    # Test 1
    logging.info("\n Test 1: High-Value Invoice PDF ")
    if os.path.exists(invoice_pdf_path):
        try:
            print("\n1\n")
            extracted_text = pdf_agent._extract_text_from_pdf(invoice_pdf_path)
            print(f"2 Extracted Text from {invoice_pdf_path}:\n{extracted_text}...")
            extracted_output = pdf_agent.process_pdf_text_content(extracted_text)
            print(f"3 Extracted PDF Output:\n {extracted_output}")
            logger.info(f"Extracted PDF Output:\n{json.dumps(extracted_output, indent=2)}")
        except Exception as e:
            logger.error(f"Error processing {invoice_pdf_path}: {e}")
    else:
        logger.warning(f"Skipping Test 1: '{invoice_pdf_path}' not found. Please create it.")
    print()

    # Test 2
    logger.info("\n Test 2: Policy Document with Regulatory Keywords PDF ")
    if os.path.exists(policy_pdf_path):
        try:
            extracted_text = pdf_agent._extract_text_from_pdf(policy_pdf_path)
            extracted_output = pdf_agent.process_pdf_text_content(extracted_text)
            logger.info(f"Extracted PDF Output:\n{json.dumps(extracted_output, indent=2)}")
        except Exception as e:
            logger.error(f"Error processing {policy_pdf_path}: {e}")
    else:
      logger.warning(f"Skipping Test 2: '{policy_pdf_path}' not found. Please create it.")

    # Test 3
    logger.info("\n Test 3: General Report PDF ")
    if os.path.exists(report_pdf_path):
        try:
            extracted_text = pdf_agent._extract_text_from_pdf(report_pdf_path)
            extracted_output = pdf_agent.process_pdf_text_content(extracted_text)
            logger.info(f"Extracted PDF Output:\n{json.dumps(extracted_output, indent=2)}")
        except Exception as e:
            logger.error(f"Error processing {report_pdf_path}: {e}")
    else:
        logger.warning(f"Skipping Test 3: '{report_pdf_path}' not found. Please create it.")

    # Test 4
    logger.info("\n Test 4: Non-existent PDF Path (Error Handling) ")
    try:
        extracted_output = pdf_agent._extract_text_from_pdf(non_existent_pdf_path)
        logger.info(f"Extracted PDF Output (should not reach here):\n{json.dumps(extracted_output, indent=2)}")
    except FileNotFoundError as e:
        logger.warning(f"Caught expected error for non-existent file: {e}")
    except Exception as e:
        logger.error(f"Caught unexpected error: {e}")

    # Test 5
    logger.info("\n Test 5: Empty Text Content (Error Handling for process_pdf_text_content) ")
    empty_output = pdf_agent.process_pdf_text_content("")
    logger.info(f"Extracted PDF Output for empty content:\n{json.dumps(empty_output, indent=2)}")
