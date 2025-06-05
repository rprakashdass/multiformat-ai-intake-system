import json
import logging
from typing import Dict, Any, Optional

# For file routing
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# LLM helper for classification
from utils.llm_helper import generate_output_from_prompt

# logger Configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class JSONAgent:
    def __init__(self):
        self.model_name = "gemini-2.0-flash"
        # Example FlowBit schema.
        self.flowbit_schema = {
            "document_id": "string (unique identifier for the document)",
            "document_type": "string (e.g., 'invoice', 'order', 'webhook_payload', 'transaction')",
            "sender_info": {
                "name": "string (optional)",
                "email": "string (optional)",
                "organization": "string (optional)"
            },
            "date": "string (YYYY-MM-DD format, e.g., '2024-05-29', optional)",
            "summary": "string (brief summary of the JSON content)",
            "key_values": "dictionary (key-value pairs of important high-level fields)",
            "line_items": [
                {
                    "description": "string",
                    "quantity": "number",
                    "unit_price": "number",
                    "total": "number (calculated)"
                }
            ],
            "total_amount": "number (optional, if applicable to document type)",
            "currency": "string (e.g., 'USD', 'EUR', optional)",
            "required_fields_status": "object (e.g., {'document_id': true, 'document_type': false})",
            "missing_fields": "list of strings (fields from FlowBit schema marked as required but not found or inferred)",
            "anomalies": "list of strings (any unusual, potentially incorrect, or suspicious data points)"
        }
        self.required_flowbit_fields = ["document_id", "document_type", "summary"]

        prompt_file_path = os.path.join(os.path.dirname(__file__), 'json_agent_prompt.txt')
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()
        logger.info(f"JSONAgent: Prompt loaded from {prompt_file_path}")

    def extract_and_format(self, arbitrary_json_str: str) -> Dict[str, Any]:
        """
        Accepts an arbitrary JSON string, extracts and re-formats data to a defined FlowBit schema,
        and identifies issues like missing required fields and anomalies using an LLM.

        Args:
            arbitrary_json_str (str): The raw JSON input as a string.

        Returns:
            Dict[str, Any]: A dictionary representing the extracted and formatted data
                            according to the FlowBit schema, including anomaly/missing field info.
        """
        if not arbitrary_json_str.strip():
            logger.warning("JSON Agent: Received empty raw JSON input. Cannot process.")
            return {
                "error": "Empty JSON input provided",
                "potential_action_type": "Flag Invalid Input"
            }

        try:
            input_data_dict = json.loads(arbitrary_json_str)
            logger.info("JSON Agent: Input JSON parsed successfully.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON Agent Error: Invalid JSON input provided. Error: {e}")
            return {
                "error": "Invalid JSON input",
                "details": str(e),
                "original_input": arbitrary_json_str,
                "potential_action_type": "Flag Invalid Input"
            }

        prompt_template = self.prompt_template.format(
            flowbit_schema_json=json.dumps(self.flowbit_schema, indent=2),
            required_flowbit_fields_json=json.dumps(self.required_flowbit_fields, indent=2),
            arbitrary_input_json=json.dumps(input_data_dict, indent=2)
        )

        llm_response_raw = generate_output_from_prompt(
            prompt_template,
            model_name=self.model_name,
            temperature=0.2
        )

        try:
            extracted_data = json.loads(llm_response_raw)
            return extracted_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON Agent Error: LLM returned malformed JSON: {llm_response_raw}. Error: {e}")
            return {
                "error": "Malformed JSON from LLM",
                "raw_llm_response": llm_response_raw,
                "details": str(e),
                "potential_action_type": "Flag LLM Output Error"
            }
        except Exception as e:
            logger.error(f"An unexpected error occurred during JSON extraction: {e}", exc_info=True) # Added exc_info
            return {
                "error": "Unexpected error during extraction",
                "details": str(e),
                "raw_llm_response": llm_response_raw,
                "potential_action_type": "Flag Processing Error"
            }

if __name__ == "__main__":

    def mock_generate_output_from_prompt(formatted_prompt, model_name, temperature):
        if "Test 1: Webhook Payload" in formatted_prompt:
            return json.dumps({
                "document_id": "WEB-ORD-001",
                "document_type": "webhook_payload",
                "sender_info": {"name": "Alice Smith", "email": "alice.smith@example.com"},
                "date": "2024-05-27",
                "summary": "Order created for Alice Smith with two items, total $131.00 USD.",
                "key_values": {"event": "order_created", "total": 131.00, "currency_code": "USD"},
                "line_items": [
                    {"description": "Wireless Mouse", "quantity": 2, "unit_price": 25.50, "total": 51.00},
                    {"description": "Mechanical Keyboard", "quantity": 1, "unit_price": 80.00, "total": 80.00}
                ],
                "total_amount": 131.00,
                "currency": "USD",
                "required_fields_status": {"document_id": True, "document_type": True, "summary": True},
                "missing_fields": [],
                "anomalies": []
            })
        elif "Test 2: Product Info" in formatted_prompt:
            return json.dumps({
                "document_id": "PROD-XYZ",
                "document_type": "product_info",
                "summary": "Product Super Gadget with negative price.",
                "key_values": {"price": -100.00, "stock_count": 500},
                "required_fields_status": {"document_id": True, "document_type": True, "summary": True},
                "missing_fields": [],
                "anomalies": ["Price is negative (-100.00) for product PROD-XYZ."]
            })
        elif "Test 3: Simple Report" in formatted_prompt:
            return json.dumps({
                "document_id": "inferred_report_id",
                "document_type": "report",
                "summary": "Daily Summary report generated on 2024-05-30 by System A.",
                "key_values": {"report_title": "Daily Summary", "generation_date": "2024-05-30"},
                "required_fields_status": {"document_id": False, "document_type": True, "summary": True},
                "missing_fields": ["document_id"],
                "anomalies": []
            })
        elif "Test 5: High-Risk Transaction" in formatted_prompt:
            return json.dumps({
                "document_id": "TXN-HIGH-RISK-789",
                "document_type": "transaction",
                "summary": "High-value transaction of $250,000 USD from Nigeria by a new user.",
                "key_values": {"amount_usd": 250000.00, "origin_country": "NG"},
                "required_fields_status": {"document_id": True, "document_type": True, "summary": True},
                "missing_fields": [],
                "anomalies": ["High transaction amount ($250,000.00)", "Transaction from high-risk country (NG)", "User has low login count (1) for high-value transaction"]
            })
        else:
            return json.dumps({"error": "Mocked LLM did not recognize prompt.", "raw_input": formatted_prompt})

    from unittest.mock import patch
    with patch('utils.llm_helper.generate_output_from_prompt', side_effect=mock_generate_output_from_prompt):
        json_agent = JSONAgent()

        logging.info("\n Test 1: Webhook Payload (Order) - Expected Clean ")
        webhook_payload_input = """
        {
          "event": "order_created",
          "data": {
            "id": "WEB-ORD-001",
            "customer": {
              "first_name": "Alice",
              "last_name": "Smith",
              "email": "alice.smith@example.com"
            },
            "order_details": {
              "date_placed": "2024-05-27T10:30:00Z",
              "items": [
                {"product_code": "P101", "name": "Wireless Mouse", "qty": 2, "price": 25.50},
                {"product_code": "K202", "name": "Mechanical Keyboard", "qty": 1, "price": 80.00}
              ],
              "total": 131.00,
              "currency_code": "USD"
            },
            "shipping_address": "123 Main St, Anytown"
          }
        }
        """
        extracted_output = json_agent.extract_and_format(webhook_payload_input)
        logger.info(f"Extracted JSON Output:\n{json.dumps(extracted_output, indent=2)}")

        logger.info("\n Test 2: Product Info - Expected Anomaly ")
        product_info_input = """
        {
          "product_id": "PROD-XYZ",
          "product_name": "Super Gadget",
          "price": -100.00,
          "stock_count": 500
        }
        """
        extracted_output = json_agent.extract_and_format(product_info_input)
        logger.info(f"Extracted JSON Output:\n{json.dumps(extracted_output, indent=2)}")

        logger.info("\n Test 3: Simple Report - Expected Missing Fields ")
        simple_report_input = """
        {
          "report_title": "Daily Summary",
          "generation_date": "2024-05-30",
          "generator": "System A"
        }
        """
        extracted_output = json_agent.extract_and_format(simple_report_input)
        logger.info(f"Extracted JSON Output:\n{json.dumps(extracted_output, indent=2)}")

        logger.info("\n Test 4: Malformed JSON Input - Expected Error Handling ")
        malformed_json_input = """
        {
          "name": "Invalid JSON",
          "value": 123
          "status": "error" // Missing comma here
        }
        """
        extracted_output = json_agent.extract_and_format(malformed_json_input)
        logger.info(f"Extracted JSON Output:\n{json.dumps(extracted_output, indent=2)}")

        logger.info("\n Test 5: High-Risk Transaction - Expected Fraud Alert ")
        fraud_transaction_input = """
        {
          "transaction_id": "TXN-HIGH-RISK-789",
          "user_id": "new_user_1234",
          "amount_usd": 250000.00,
          "origin_country": "NG",
          "login_count_24hr": 1,
          "device_type": "mobile",
          "ip": "192.168.1.10"
        }
        """
        extracted_output = json_agent.extract_and_format(fraud_transaction_input)
        logger.info(f"Extracted JSON Output:\n{json.dumps(extracted_output, indent=2)}")