import json
from typing import Dict, Any, Tuple

# For file routing
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# LLM helper for classification
from utils.llm_helper import generate_output_from_prompt

class EmailAgent:
    def __init__(self):
        self.model_name = "gemini-2.0-flash"
        self.available_tones = ["Escalation", "Polite", "Threatening", "Neutral", "Informative", "Question"]
        self.available_urgencies = ["High", "Medium", "Low"]

    def process_email(self, raw_email_content: str) -> Dict[str, Any]:
        """
        Processes raw email content to extract structured fields, identify tone,
        and determine urgency using an LLM.

        Args:
            raw_email_content (str): The full raw text content of the email,
                                     including headers and body.

        Returns:
            Dict[str, Any]: A dictionary containing extracted fields, tone, and urgency.
                            Includes error information if extraction fails.
        """
        # Prompt for the LLM
        prompt = f"""
        You are an AI assistant specialized in parsing incoming emails for FlowBit AI.
        Your task is to extract key information, identify the tone, and determine the urgency
        from the provided raw email content.

        You must respond ONLY with a JSON object.

        Here is the required JSON schema for your output:
        ```json
        {{
            "sender_name": "string (e.g., 'John Doe')",
            "sender_email": "string (e.g., 'john.doe@example.com')",
            "subject": "string (the email's subject line)",
            "issue_summary": "string (a concise summary of the main issue or request in the email body)",
            "urgency": "string (select from: {', '.join([f'"{u}"' for u in self.available_urgencies])})",
            "tone": "string (select from: {', '.join([f'"{t}"' for t in self.available_tones])})",
            "potential_action_type": "string (a high-level suggestion for follow-up based on tone/urgency, e.g., 'Escalate to CRM', 'Log and Close', 'Needs Clarification')"
        }}
        ```

        Detailed Instructions:
        1.  Extract `sender_name` and `sender_email` from the 'From:' header. If not explicitly found, try to infer.
        2.  Extract `subject` from the 'Subject:' header.
        3.  Provide a clear and concise `issue_summary` of the email's core message.
        4.  Determine `urgency` based on keywords like "urgent", "ASAP", "critical", "high priority", "immediately", or lack thereof. Default to "Low" if no clear urgency is present.
        5.  Determine the `tone` from the available options. Consider the language, sentiment, and any explicit demands.
        6.  For `potential_action_type`:
            * If `tone` is "Escalation" or "Threatening" AND `urgency` is "High", suggest "Escalate to CRM".
            * If `tone` is "Polite" or "Informative" AND `urgency` is "Low" or "Medium", suggest "Log and Close".
            * If `tone` is "Question" or `urgency` is "Medium" and not an escalation, suggest "Needs Clarification".
            * For any other combination, use "Review Manually".

        Examples  

        Example 1 (Escalation - High Urgency):
        raw_email_content:
        "From: Alice Johnson <alice.johnson@example.com>
        Subject: URGENT: Service outage impacting critical operations
        Dear Support,
        I am writing to express my severe dissatisfaction with the ongoing service outage on our account #XYZ. This has been impacting our critical production systems for the last 4 hours. This is completely unacceptable. We need this resolved IMMEDIATELY. My boss is furious.
        Regards,
        Alice"
        json_output:
        ```json
        {{
            "sender_name": "Alice Johnson",
            "sender_email": "alice.johnson@example.com",
            "subject": "URGENT: Service outage impacting critical operations",
            "issue_summary": "Customer is experiencing a critical service outage on account #XYZ, impacting production systems, and demands immediate resolution.",
            "urgency": "High",
            "tone": "Escalation",
            "potential_action_type": "Escalate to CRM"
        }}
        ```

        Example 2 (Polite - Low Urgency):
        raw_email_content:
        "From: Bob Smith <bob.smith@example.com>
        Subject: Question about new feature
        Hi Team,
        Could you please provide some documentation on the new 'Analytics Dashboard' feature? I'm trying to understand how to generate custom reports. No rush, whenever you have a moment.
        Thanks,
        Bob"
        json_output:
        ```json
        {{
            "sender_name": "Bob Smith",
            "sender_email": "bob.smith@example.com",
            "subject": "Question about new feature",
            "issue_summary": "Customer is requesting documentation for the new 'Analytics Dashboard' feature to learn how to generate custom reports.",
            "urgency": "Low",
            "tone": "Polite",
            "potential_action_type": "Log and Close"
        }}
        ```

        Example 3 (Threatening - High Urgency):
        raw_email_content:
        "From: Legal Dept <legal@example.com>
        Subject: Immediate Legal Action - Breach of Contract
        To whom it may concern,
        This is a formal notice of breach of contract. If the outstanding payment is not received within 24 hours, we will be forced to initiate legal proceedings without further notice. Consider this your final warning.
        Sincerely,
        Legal Counsel"
        json_output:
        ```json
        {{
            "sender_name": "Legal Dept",
            "sender_email": "legal@example.com",
            "subject": "Immediate Legal Action - Breach of Contract",
            "issue_summary": "Formal notice of contract breach due to outstanding payment, threatening immediate legal action if payment not received within 24 hours.",
            "urgency": "High",
            "tone": "Threatening",
            "potential_action_type": "Escalate to CRM"
        }}
        ```

        Example 4 (Informative - Medium Urgency):
        raw_email_content:
        "From: Sarah Connor <sarah.connor@example.com>
        Subject: Software Update Notification - Version 3.1
        Team,
        Just a heads-up that we'll be rolling out software version 3.1 next Tuesday. This update includes minor bug fixes and performance improvements. No action required from users, but please be aware of a potential brief downtime around 3 AM EST.
        Best,
        Sarah"
        json_output:
        ```json
        {{
            "sender_name": "Sarah Connor",
            "sender_email": "sarah.connor@example.com",
            "subject": "Software Update Notification - Version 3.1",
            "issue_summary": "Notification regarding upcoming software version 3.1 rollout next Tuesday, including bug fixes and performance improvements with potential brief downtime.",
            "urgency": "Medium",
            "tone": "Informative",
            "potential_action_type": "Log and Close"
        }}
        ```

          End of Examples  

        Now, process the following raw email content:

        raw_email_content:
        "{raw_email_content}"
        json_output:
        """

        raw_llm_response = generate_output_from_prompt(
            prompt,
            self.model_name
        )

        # error handling
        try:
            extracted_data = json.loads(raw_llm_response)
            required_fields = ["sender_name", "sender_email", "subject", "issue_summary", "urgency", "tone", "potential_action_type"]
            for field in required_fields:
                if field not in extracted_data:
                    raise ValueError(f"Missing required field in LLM response: {field}")

            if extracted_data["tone"] not in self.available_tones:
                extracted_data["tone"] = "Neutral" # Default if LLM hallucinates tone
            if extracted_data["urgency"] not in self.available_urgencies:
                extracted_data["urgency"] = "Low" # Default if LLM hallucinates urgency

            print(f"[Email Agent] Processed\nTone='{extracted_data['tone']}', Urgency='{extracted_data['urgency']}', Action='{extracted_data['potential_action_type']}'")
            
            return extracted_data
        
        except json.JSONDecodeError as e:
            print(f"Email Agent Error: LLM returned malformed JSON: { raw_llm_response}. Error: {e}")
            return {
                "error": "Malformed JSON from LLM",
                "raw_llm_response": raw_llm_response,
                "details": str(e)
            }
        except ValueError as e:
            print(f"Email Agent Error: {e}. Raw response: {raw_llm_response}")
            return {
                "error": str(e),
                "raw_llm_response":  raw_llm_response
            }
        except Exception as e:
            print(f"An unexpected error occurred during email processing: {e}")
            return {
                "error": f"Unexpected error: {e}",
                "raw_llm_response":  raw_llm_response
            }
        
        return None


if __name__ == "__main__":
    email_agent = EmailAgent()

    print("\n  Testing Email - High Urgency Complaint  ")
    email_input_1 = """
    From: customer_support@example.com
    Subject: EXTREMELY URGENT: Major System Failure on Account #CUST123
    Date: Thu, 29 May 2025 14:00:00 +0530

    To whom it may concern,

    Our primary production system is completely down due to your recent update.
    This is costing us thousands of dollars per minute. I demand immediate attention
    and resolution. This is unacceptable! Respond ASAP.

    Best regards,
    Frustrated Client
    """
    extracted_output_1 = email_agent.process_email(email_input_1)
    print(f"Extracted Email Output 1:\n{json.dumps(extracted_output_1, indent=2)}")

    print("\n  Testing Email - Routine Question  ")
    email_input_2 = """
    From: inquiries@flowbit.com
    Subject: Follow-up on recent webinar
    Date: Wed, 28 May 2025 10:15:00 -0400

    Hi Team,

    I attended your webinar yesterday and had a quick question about the data
    integration features you showcased. Is there a simple API for pushing custom data?

    Thanks,
    Curious Learner
    """
    extracted_output_2 = email_agent.process_email(email_input_2)
    print(f"Extracted Email Output 2:\n{json.dumps(extracted_output_2, indent=2)}")

    print("\n  Testing Email - Informative Update  ")
    email_input_3 = """
    From: devops@yourcompany.com
    Subject: Scheduled Maintenance Notification
    Date: Fri, 30 May 2025 08:00:00 +0000

    Dear Users,

    Please be advised of scheduled maintenance on our database servers this
    Saturday from 2 AM to 4 AM UTC. During this period, some services may
    experience brief interruptions. We apologize for any inconvenience.

    Sincerely,
    DevOps Team
    """
    extracted_output_3 = email_agent.process_email(email_input_3)
    print(f"Extracted Email Output 3:\n{json.dumps(extracted_output_3, indent=2)}")

    print("\n  Testing Email - Threatening (Implicit)  ")
    email_input_4 = """
    From: unknown_sender@darkweb.com
    Subject: Your system's security is compromised
    Date: Fri, 30 May 2025 09:00:00 +0000

    We have gained access to your internal network. Expect consequences if our demands are not met.
    A ransom note will follow.
    """

    extracted_output_4 = email_agent.process_email(email_input_4)
    print(f"Extracted Email Output 4:\n{json.dumps(extracted_output_4, indent=2)}")