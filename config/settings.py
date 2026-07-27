"""Jarvis Central Configuration Module.

Applies clean validation schemas via Pydantic BaseSettings.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application-wide settings validated at runtime."""

    APP_NAME: str = "Jarvis"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # Server Ports
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    WEBSOCKET_PORT: int = 8001

    # AI Engine Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_MODEL_NAME: str = "gpt-4o"

    # Databases
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "jarvis_db"
    POSTGRES_USER: str = "jarvis_user"
    POSTGRES_PASSWORD: str = "jarvis_password"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Security
    SECRET_KEY: str = "default_insecure_key_must_be_overridden"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = AppSettings()
