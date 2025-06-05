import redis
import json
import time
import logging
from typing import Dict, Any

# For file routing
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings

# logger configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class MemoryManager:
    def __init__(self):
        self.r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        try:
            self.r.ping()
            logger.info(f"Connected to Redis successfully at {settings.REDIS_HOST}:{settings.REDIS_PORT}!")
        except redis.exceptions.ConnectionError as e:
            logger.critical(f"Failed to connect to Redis: {e}. Please ensure Redis is running and accessible.")
            sys.exit(1)

    def _generate_key(self, conversation_id: str, prefix: str) -> str:
        return f"{prefix}:{conversation_id}"

    def save_input_metadata(self, conversation_id: str, metadata: Dict[str, Any]):
        key = self._generate_key(conversation_id, "input_metadata")
        metadata["timestamp"] = time.time()
        self.r.hset(key, mapping=metadata)
        logger.info(f"Input metadata for conversation '{conversation_id}' saved successfully.")
        logger.debug(f"Saved metadata: {metadata}")

    def save_extracted_data(self, conversation_id: str, agent_name: str, data: Dict[str, Any]):
        key = self._generate_key(conversation_id, "extracted_data")
        self.r.hset(key, agent_name, json.dumps(data))
        logger.info(f"Extracted data from '{agent_name}' saved for conversation '{conversation_id}'.")
        logger.debug(f"Saved extracted data: {data}")

    def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        context = {}

        input_metadata_key = self._generate_key(conversation_id, "input_metadata")
        input_metadata = self.r.hgetall(input_metadata_key)

        if 'timestamp' in input_metadata:
            try:
                input_metadata['timestamp'] = float(input_metadata['timestamp'])
            except ValueError:
                logger.warning(f"Timestamp for '{conversation_id}' is malformed: {input_metadata['timestamp']}. Storing as string.")
        context["input_metadata"] = input_metadata

        extracted_data_key = self._generate_key(conversation_id, "extracted_data")
        raw_extracted_data = self.r.hgetall(extracted_data_key)

        parsed_extracted_data = {}
        for agent_name, data_str in raw_extracted_data.items():
            try:
                parsed_extracted_data[agent_name] = json.loads(data_str)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON for agent '{agent_name}' in conversation '{conversation_id}': {e}. Data: '{data_str[:100]}...'")
                parsed_extracted_data[agent_name] = data_str

        context["extracted_data"] = parsed_extracted_data
        logger.info(f"Retrieved context for conversation '{conversation_id}'.")
        logger.debug(f"Retrieved context: {json.dumps(context, indent=2)}")
        return context

    def clear_context(self, conversation_id: str):
        input_metadata_key = self._generate_key(conversation_id, "input_metadata")
        extracted_data_key = self._generate_key(conversation_id, "extracted_data")

        deleted_count = self.r.delete(input_metadata_key, extracted_data_key)
        if deleted_count > 0:
            logger.info(f"Context for conversation '{conversation_id}' has been cleared.")
        else:
            logger.warning(f"No context found to clear for conversation '{conversation_id}'.")


if __name__ == "__main__":
    import uuid
    import sys

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Starting MemoryManager Demo")

    try:
        mem_manager = MemoryManager()
    except SystemExit:
        logger.error("Demo cannot proceed without a Redis connection.")
        sys.exit(1)

    test_conv_id = str(uuid.uuid4())
    logger.info(f"Using a unique ID for this demo: {test_conv_id}")

    logger.info("\n 1. Saving Initial Input Details ")
    initial_metadata = {
        "source": "email_webhook",
        "type": "text",
        "format": "Email",
        "intent": "RFQ",
        "original_filename": "rfq_20240529.eml"
    }
    mem_manager.save_input_metadata(test_conv_id, initial_metadata)

    logger.info("\n 2. Storing Data Extracted by Email Parser ")
    email_extracted_data = {
        "sender_name": "Alice Wonderland",
        "sender_email": "alice@example.com",
        "request_subject": "Quote for AI Services",
        "urgency": "High",
        "conversation_id": test_conv_id
    }
    mem_manager.save_extracted_data(test_conv_id, "EmailParserAgent", email_extracted_data)

    logger.info("\n 3. Storing Data Extracted by JSON Agent (simulating a follow-up) ")
    json_extracted_data = {
        "product_id": "FB-PRO-200",
        "quantity_requested": 50,
        "estimated_budget": 15000.00,
        "currency": "USD"
    }
    mem_manager.save_extracted_data(test_conv_id, "JSONAgent", json_extracted_data)

    logger.info("\n 4. Fetching the Complete Conversation History ")
    retrieved_context = mem_manager.get_conversation_context(test_conv_id)
    logger.info(f"Here's the full context for '{test_conv_id}':\n{json.dumps(retrieved_context, indent=2)}")

    logger.info("\n 5. Clearing the Conversation History ")
    mem_manager.clear_context(test_conv_id)

    logger.info("\n 6. Verifying History is Cleared ")
    empty_context = mem_manager.get_conversation_context(test_conv_id)
    logger.info(f"Context after clearing for '{test_conv_id}':\n{json.dumps(empty_context, indent=2)}")
    if not empty_context["input_metadata"] and not empty_context["extracted_data"]:
        logger.info("Great! The conversation history was successfully cleared.")
    else:
        logger.warning("Oops! The conversation history was NOT fully cleared as expected.")

    logger.info("\n MemoryManager Demo Complete ")