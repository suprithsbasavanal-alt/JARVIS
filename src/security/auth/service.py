"""Authentication & Role-Based Access Control (RBAC) Service."""

from datetime import datetime, timezone, timedelta
from typing import List
from pydantic import BaseModel
from src.shared.exceptions.base import SecurityViolationError
from config.settings import settings


class UserSessionToken(BaseModel):
    """Token payload claims."""
    user_id: str
    roles: List[str] = ["user"]
    session_id: str
    exp: float


class AuthenticationService:
    """Manages user authentication and Role-Based Access Control (RBAC)."""

    def create_access_token(self, user_id: str, roles: List[str] = None, session_id: str = "default") -> str:
        """Generates token payload for user authorization."""
        roles = roles or ["user"]
        expire_delta = timedelta(minutes=settings.security.access_token_expire_minutes)
        exp_time = (datetime.now(timezone.utc) + expire_delta).timestamp()

        token_payload = f"{user_id}:{','.join(roles)}:{session_id}:{exp_time}"
        return token_payload

    def verify_token(self, token: str) -> UserSessionToken:
        """Verifies session token and extracts user claims."""
        try:
            parts = token.split(":")
            if len(parts) != 4:
                raise SecurityViolationError("Malformed authorization token.")

            user_id, roles_str, session_id, exp_str = parts
            exp = float(exp_str)

            if datetime.now(timezone.utc).timestamp() > exp:
                raise SecurityViolationError("Authorization token has expired.")

            return UserSessionToken(
                user_id=user_id,
                roles=roles_str.split(","),
                session_id=session_id,
                exp=exp
            )
        except Exception as e:
            raise SecurityViolationError(f"Token verification failed: {str(e)}")

    def check_permission(self, token: UserSessionToken, required_role: str) -> bool:
        """Enforces Role-Based Access Control (RBAC)."""
        if required_role not in token.roles and "admin" not in token.roles:
            raise SecurityViolationError(f"User '{token.user_id}' lacks required role '{required_role}'.")
        return True
