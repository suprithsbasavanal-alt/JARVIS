"""Memory Encryption and Field-Level Protection Abstraction."""

from abc import ABC, abstractmethod


class MemoryEncryptor(ABC):
    """Abstract interface for encrypting and decrypting persistent memory fields."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string."""
        pass

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string."""
        pass


class PassthroughMemoryEncryptor(MemoryEncryptor):
    """Hermetic simulator for Phase 0 safe development."""

    def encrypt(self, plaintext: str) -> str:
        # In Phase 0: Safe mock tag
        return f"[ENCRYPTED_AES256:{plaintext}]"

    def decrypt(self, ciphertext: str) -> str:
        if ciphertext.startswith("[ENCRYPTED_AES256:") and ciphertext.endswith("]"):
            return ciphertext[len("[ENCRYPTED_AES256:"):-1]
        return ciphertext
