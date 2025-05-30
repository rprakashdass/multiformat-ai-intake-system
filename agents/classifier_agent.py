import json
from typing import Dict, Any, Tuple

# For file routing
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# LLM helper for classification
from utils.llm_helper import generate_text_from_prompt

class ClassifierAgent:
    def __init__(self):
        self.model_name = "gemini-2.0-flash"
        self.available_formats = ["Email", "JSON", "PDF"]
        self.available_intents = ["RFQ", "Complaint", "Invoice", "Regulation", "Fraud Risk", "Other"]

    def classify_input(self, raw_input: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Classifies the raw input's format and intent using an LLM.
        This version includes 'Fraud Risk' as a possible intent.

        Args:
            raw_input (str): The raw text content of the input (email, JSON, or mock PDF text).

        Returns:
            Tuple[str, str, Dict[str, Any]]: A tuple containing the classified format, intent,
                                              and the raw classification output from the LLM.
        """
        #   Prompt Engineering for Classification  
        # We want the LLM to act as a data intake specialist.
        # We need clear instructions and a strict JSON output format.
        # We provide examples (few-shot) within the prompt to guide the LLM.

        prompt = f"""
        You are an intelligent data intake system responsible for classifying incoming raw text data.
        Your task is to analyze the provided raw_input and determine its format and primary business intent.

        Available Formats: {', '.join([f'"{f}"' for f in self.available_formats])}
        Available Intents: {', '.join([f'"{i}"' for i in self.available_intents])}

        You must respond ONLY with a JSON object containing two keys: "format" and "intent".
        If you cannot confidently determine the intent, classify it as "Other".

          Examples  

        Example 1 (Email - RFQ):
        raw_input:
        "Subject: RFQ for new software licenses
        Dear Sir/Madam,
        We are looking for a quote for 50 licenses of 'FlowSuite Pro'. Please provide your best offer by end of day Friday.
        Thanks,
        Alice"
        json_output:
        ```json
        {{
            "format": "Email",
            "intent": "RFQ"
        }}
        ```

        Example 2 (JSON - Invoice):
        raw_input:
        ```json
        {{
            "invoice_id": "INV-2024-001",
            "customer_name": "Acme Corp",
            "total_amount": 1250.75,
            "items": [
                {{"description": "Laptop", "quantity": 1, "price": 1250.75}}
            ]
        }}
        ```
        json_output:
        ```json
        {{
            "format": "JSON",
            "intent": "Invoice"
        }}
        ```

        Example 3 (PDF - Regulation):
        raw_input:
        "CHAPTER 3 – DATA PRIVACY REGULATIONS\\nSection 3.1. General Principles. This regulation outlines the requirements for the processing of personal data within the jurisdiction of BetaCorp..."
        json_output:
        ```json
        {{
            "format": "PDF",
            "intent": "Regulation"
        }}
        ```

        Example 4 (Email - Complaint):
        raw_input:
        "Subject: Urgent Complaint Regarding Service Interruption
        To whom it may concern,
        I am writing to express my severe dissatisfaction with the recent service interruption on our account #XYZ. This has caused significant disruption to our operations.
        Sincerely,
        Bob"
        json_output:
        ```json
        {{
            "format": "Email",
            "intent": "Complaint"
        }}
        ```

        Example 5 (JSON - Fraud Risk):
        raw_input:
        ```json
        {{
            "transaction_id": "TXN-98765",
            "user_id": "user123",
            "amount": 50000.00,
            "currency": "USD",
            "ip_address": "1.2.3.4",
            "location": "Nigeria",
            "previous_transactions": 0,
            "account_age_days": 1
        }}
        ```
        json_output:
        ```json
        {{
            "format": "JSON",
            "intent": "Fraud Risk"
        }}
        ```

        Example 6 (Unclear/Other):
        raw_input:
        "Hello, just wanted to check if you received my previous email about the meeting on Tuesday. Let me know if you need anything."
        json_output:
        ```json
        {{
            "format": "Email",
            "intent": "Other"
        }}
        ```

          End Examples  

        Now, classify the following raw_input:

        raw_input:
        "{raw_input}"
        json_output:
        """

        # Call the LLM helper function
        classification_raw = generate_text_from_prompt(
            prompt,
            model_name=self.model_name,
            temperature=0.1, # Low temperature for classification accuracy
           # json_output=True # Request JSON output
        )

        #   Error Handling for LLM Output  
        try:
            classification_data = json.loads(classification_raw)
            if "format" not in classification_data or "intent" not in classification_data:
                raise ValueError("LLM response missing 'format' or 'intent' keys.")
            
            classified_format = classification_data["format"]
            classified_intent = classification_data["intent"]

            # Validation against our defined lists
            if classified_format not in self.available_formats:
                print(f"Classifier Agent Warning: LLM returned unknown format '{classified_format}'. Defaulting to 'Unknown'.")
                classified_format = "Unknown"
            if classified_intent not in self.available_intents:
                print(f"Classifier Agent Warning: LLM returned unknown intent '{classified_intent}'. Defaulting to 'Other'.")
                classified_intent = "Other"

            print(f"Classifier Agent: Format='{classified_format}', Intent='{classified_intent}'")
            return classified_format, classified_intent, classification_data

        except json.JSONDecodeError as e:
            print(f"Classifier Agent Error: LLM returned malformed JSON: {classification_raw}. Error: {e}")
            return "Unknown", "Unknown", {"error": "Malformed JSON from LLM", "raw_response": classification_raw}
        except ValueError as e:
            print(f"Classifier Agent Error: {e}. Raw response: {classification_raw}")
            return "Unknown", "Unknown", {"error": str(e), "raw_response": classification_raw}
        except Exception as e:
            print(f"An unexpected error occurred during classification: {e}")
            return "Unknown", "Unknown", {"error": f"Unexpected error: {e}", "raw_response": classification_raw}

# Testing the Classifier Agent
if __name__ == "__main__":
    classifier = ClassifierAgent()

    print("\n  Testing Email RFQ  ")
    email_rfq_input = """
    Subject: Request for Quotation - Server Upgrade
    Dear Flowbit AI Team,
    We require a detailed quote for the upgrade of our server infrastructure. Specifically, we are looking for:
    - 2x Dell PowerEdge R750 servers
    - 5x NVIDIA A100 GPUs
    - Installation and setup services
    Please provide your best pricing and estimated delivery times by end of next week.
    Best regards,
    Innovate Solutions
    """
    fmt, intent, raw_output = classifier.classify_input(email_rfq_input)
    print(f"Classified: Format='{fmt}', Intent='{intent}'")
    print(f"Raw LLM Output:\n{json.dumps(raw_output, indent=2)}")

    print("\n  Testing JSON Invoice  ")
    json_invoice_input = """
    {
      "documentType": "Invoice",
      "invoiceNumber": "INV-1002-2024",
      "customer_name": "Acme Corp",
      "total_amount": 1250.75,
      "items": [
        {
          "description": "Enterprise License - Q3 2024",
          "quantity": 1,
          "unitPrice": 5000.00,
          "lineTotal": 5000.00
        }
      ]
    }
    """
    fmt, intent, raw_output = classifier.classify_input(json_invoice_input)
    print(f"Classified: Format='{fmt}', Intent='{intent}'")
    print(f"Raw LLM Output:\n{json.dumps(raw_output, indent=2)}")

    print("\n  Testing Mock PDF Regulation  ")
    pdf_regulation_input = """
    Article 5: Data Minimization
    Personal data shall be adequate, relevant and limited to what is necessary in relation to the purposes for which they are processed. This principle ensures that organizations do not collect more data than is strictly required. Any processing beyond these limits is prohibited.
    """
    fmt, intent, raw_output = classifier.classify_input(pdf_regulation_input)
    print(f"Classified: Format='{fmt}', Intent='{intent}'")
    print(f"Raw LLM Output:\n{json.dumps(raw_output, indent=2)}")

    print("\n  Testing JSON Fraud Risk  ")
    json_fraud_input = """
    {
      "transactionId": "TRX-XYZ-999",
      "userId": "user_high_risk_007",
      "amount": 15000.00,
      "currency": "USD",
      "country": "Nigeria",
      "device": "mobile",
      "loginAttempts": 5,
      "timeSinceLastLogin": "10 minutes"
    }
    """
    fmt, intent, raw_output = classifier.classify_input(json_fraud_input)
    print(f"Classified: Format='{fmt}', Intent='{intent}'")
    print(f"Raw LLM Output:\n{json.dumps(raw_output, indent=2)}")

    print("\n  Testing Unknown Content  ")
    unknown_input = """
    This is just some random text that doesn't clearly indicate a format or intent.
    It talks about the weather and maybe a local event.
    """
    fmt, intent, raw_output = classifier.classify_input(unknown_input)
    print(f"Classified: Format='{fmt}', Intent='{intent}'")
    print(f"Raw LLM Output:\n{json.dumps(raw_output, indent=2)}")