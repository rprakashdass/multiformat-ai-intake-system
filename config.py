from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(env_path), extra='ignore')
    UPLOAD_DIR: str = "uploads"
    GOOGLE_API_KEY: str

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0


settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

if __name__ == "__main__":
    # Testing settings
    print(f"Google API Key Loaded (first 5 chars): {settings.GOOGLE_API_KEY[:5]}*****")
    print(f"Redis Host: {settings.REDIS_HOST}")
    print(f"Redis Port: {settings.REDIS_PORT}")