"""Secret Vault & Payload Encryption Helpers."""

import base64
import hashlib
from config.settings import settings


class SecretVaultService:
    """Manages secret string obfuscation and vault encryption keys."""

    @staticmethod
    def hash_secret(secret_str: str) -> str:
        """Computes SHA-256 hash of secret token."""
        salt = settings.security.secret_key.get_secret_value()
        combined = f"{secret_str}:{salt}".encode("utf-8")
        return hashlib.sha256(combined).hexdigest()

    @staticmethod
    def mask_secret(secret_str: str, visible_chars: int = 4) -> str:
        """Masks API keys or tokens showing only last visible_chars."""
        if not secret_str or len(secret_str) <= visible_chars:
            return "******"
        return "*" * (len(secret_str) - visible_chars) + secret_str[-visible_chars:]
