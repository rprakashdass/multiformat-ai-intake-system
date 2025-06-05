import json
import re
import os
import sys
from typing import Dict, Any, Tuple
from enum import Enum
import logging

# For file routing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# LLM helper for classification
from utils.llm_helper import generate_output_from_prompt

# logger Configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Format(str, Enum):
    EMAIL = "Email"
    JSON = "JSON"
    PDF = "PDF"
    OTHER = "Other"

class Intent(str, Enum):
    RFQ = "RFQ"
    COMPLAINT = "Complaint"
    INVOICE = "Invoice"
    REGULATION = "Regulation"
    FRAUD = "Fraud Risk"
    OTHER = "Other"

class ClassifierAgent:
    """
    Agent to classify input text into format and business intent.
    Uses LLM via generate_output_from_prompt to classify inputs.
    """

    def __init__(self, model_name: str = "gemini-1.5-flash-latest") -> None:
        self.model_name = model_name
        self.available_formats = [f.value for f in Format]
        self.available_intents = [i.value for i in Intent]

        prompt_file_path = os.path.join(os.path.dirname(__file__), 'classification_prompt.txt')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

    def _extract_json(self, text: str) -> str:
        """
        Extract the first JSON object from the text response.

        Args:
            text (str): Raw LLM output

        Returns:
            str: JSON string extracted or original text if not found
        """
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        logger.warning("No JSON block found in LLM output, returning raw text.")
        return text

    def classify_input(self, raw_input: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Classify the raw input into format and intent.

        Args:
            raw_input (str): Raw text input from user/system

        Returns:
            Tuple[str, str, Dict[str, Any]]: Detected format, intent, and full classification data
        """
        if not raw_input.strip():
            logger.warning("Received empty raw input for classification.")
            return Format.OTHER.value, Intent.OTHER.value, {"error": "Empty input"}

        logger.info("Starting classification for input.")

        formatted_prompt = self.prompt_template.format(
            formats=', '.join(f'"{f}"' for f in self.available_formats),
            intents=', '.join(f'"{i}"' for i in self.available_intents),
            input_data=raw_input.strip()
        )

        classification_raw = generate_output_from_prompt(
            formatted_prompt,
            model_name=self.model_name,
            temperature=0.1,
        )

        try:
            cleaned_output = self._extract_json(classification_raw)
            classification_data = json.loads(cleaned_output)

            classified_format = classification_data.get("format", Format.OTHER.value)
            classified_intent = classification_data.get("intent", Intent.OTHER.value)

            if classified_format not in self.available_formats:
                logger.warning(f"Unknown format '{classified_format}' detected, defaulting to 'Other'.")
                classified_format = Format.OTHER.value

            if classified_intent not in self.available_intents:
                logger.warning(f"Unknown intent '{classified_intent}' detected, defaulting to 'Other'.")
                classified_intent = Intent.OTHER.value

            logger.info(f"Classification result: Format='{classified_format}', Intent='{classified_intent}'")
            return classified_format, classified_intent, classification_data

        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON output from LLM: {e}")
            return Format.OTHER.value, Intent.OTHER.value, {"error": "Malformed JSON", "raw": classification_raw}
        except Exception as e:
            logger.error(f"Unexpected error during classification: {e}")
            return Format.OTHER.value, Intent.OTHER.value, {"error": str(e), "raw": classification_raw}

def run_format_intent_tests(agent: ClassifierAgent):
    test_cases = [
        {
            "title": "Email - Complaint",
            "input": """Subject: Service Delay\n\nHello, I emailed last week about a transaction delay and have not received any response. Please escalate.""",
        },
        {
            "title": "PDF-like - Invoice",
            "input": """
            Invoice Number: INV-2025-101
            Date: 2025-06-01
            Amount Due: $12,500
            Services: Software Development and Consulting
            """,
        },
        {
            "title": "JSON Payload - Fraud Risk",
            "input": json.dumps({
                "event": "suspicious_login",
                "user_id": "abc123",
                "location": "Nigeria",
                "timestamp": "2025-06-01T10:00:00Z"
            }, indent=2),
        },
        {
            "title": "Unstructured Text - Regulation",
            "input": "The policy document discusses compliance with GDPR, HIPAA, and other regulatory frameworks.",
        },
        {
            "title": "Empty Input",
            "input": "",
        }
    ]

    for case in test_cases:
        logger.info(f" {case['title']} ")
        fmt, intent, output = agent.classify_input(case["input"])
        logger.info(f"Detected Format: {fmt}")
        logger.info(f"Detected Intent: {intent}")
        logger.info(f"Details: {json.dumps(output, indent=2)}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    classifier_agent = ClassifierAgent()
    run_format_intent_tests(classifier_agent)