"""Device and Session Authentication Manager."""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from core.exceptions import AuthenticationError


class DeviceIdentity(BaseModel):
    """Enrolled device record."""
    device_id: str
    device_name: str
    public_key_fingerprint: str
    is_revoked: bool = False
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionToken(BaseModel):
    """Short-lived capability token issued to an authenticated client."""
    token_id: UUID = Field(default_factory=uuid4)
    device_id: str
    secret_hash: str
    expires_at: datetime

    def is_valid(self, secret: str) -> bool:
        """Verify token expiration and hash match."""
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        expected_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        return secrets.compare_digest(self.secret_hash, expected_hash)


class Authenticator:
    """Authentication and session lifecycle controller."""

    def __init__(self, token_ttl_minutes: int = 15) -> None:
        self.token_ttl = timedelta(minutes=token_ttl_minutes)
        self._devices: dict[str, DeviceIdentity] = {}
        self._active_tokens: dict[UUID, SessionToken] = {}

    def enroll_device(self, device_id: str, device_name: str, fingerprint: str) -> DeviceIdentity:
        """Enroll a trusted client device."""
        device = DeviceIdentity(
            device_id=device_id,
            device_name=device_name,
            public_key_fingerprint=fingerprint,
        )
        self._devices[device_id] = device
        return device

    def revoke_device(self, device_id: str) -> None:
        """Revoke a device and purge all of its active session tokens."""
        if device_id in self._devices:
            self._devices[device_id].is_revoked = True
        # Invalidate active tokens for this device
        to_remove = [tid for tid, tok in self._active_tokens.items() if tok.device_id == device_id]
        for tid in to_remove:
            del self._active_tokens[tid]

    def authenticate_device(self, device_id: str) -> tuple[SessionToken, str]:
        """Authenticate device and issue a new short-lived session token with a raw secret."""
        device = self._devices.get(device_id)
        if not device or device.is_revoked:
            raise AuthenticationError(f"Device '{device_id}' is unknown or revoked.")

        raw_secret = secrets.token_urlsafe(32)
        secret_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
        token = SessionToken(
            device_id=device_id,
            secret_hash=secret_hash,
            expires_at=datetime.now(timezone.utc) + self.token_ttl,
        )
        self._active_tokens[token.token_id] = token
        return token, raw_secret

    def validate_session(self, token_id: UUID, raw_secret: str) -> bool:
        """Validate an active session token."""
        token = self._active_tokens.get(token_id)
        if not token:
            return False
        device = self._devices.get(token.device_id)
        if not device or device.is_revoked:
            return False
        return token.is_valid(raw_secret)
