import json
import logging
from typing import Any, Dict

# For file routing
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from memory.memory_manager import MemoryManager

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ActionRouter:
    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager
        logger.info(f"[{self.__class__.__name__}] Initialized with MemoryManager.")

    def _simulate_api_call(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulates an external API call to a given endpoint with a payload."""
        logger.info(f"[{self.__class__.__name__}] Simulating API POST to: {endpoint}")
        logger.debug(f"[{self.__class__.__name__}] Payload: {json.dumps(payload, indent=2)}")

        simulated_response = {
            "status": "success",
            "message": f"Action triggered successfully for {endpoint}",
            "received_payload": payload,
            "timestamp": self.memory.r.time()[0]
        }
        logger.info(f"[{self.__class__.__name__}] Simulated Response: {simulated_response['message']}")
        return simulated_response

    def route_action(self, conversation_id: str, agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Routes and triggers a follow-up action based on the agent's output.
        Logs the triggered action to memory.
        """
        potential_action_type = agent_output.get("potential_action_type")
        action_details: Dict[str, Any] = {
            "action_triggered": "No Action",
            "action_status": "skipped",
            "action_response": {},
            "reason": f"No specific action type suggested or recognized: {potential_action_type}"
        }

        if not potential_action_type:
            logger.warning(f"[{self.__class__.__name__}] No 'potential_action_type' found in agent output for '{conversation_id}'. Skipping action routing.")
            self.memory.save_extracted_data(conversation_id, "ActionRouter_Decision", action_details)
            return action_details

        logger.info(f"[{self.__class__.__name__}] Routing action for '{conversation_id}' based on type: '{potential_action_type}'")

        if potential_action_type == "Escalate to CRM":
            endpoint = "/crm/escalate_issue"
            payload = {
                "conversation_id": conversation_id,
                "issue_summary": agent_output.get("issue_summary", "N/A"),
                "sender_info": agent_output.get("sender_info", agent_output.get("sender_email", "N/A")),
                "urgency": agent_output.get("urgency", "High"),
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "CRM Escalation",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }
        elif potential_action_type == "Log and Close":
            endpoint = "/log_system/close_ticket"
            payload = {
                "conversation_id": conversation_id,
                "summary": agent_output.get("issue_summary", "Routine request/info"),
                "status": "closed_by_automation",
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "Log & Close Ticket",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }
        elif potential_action_type == "Flag for Review":
            endpoint = "/alert_system/flag_review"
            payload = {
                "conversation_id": conversation_id,
                "reason": "Data anomaly or missing critical fields detected",
                "anomalies": agent_output.get("anomalies", []),
                "missing_fields": agent_output.get("missing_fields", []),
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "Manual Review Flag",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }
        elif potential_action_type == "Escalate Fraud Alert":
            endpoint = "/risk_management/fraud_alert"
            payload = {
                "conversation_id": conversation_id,
                "risk_level": "High",
                "details": agent_output.get("anomalies", ["Potential fraud indicators detected."]),
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "Fraud Alert Escalation",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }
        elif potential_action_type == "Review High Value Invoice":
            endpoint = "/finance_system/review_invoice"
            payload = {
                "conversation_id": conversation_id,
                "invoice_id": agent_output.get("document_id", "N/A"),
                "total_amount": agent_output.get("total_amount", "N/A"),
                "currency": agent_output.get("currency", "N/A"),
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "High Value Invoice Review",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }
        elif potential_action_type == "Flag Compliance Document":
            endpoint = "/compliance_system/flag_document"
            payload = {
                "conversation_id": conversation_id,
                "document_id": agent_output.get("document_id", "N/A"),
                "regulatory_keywords": agent_output.get("identified_regulatory_keywords", []),
                "summary": agent_output.get("summary", "Compliance-related document."),
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "Compliance Document Flag",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }
        elif potential_action_type == "Log Document":
            endpoint = "/document_management/log_document"
            payload = {
                "conversation_id": conversation_id,
                "document_id": agent_output.get("document_id", "N/A"),
                "document_type": agent_output.get("document_type", "N/A"),
                "summary": agent_output.get("summary", "General document log."),
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "Log Document",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }
        elif potential_action_type in ["Needs Clarification", "Flag Invalid Input", "Flag LLM Output Error", "Flag Processing Error", "Review Manually", "Flag Unreadable Document"]:
            endpoint = "/manual_review/create_task"
            payload = {
                "conversation_id": conversation_id,
                "reason": potential_action_type,
                "details": agent_output.get("error", "Reason provided by agent."),
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "Manual Review Task",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }
        else:
            logger.warning(f"[{self.__class__.__name__}] Unrecognized action type: '{potential_action_type}'. Defaulting to manual review.")
            endpoint = "/manual_review/create_task"
            payload = {
                "conversation_id": conversation_id,
                "reason": "Unrecognized action type",
                "details": f"Agent suggested: {potential_action_type}. Full agent output: {agent_output}",
                "extracted_data": agent_output
            }
            response = self._simulate_api_call(endpoint, payload)
            action_details = {
                "action_triggered": "Unrecognized Action Manual Review",
                "action_status": response.get("status", "unknown"),
                "action_endpoint": endpoint,
                "action_payload": payload,
                "action_response": response
            }

        self.memory.save_extracted_data(conversation_id, "ActionRouter_Outcome", action_details)
        logger.info(f"[{self.__class__.__name__}] Action '{action_details['action_triggered']}' logged for '{conversation_id}'.")
        return action_details


def run_demos():
    import uuid
    # Initialize MemoryManager
    mem_manager = MemoryManager()
    action_router = ActionRouter(mem_manager)

    logger.info("\n Demo 1: Email Agent Output - Escalation to CRM ")
    conv_id_1 = str(uuid.uuid4())
    email_output_escalation = {
        "sender_name": "Alice Johnson",
        "sender_email": "alice.johnson@example.com",
        "subject": "URGENT: Service outage impacting critical operations",
        "issue_summary": "Customer is experiencing a critical service outage, demands immediate resolution.",
        "urgency": "High",
        "tone": "Escalation",
        "potential_action_type": "Escalate to CRM"
    }
    mem_manager.save_input_metadata(conv_id_1, {"source": "email", "format": "Email", "intent": "Complaint"})
    mem_manager.save_extracted_data(conv_id_1, "EmailAgent", email_output_escalation)
    action_result_1 = action_router.route_action(conv_id_1, email_output_escalation)
    logger.info(f"Action Result 1:\n{json.dumps(action_result_1, indent=2)}")
    logger.info(f"Context after action for {conv_id_1}:\n{json.dumps(mem_manager.get_conversation_context(conv_id_1), indent=2)}")
    mem_manager.clear_context(conv_id_1)

    logger.info("\n Demo 2: JSON Agent Output - Flag for Review (Anomaly) ")
    conv_id_2 = str(uuid.uuid4())
    json_output_anomaly = {
        "document_id": "PROD-XYZ",
        "document_type": "product_info",
        "summary": "Information about a product called Super Gadget.",
        "anomalies": ["Price is negative (-100.00), which is unusual for a product price."],
        "missing_fields": [],
        "potential_action_type": "Flag for Review"
    }
    mem_manager.save_input_metadata(conv_id_2, {"source": "webhook", "format": "JSON", "intent": "Product Update"})
    mem_manager.save_extracted_data(conv_id_2, "JSONAgent", json_output_anomaly)
    action_result_2 = action_router.route_action(conv_id_2, json_output_anomaly)
    logger.info(f"Action Result 2:\n{json.dumps(action_result_2, indent=2)}")
    logger.info(f"Context after action for {conv_id_2}:\n{json.dumps(mem_manager.get_conversation_context(conv_id_2), indent=2)}")
    mem_manager.clear_context(conv_id_2)

    logger.info("\n Demo 3: PDF Agent Output - High Value Invoice Review ")
    conv_id_3 = str(uuid.uuid4())
    pdf_output_high_value = {
        "document_type": "invoice",
        "document_id": "INV-2024-555",
        "summary": "An invoice for software licenses and consulting services.",
        "total_amount": 19000.00,
        "currency": "USD",
        "is_high_value_invoice": True,
        "mentions_regulatory_keywords": False,
        "potential_action_type": "Review High Value Invoice"
    }
    mem_manager.save_input_metadata(conv_id_3, {"source": "upload", "format": "PDF", "intent": "Invoice"})
    mem_manager.save_extracted_data(conv_id_3, "PDFAgent", pdf_output_high_value)
    action_result_3 = action_router.route_action(conv_id_3, pdf_output_high_value)
    logger.info(f"Action Result 3:\n{json.dumps(action_result_3, indent=2)}")
    logger.info(f"Context after action for {conv_id_3}:\n{json.dumps(mem_manager.get_conversation_context(conv_id_3), indent=2)}")
    mem_manager.clear_context(conv_id_3)

    logger.info("\n Demo 4: PDF Agent Output - Flag Compliance Document ")
    conv_id_4 = str(uuid.uuid4())
    pdf_output_compliance = {
        "document_type": "policy",
        "document_id": "Company Privacy Policy - Version 2.1",
        "summary": "Company Privacy Policy outlining data protection.",
        "mentions_regulatory_keywords": True,
        "identified_regulatory_keywords": ["GDPR", "HIPAA"],
        "is_high_value_invoice": False,
        "potential_action_type": "Flag Compliance Document"
    }
    mem_manager.save_input_metadata(conv_id_4, {"source": "upload", "format": "PDF", "intent": "Regulation"})
    mem_manager.save_extracted_data(conv_id_4, "PDFAgent", pdf_output_compliance)
    action_result_4 = action_router.route_action(conv_id_4, pdf_output_compliance)
    logger.info(f"Action Result 4:\n{json.dumps(action_result_4, indent=2)}")
    logger.info(f"Context after action for {conv_id_4}:\n{json.dumps(mem_manager.get_conversation_context(conv_id_4), indent=2)}")
    mem_manager.clear_context(conv_id_4)

    logger.info("\n Demo 5: Email Agent Output - Log and Close ")
    conv_id_5 = str(uuid.uuid4())
    email_output_log = {
        "sender_name": "Bob Smith",
        "sender_email": "bob.smith@example.com",
        "subject": "Question about new feature",
        "issue_summary": "Customer has a question about new feature.",
        "urgency": "Low",
        "tone": "Polite",
        "potential_action_type": "Log and Close"
    }
    mem_manager.save_input_metadata(conv_id_5, {"source": "email", "format": "Email", "intent": "Question"})
    mem_manager.save_extracted_data(conv_id_5, "EmailAgent", email_output_log)
    action_result_5 = action_router.route_action(conv_id_5, email_output_log)
    logger.info(f"Action Result 5:\n{json.dumps(action_result_5, indent=2)}")
    logger.info(f"Context after action for {conv_id_5}:\n{json.dumps(mem_manager.get_conversation_context(conv_id_5), indent=2)}")
    mem_manager.clear_context(conv_id_5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    run_demos()