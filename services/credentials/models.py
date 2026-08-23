"""Typed credential data models and redaction utilities (Phase 9.3)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CredentialType(str, Enum):
    """Supported external service authentication credential formats."""
    OAUTH2 = "OAUTH2"
    API_TOKEN = "API_TOKEN"
    BOT_TOKEN = "BOT_TOKEN"
    GENERIC = "GENERIC"


@dataclass(repr=False)
class BaseCredential:
    """Base model for all service credentials with strict secrecy guarantees."""
    service_id: str
    credential_type: CredentialType
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if the credential has passed its expiration threshold with a safety buffer."""
        if not self.expires_at:
            return False
        now_ts = datetime.now(timezone.utc).timestamp()
        exp_ts = self.expires_at.timestamp()
        return (exp_ts - now_ts) <= buffer_seconds

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a strictly sanitized metadata summary containing zero secrets."""
        return {
            "service_id": self.service_id,
            "credential_type": self.credential_type.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(service_id='{self.service_id}', type={self.credential_type.value}, secret=[REDACTED])>"

    def __str__(self) -> str:
        return self.__repr__()


@dataclass(repr=False)
class OAuth2Credentials(BaseCredential):
    """OAuth 2.0 access and refresh token credentials."""
    access_token: str = ""
    refresh_token: str | None = None
    token_type: str = "Bearer"
    scopes: list[str] = field(default_factory=list)

    def __init__(
        self,
        service_id: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
        token_type: str = "Bearer",
        scopes: list[str] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(
            service_id=service_id,
            credential_type=CredentialType.OAUTH2,
            created_at=created_at or datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.scopes = scopes or []

    def to_safe_dict(self) -> dict[str, Any]:
        base = super().to_safe_dict()
        base.update({
            "token_type": self.token_type,
            "has_refresh_token": bool(self.refresh_token),
            "scopes": self.scopes,
        })
        return base


@dataclass(repr=False)
class ApiTokenCredentials(BaseCredential):
    """API token / Personal Access Token credentials (e.g. GitHub PAT)."""
    token: str = ""
    username: str | None = None
    scopes: list[str] = field(default_factory=list)

    def __init__(
        self,
        service_id: str,
        token: str,
        username: str | None = None,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(
            service_id=service_id,
            credential_type=CredentialType.API_TOKEN,
            created_at=created_at or datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        self.token = token
        self.username = username
        self.scopes = scopes or []

    def to_safe_dict(self) -> dict[str, Any]:
        base = super().to_safe_dict()
        base.update({
            "username": self.username,
            "scopes": self.scopes,
        })
        return base


@dataclass(repr=False)
class BotTokenCredentials(BaseCredential):
    """Bot token credentials (e.g. Slack xoxb- bot token)."""
    bot_token: str = ""
    team_id: str | None = None
    scopes: list[str] = field(default_factory=list)

    def __init__(
        self,
        service_id: str,
        bot_token: str,
        team_id: str | None = None,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(
            service_id=service_id,
            credential_type=CredentialType.BOT_TOKEN,
            created_at=created_at or datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        self.bot_token = bot_token
        self.team_id = team_id
        self.scopes = scopes or []

    def to_safe_dict(self) -> dict[str, Any]:
        base = super().to_safe_dict()
        base.update({
            "team_id": self.team_id,
            "scopes": self.scopes,
        })
        return base


@dataclass(repr=False)
class GenericServiceCredentials(BaseCredential):
    """Generic key-value service credentials for extensible connectors."""
    payload: dict[str, str] = field(default_factory=dict)

    def __init__(
        self,
        service_id: str,
        payload: dict[str, str],
        expires_at: datetime | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(
            service_id=service_id,
            credential_type=CredentialType.GENERIC,
            created_at=created_at or datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        self.payload = payload

    def to_safe_dict(self) -> dict[str, Any]:
        base = super().to_safe_dict()
        base.update({
            "keys": list(self.payload.keys()),
        })
        return base
