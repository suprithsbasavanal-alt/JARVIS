"""Execution Context and System State Container for JARVIS."""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from core.compat import BaseModel, Field
from config.schema import PermissionLevel
from core.types import ExecutionContext


class SessionContext(BaseModel):
    """Context state for an active conversation turn and session."""
    session_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID = Field(default_factory=uuid4)
    device_id: str = "desktop-local-primary"
    user_name: str = "Suprith"
    formal_salutation: str = "Sir"
    permission_level: PermissionLevel = PermissionLevel.NORMAL
    exec_context: ExecutionContext = ExecutionContext.PRIVATE
    is_user_confirmed_alone: bool = False
    active_whitelist_paths: list[str] = Field(default_factory=lambda: ["sandbox/fixtures/mock_files"])
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def touch(self) -> None:
        """Update last activity timestamp and generate a new correlation ID for the turn."""
        self.last_activity_at = datetime.now(timezone.utc)
        self.correlation_id = uuid4()

    def get_salutation(self) -> str:
        """Derive appropriate salutation based on context rules."""
        if self.exec_context == ExecutionContext.PRIVATE:
            return self.user_name
        return self.formal_salutation
