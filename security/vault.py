"""Abstract Cryptographic Secret Vault Interface."""

from abc import ABC, abstractmethod


class SecretVault(ABC):
    """Abstract interface for hardware-backed or local keyring storage."""

    @abstractmethod
    def store_secret(self, key: str, value: str) -> None:
        """Securely store a secret key-value pair."""
        pass

    @abstractmethod
    def get_secret(self, key: str) -> str | None:
        """Retrieve a stored secret."""
        pass

    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """Delete a stored secret."""
        pass


class MockSecretVault(SecretVault):
    """Hermetic in-memory vault for Phase 0 safe development."""

    def __init__(self) -> None:
        self._vault: dict[str, str] = {}

    def store_secret(self, key: str, value: str) -> None:
        self._vault[key] = value

    def get_secret(self, key: str) -> str | None:
        return self._vault.get(key)

    def delete_secret(self, key: str) -> bool:
        if key in self._vault:
            del self._vault[key]
            return True
        return False
