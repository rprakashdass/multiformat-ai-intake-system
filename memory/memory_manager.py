# memory/memory_manager.py
import redis
import json
import time
from typing import Dict, Any, Optional

# For file routing
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Get's the Redis connection details
from utils.config import settings

class MemoryManager:
    def __init__(self):
        """
        Initializes the MemoryManager, connecting to Redis.
        Includes a connection test to ensure Redis is reachable.
        """
        self.r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        # Test connection to Redis
        try:
            self.r.ping()
            print(f"[{self.__class__.__name__}] Successfully connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}!")
        except redis.exceptions.ConnectionError as e:
            print(f"[{self.__class__.__name__}] Error: Could not connect to Redis: {e}. Please ensure Redis is running and accessible.")
            exit(1) 

    def _generate_key(self, conversation_id: str, prefix: str) -> str:
        """
        Generates a unique Redis key for storing data related to a specific conversation.
        Keys are structured as 'prefix:conversation_id'.
        """
        return f"{prefix}:{conversation_id}"

    def save_input_metadata(self, conversation_id: str, metadata: Dict[str, Any]):
        """
        Saves initial input metadata for a conversation.
        Metadata includes: source, type, timestamp, classified format, and intent.
        
        Args:
            conversation_id (str): A unique ID for the ongoing conversation/request.
            metadata (Dict[str, Any]): Dictionary containing initial input details.
        """
        key = self._generate_key(conversation_id, "input_metadata")
        print("key is ", key)
        metadata["timestamp"] = time.time()
        self.r.hset(key, mapping=metadata)
        print(f"[{self.__class__.__name__}] Saved input metadata for '{conversation_id}': {metadata}")

    def save_extracted_data(self, conversation_id: str, agent_name: str, data: Dict[str, Any]):
        """
        Saves structured data extracted by a specific agent.
        The data is stored as a JSON string within a hash keyed by conversation_id.
        
        Args:
            conversation_id (str): The unique ID for the conversation.
            agent_name (str): The name of the agent that performed the extraction (e.g., 'EmailParserAgent', 'JSONAgent').
            data (Dict[str, Any]): The extracted structured data.
        """
        key = self._generate_key(conversation_id, "extracted_data")
        # json.dumps(data) -> converts python object to json strings
        self.r.hset(key, agent_name, json.dumps(data))
        print(f"[{self.__class__.__name__}] Saved extracted data from '{agent_name}' for '{conversation_id}': {data}")

    def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """
        Retrieves all stored context (input metadata and extracted data) for a given conversation ID.
        
        Args:
            conversation_id (str): The unique ID for the conversation.
            
        Returns:
            Dict[str, Any]: A dictionary containing 'input_metadata' and 'extracted_data' hashes.
                            'extracted_data' will contain parsed JSON objects for each agent.
        """
        context = {}

        # 1. Getting the input metadata
        input_metadata_key = self._generate_key(conversation_id, "input_metadata")
        input_metadata = self.r.hgetall(input_metadata_key)

        # Convert timestamp back to float if it was stored as a string (decode_responses handles this largely)
        if 'timestamp' in input_metadata:
            input_metadata['timestamp'] = float(input_metadata['timestamp'])
        context["input_metadata"] = input_metadata

        # 2. Get Extracted Data from all agents
        extracted_data_key = self._generate_key(conversation_id, "extracted_data")
        raw_extracted_data = self.r.hgetall(extracted_data_key)

        parsed_extracted_data = {}
        for agent_name, data_str in raw_extracted_data.items():
            try:
                # Attempt to parse the JSON string back into a Python dictionary
                parsed_extracted_data[agent_name] = json.loads(data_str)
            except json.JSONDecodeError:
                # If for some reason it's not valid JSON, store as raw string
                parsed_extracted_data[agent_name] = data_str 
        
        context["extracted_data"] = parsed_extracted_data

        return context

    def clear_context(self, conversation_id: str):
        """
        Deletes all Redis keys associated with a given conversation ID, effectively clearing its context.
        
        Args:
            conversation_id (str): The unique ID of the conversation to clear.
        """
        input_metadata_key = self._generate_key(conversation_id, "input_metadata")
        extracted_data_key = self._generate_key(conversation_id, "extracted_data")
        # DELETE command removes the specified keys from Redis
        self.r.delete(input_metadata_key, extracted_data_key)
        print(f"[{self.__class__.__name__}] Cleared context for '{conversation_id}'.")

# --- Example Usage (for testing the MemoryManager directly) ---
if __name__ == "__main__":
    print("--- Running MemoryManager Test ---")
    mem_manager = MemoryManager()
    
    # Generate a unique ID for this test conversation
    import uuid
    test_conv_id = str(uuid.uuid4())
    print(f"Using test conversation ID: {test_conv_id}")

    print("\n--- 1. Saving Input Metadata ---")
    initial_metadata = {
        "source": "email_webhook",
        "type": "text",
        "format": "Email",
        "intent": "RFQ",
        "original_filename": "rfq_20240529.eml"
    }
    mem_manager.save_input_metadata(test_conv_id, initial_metadata)

    print("\n--- 2. Saving Extracted Data from Email Parser Agent ---")
    email_extracted_data = {
        "sender_name": "Alice Wonderland",
        "sender_email": "alice@example.com",
        "request_subject": "Quote for AI Services",
        "urgency": "High",
        "conversation_id": test_conv_id # Often useful to store in extracted data too
    }
    mem_manager.save_extracted_data(test_conv_id, "EmailParserAgent", email_extracted_data)

    print("\n--- 3. Saving Extracted Data from JSON Agent (simulating a chained request) ---")
    json_extracted_data = {
        "product_id": "FB-PRO-200",
        "quantity_requested": 50,
        "estimated_budget": 15000.00,
        "currency": "USD"
    }
    mem_manager.save_extracted_data(test_conv_id, "JSONAgent", json_extracted_data)

    print("\n--- 4. Retrieving Full Conversation Context ---")
    retrieved_context = mem_manager.get_conversation_context(test_conv_id)
    print(f"Retrieved Context for '{test_conv_id}':\n{json.dumps(retrieved_context, indent=2)}")

    print("\n--- 5. Clearing Context ---")
    mem_manager.clear_context(test_conv_id)

    print("\n--- 6. Verifying Context is Cleared ---")
    empty_context = mem_manager.get_conversation_context(test_conv_id)
    print(f"Context after clearing for '{test_conv_id}':\n{json.dumps(empty_context, indent=2)}")
    if not empty_context["input_metadata"] and not empty_context["extracted_data"]:
        print("Context successfully cleared!")
    else:
        print("Context was NOT fully cleared.")

    print("\n--- MemoryManager Test Complete ---")