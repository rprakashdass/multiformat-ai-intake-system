import redis
import json
import time
from typing import Dict, Any, Optional

from utils.config import settings

class MemoryManager:
    def __init__(self):
        """
        Initializing redis client
        """
        self.r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )

        try:
            self.r.ping()
            print(f"[{self.__class__.__name__}] is Successfully connected to Redis at {settings.REDIS_HOST} on port {settings.REDIS_PORT}")
        except redis.exceptions.ConnectionError as e:
            print(f"[{self.__class__.__name__}] is having error at Redis connection, {e}")
            exit(1)
        
    def _generate_key(self, conversation_id: str, prefix: str) -> str:
        """
        Creates a unique on the combination of prefix and conversation_id
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
        key = self._generate_key(conversation_id, "input_data")
        metadata["timestamp"] = time.time()
        self.r.hset(key, mapping=metadata)
        print(f"[{self.__class__.__name__}] Saved input metadata for '{conversation_id}': {metadata}")

    


if __name__ == "__main__":
    print("Running MemoryManager Test")
    memory_manager = MemoryManager()