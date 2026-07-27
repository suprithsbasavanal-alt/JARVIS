"""Centralized Modular Configuration Management for Jarvis.

Manages environment variables, feature flags, API settings, model settings,
development/production modes, logging options, security parameters, and application constants.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from config.constants import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_VECTOR_COLLECTION,
    DEFAULT_EMBEDDING_DIMENSION,
)


class EnvironmentMode(str, Enum):
    """Execution environment mode enums."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class FeatureFlagsConfig(BaseModel):
    """Dynamic feature toggle flags for modular components."""
    enable_voice: bool = Field(default=True, description="Enable STT/TTS voice pipeline")
    enable_sandbox: bool = Field(default=True, description="Enable code execution isolation sandbox")
    enable_rag: bool = Field(default=True, description="Enable vector semantic retrieval (RAG)")
    enable_telemetry: bool = Field(default=True, description="Enable OpenTelemetry tracing and metrics")
    enable_guardrails: bool = Field(default=True, description="Enable prompt injection and safety guardrails")
    enable_background_automation: bool = Field(default=True, description="Enable DAG workflow automation runner")
    enable_websocket_streaming: bool = Field(default=True, description="Enable WebSocket real-time gateway")


class APISettingsConfig(BaseModel):
    """API Gateway and Web Server configurations."""
    host: str = Field(default="0.0.0.0", description="API listener IP host")
    port: int = Field(default=8000, description="HTTP REST API port")
    websocket_port: int = Field(default=8001, description="WebSocket streaming port")
    grpc_port: int = Field(default=50051, description="gRPC microservice port")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins list")
    rate_limit_per_minute: int = Field(default=120, description="Max API requests per minute per IP")
    request_timeout_seconds: int = Field(default=30, description="Global API request timeout in seconds")


class ModelSettingsConfig(BaseModel):
    """AI Engine LLM provider and inference defaults."""
    default_provider: str = Field(default="openai", description="Primary model vendor (openai, anthropic, gemini, local)")
    fallback_provider: str = Field(default="gemini", description="Fallback vendor on provider outage")
    default_model_name: str = Field(default="gpt-4o", description="Default LLM model identifier")
    embedding_model_name: str = Field(default="text-embedding-3-small", description="Default text embedding model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Inference sampling temperature")
    max_tokens: int = Field(default=4096, gt=0, description="Maximum token generation limit")
    stream_by_default: bool = Field(default=True, description="Stream token responses asynchronously by default")
    openai_api_key: Optional[SecretStr] = Field(default=None, description="OpenAI API Key")
    anthropic_api_key: Optional[SecretStr] = Field(default=None, description="Anthropic API Key")
    gemini_api_key: Optional[SecretStr] = Field(default=None, description="Google Gemini API Key")


class LoggingConfig(BaseModel):
    """Structured Logging and Diagnostics Configuration."""
    level: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    use_json_format: bool = Field(default=False, description="Enable structured JSON log format")
    log_to_file: bool = Field(default=True, description="Enable log file persistence")
    log_file_path: str = Field(default="logs/jarvis.log", description="Log file destination path")
    max_bytes: int = Field(default=10485760, description="Log file rotation threshold in bytes (10MB)")
    backup_count: int = Field(default=5, description="Number of rotated log backups to retain")


class SecurityConfig(BaseModel):
    """Security, Authentication, and Guardrail Configuration."""
    secret_key: SecretStr = Field(
        default=SecretStr("jarvis_default_dev_secret_key_change_in_production_32_bytes"),
        description="JWT signature and payload encryption secret key"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT token signing algorithm")
    access_token_expire_minutes: int = Field(default=60, description="JWT token validity duration in minutes")
    sandbox_execution_timeout_seconds: int = Field(default=30, description="Code execution sandbox isolation timeout")
    max_payload_size_mb: int = Field(default=10, description="Maximum allowed API body size in MB")
    enable_strict_guardrails: bool = Field(default=True, description="Block requests triggering security scanners")


class DatabaseConfig(BaseModel):
    """Databases, Vector Stores, and Caching Configuration."""
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="jarvis_db", description="Database name")
    postgres_user: str = Field(default="jarvis_user", description="Database user")
    postgres_password: SecretStr = Field(default=SecretStr("jarvis_password"), description="Database password")

    qdrant_host: str = Field(default="localhost", description="Qdrant vector storage host")
    qdrant_port: int = Field(default=6333, description="Qdrant REST port")
    qdrant_api_key: Optional[SecretStr] = Field(default=None, description="Qdrant Cloud API key")
    vector_collection_name: str = Field(default=DEFAULT_VECTOR_COLLECTION, description="Vector store collection name")
    vector_dimension: int = Field(default=DEFAULT_EMBEDDING_DIMENSION, description="Embedding vector space dimension")

    redis_host: str = Field(default="localhost", description="Redis cache host")
    redis_port: int = Field(default=6379, description="Redis cache port")
    redis_db: int = Field(default=0, description="Redis database index")

    @property
    def postgres_connection_string(self) -> str:
        """Returns PostgreSQL async connection DSN."""
        pwd = self.postgres_password.get_secret_value()
        return f"postgresql+asyncpg://{self.postgres_user}:{pwd}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


class VoiceConfig(BaseModel):
    """Voice Speech Recognition and Audio Synthesis settings."""
    stt_provider: str = Field(default="whisper", description="STT engine (whisper, deepgram, native)")
    tts_provider: str = Field(default="elevenlabs", description="TTS engine (elevenlabs, coqui, native)")
    elevenlabs_api_key: Optional[SecretStr] = Field(default=None, description="ElevenLabs API key")
    sample_rate: int = Field(default=16000, description="Audio PCM sample rate in Hz")
    channels: int = Field(default=1, description="Audio channel count (1=mono)")


class JarvisSettings(BaseSettings):
    """Central Jarvis Application Configuration Container."""

    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    environment: EnvironmentMode = Field(default=EnvironmentMode.DEVELOPMENT, description="Current execution mode")
    debug: bool = Field(default=True, description="Debug mode toggle")

    # Sub-configuration modules
    features: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)
    api: APISettingsConfig = Field(default_factory=APISettingsConfig)
    model: ModelSettingsConfig = Field(default_factory=ModelSettingsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore"
    )

    # Convenience helper methods
    def is_development(self) -> bool:
        """Returns True if running in development mode."""
        return self.environment == EnvironmentMode.DEVELOPMENT or self.debug is True

    def is_production(self) -> bool:
        """Returns True if running in production mode."""
        return self.environment == EnvironmentMode.PRODUCTION

    def is_testing(self) -> bool:
        """Returns True if running in testing mode."""
        return self.environment == EnvironmentMode.TESTING

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Checks whether a feature flag is enabled."""
        if hasattr(self.features, feature_name):
            return getattr(self.features, feature_name) is True
        return False


def get_settings() -> JarvisSettings:
    """Factory function returning active JarvisSettings singleton."""
    return JarvisSettings()


# Global active settings instance
settings = get_settings()
