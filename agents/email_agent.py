import json
import logging
from typing import Dict, Any
from enum import Enum
import sys
import os

# For file routing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# LLM helper for classification
from utils.llm_helper import generate_output_from_prompt

# logger Configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class Tone(Enum):
    """Enumeration of supported email tones."""
    ESCALATION = "Escalation"
    POLITE = "Polite"
    THREATENING = "Threatening"
    NEUTRAL = "Neutral"
    INFORMATIVE = "Informative"
    QUESTION = "Question"


class Urgency(Enum):
    """Enumeration of supported urgency levels for emails."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class EmailAgent:
    """
    Agent for processing raw email content to extract structured data,
    including sender info, subject, tone, urgency, and suggested action.

    Uses an LLM with a classification prompt to analyze email content.
    """

    def __init__(self):
        self.model_name = "gemini-2.0-flash"
        self.available_tones = [t.value for t in Tone]
        self.available_urgencies = [u.value for u in Urgency]

        prompt_file_path = os.path.join(os.path.dirname(__file__), 'email_agent_prompt.txt')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

    def process_email(self, raw_email_content: str) -> Dict[str, Any]:
        """
        Process the raw email text to extract key information using an LLM.

        Args:
            raw_email_content (str): The full raw text of the email, including headers and body.

        Returns:
            Dict[str, Any]: Extracted email data including:
                - sender_name
                - sender_email
                - subject
                - issue_summary
                - urgency
                - tone
                - potential_action_type
            Or error details if processing fails.
        """

        prompt = self.prompt_template.format(
            available_urgencies=', '.join(f'"{f}"' for f in self.available_urgencies),
            available_tones=', '.join(f'"{f}"' for f in self.available_tones),
            email_content=raw_email_content.strip(),
        )

        try:
            raw_llm_response = generate_output_from_prompt(
                prompt,
                self.model_name
            )
            print(raw_llm_response)

            extracted_data = json.loads(raw_llm_response)

            required_fields = [
                "sender_name",
                "sender_email",
                "subject",
                "issue_summary",
                "urgency",
                "tone",
                "potential_action_type"
            ]

            for field in required_fields:
                if field not in extracted_data:
                    raise ValueError(f"Missing required field in LLM response: '{field}'")

            if extracted_data["tone"] not in self.available_tones:
                logger.warning(f"Unrecognized tone '{extracted_data['tone']}', defaulting to Neutral")
                extracted_data["tone"] = Tone.NEUTRAL.value
            if extracted_data["urgency"] not in self.available_urgencies:
                logger.warning(f"Unrecognized urgency '{extracted_data['urgency']}', defaulting to Low")
                extracted_data["urgency"] = Urgency.LOW.value

            logger.info(f"Processed email: Tone='{extracted_data['tone']}', "
                             f"Urgency='{extracted_data['urgency']}', "
                             f"Action='{extracted_data['potential_action_type']}'")

            return extracted_data

        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON from LLM: Error: {e}")
            return {
                "error": "Malformed JSON from LLM",
                "raw_llm_response": raw_llm_response,
                "details": str(e)
            }

        except ValueError as e:
            logger.error(f"{e}. Raw response: {raw_llm_response}")
            return {
                "error": str(e),
                "raw_llm_response": raw_llm_response
            }

        except Exception as e:
            logger.exception(f"Unexpected error during processing: {e}")
            return {
                "error": f"Unexpected error: {e}",
                "raw_llm_response": raw_llm_response
            }


if __name__ == "__main__":
    email_agent = EmailAgent()

    test_emails = {
        "High Urgency Complaint": """
            From: customer_support@example.com
            Subject: EXTREMELY URGENT: Major System Failure on Account #CUST123
            Date: Thu, 29 May 2025 14:00:00 +0530

            To whom it may concern,

            Our primary production system is completely down due to your recent update.
            This is costing us thousands of dollars per minute. I demand immediate attention
            and resolution. This is unacceptable! Respond ASAP.

            Best regards,
            Frustrated Client
        """,

        "Routine Question": """
            From: inquiries@flowbit.com
            Subject: Follow-up on recent webinar
            Date: Wed, 28 May 2025 10:15:00 -0400

            Hi Team,

            I attended your webinar yesterday and had a quick question about the data
            integration features you showcased. Is there a simple API for pushing custom data?

            Thanks,
            Curious Learner
        """,

        "Informative Update": """
            From: devops@yourcompany.com
            Subject: Scheduled Maintenance Notification
            Date: Fri, 30 May 2025 08:00:00 +0000

            Dear Users,

            Please be advised of scheduled maintenance on our database servers this
            Saturday from 2 AM to 4 AM UTC. During this period, some services may
            experience brief interruptions. We apologize for any inconvenience.

            Sincerely,
            DevOps Team
        """,

        "Threatening (Implicit)": """
            From: unknown_sender@darkweb.com
            Subject: Your system's security is compromised
            Date: Fri, 30 May 2025 09:00:00 +0000

            We have gained access to your internal network. Expect consequences if our demands are not met.
            A ransom note will follow.
        """
    }

    for test_name, email_text in test_emails.items():
        logging.info(f"\nTesting Email - {test_name}")
        result = email_agent.process_email(email_text)
        logging.info(json.dumps(result, indent=2))