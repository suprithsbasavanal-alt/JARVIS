"""Configuration schema definitions for JARVIS.

Validated using Pydantic v2 with strict typing and default-safe constraints.
"""

from enum import Enum
from pathlib import Path
from typing import Literal


class PermissionLevel(str, Enum):
    """Conceptual permission levels for JARVIS."""
    LOCKED = "LOCKED"
    NORMAL = "NORMAL"
    SENSITIVE = "SENSITIVE"


class ModelTier(str, Enum):
    """Model routing tier categories."""
    FAST = "fast"
    REASONING = "reasoning"
    LOCAL_PRIVATE = "local_private"


from core.compat import BaseModel, Field


class SystemConfig(BaseModel):
    """System-level operational settings."""
    environment: Literal["development", "testing", "production"] = "development"
    debug: bool = True
    timezone: str = "Asia/Kolkata"
    user_display_name: str = "Suprith"
    formal_salutation: str = "Sir"
    enable_external_services: bool = False


class SecurityConfig(BaseModel):
    """Security engine configuration."""
    default_permission_level: PermissionLevel = PermissionLevel.NORMAL
    require_confirmation_for_sensitive: bool = True
    enable_prompt_guard: bool = True
    enable_pii_sanitization: bool = True
    audit_log_path: Path = Path("logs/audit.log")
    session_timeout_minutes: int = Field(default=60, ge=1, le=1440)
    max_failed_auth_attempts: int = Field(default=3, ge=1, le=10)


class ModelTierConfig(BaseModel):
    """Configuration for a specific AI model tier."""
    provider: Literal["mock", "local", "cloud"] = "mock"
    model_name: str = "mock-model"
    endpoint: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32768)


class ModelsConfig(BaseModel):
    """Model routing configuration across tiers."""
    default_provider: Literal["mock", "local", "cloud"] = "mock"
    fast_tier: ModelTierConfig = Field(
        default_factory=lambda: ModelTierConfig(model_name="mock-fast-v1", temperature=0.2)
    )
    reasoning_tier: ModelTierConfig = Field(
        default_factory=lambda: ModelTierConfig(model_name="mock-reasoning-v1", temperature=0.1)
    )
    local_private_tier: ModelTierConfig = Field(
        default_factory=lambda: ModelTierConfig(model_name="mock-local-v1", temperature=0.1)
    )


class MemoryConfig(BaseModel):
    """Memory subsystem configuration."""
    storage_type: Literal["sqlite_encrypted", "mock_in_memory"] = "mock_in_memory"
    db_path: Path = Path("data/memory.db")
    vector_index_path: Path = Path("data/vectors")
    enable_encryption: bool = True
    retention_days: int = Field(default=90, ge=1)
    max_working_memory_items: int = Field(default=20, ge=5, le=100)


class SandboxConfig(BaseModel):
    """Sandbox environment constraints."""
    enabled: bool = True
    enforce_strict_isolation: bool = True
    virtual_root: Path = Path("sandbox/fixtures/mock_files")
    allow_network: bool = False


class VoiceConfig(BaseModel):
    """Voice pipeline configuration."""
    enabled: bool = False
    wake_phrase: str = "Hey Jarvis"
    stt_engine: Literal["mock", "whisper_local", "cloud"] = "mock"
    tts_engine: Literal["mock", "piper_local", "avfoundation", "cloud"] = "mock"


class JarvisConfig(BaseModel):
    """Root configuration container for JARVIS."""
    system: SystemConfig = Field(default_factory=SystemConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
