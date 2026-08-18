# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str = ""      # opcional por ahora
    LLM_PROVIDER: str = "openai"
    MODEL_NAME: str = "gpt-4o-mini"
    REDIS_URL: str = "redis://localhost:6379"
    LOG_LEVEL: str = "INFO"
    ENV: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()