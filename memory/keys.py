"""Key Provider Interfaces and Implementations for Secure Memory Encryption."""

from abc import ABC, abstractmethod
import hashlib
import hmac


class KeyProvider(ABC):
    """Abstract interface for retrieving memory encryption and authentication keys."""

    @abstractmethod
    def get_encryption_key(self, purpose: str = "memory_field_encryption") -> bytes:
        """Derive or retrieve 32-byte key for encryption."""
        pass

    @abstractmethod
    def get_authentication_key(self, purpose: str = "memory_field_authentication") -> bytes:
        """Derive or retrieve 32-byte key for HMAC message authentication."""
        pass


class TestKeyProvider(KeyProvider):
    """Hermetic test-only key provider using deterministic key derivation for sandbox testing.
    
    NEVER use this in production. Uses a fixed test salt and seed.
    """
    __test__ = False

    def __init__(self, test_seed: str = "jarvis_phase2_sandbox_test_secret_seed_2026") -> None:
        self._seed = test_seed.encode("utf-8")

    def get_encryption_key(self, purpose: str = "memory_field_encryption") -> bytes:
        """Derive deterministic 32-byte test encryption key via HKDF/HMAC-SHA256."""
        h = hmac.new(self._seed, f"enc_{purpose}".encode("utf-8"), hashlib.sha256)
        return h.digest()

    def get_authentication_key(self, purpose: str = "memory_field_authentication") -> bytes:
        """Derive deterministic 32-byte test authentication key via HKDF/HMAC-SHA256."""
        h = hmac.new(self._seed, f"auth_{purpose}".encode("utf-8"), hashlib.sha256)
        return h.digest()


class HardwareKeyProvider(KeyProvider):
    """Production key interface for hardware-backed keys (Keychain / Android Keystore)."""

    def __init__(self, key_identifier: str = "com.jarvis.memory.master") -> None:
        self.key_identifier = key_identifier

    def get_encryption_key(self, purpose: str = "memory_field_encryption") -> bytes:
        # In Phase 2: Stub interface for future production phase
        raise NotImplementedError("HardwareKeyProvider is reserved for Phase 13 production deployment.")

    def get_authentication_key(self, purpose: str = "memory_field_authentication") -> bytes:
        # In Phase 2: Stub interface for future production phase
        raise NotImplementedError("HardwareKeyProvider is reserved for Phase 13 production deployment.")
