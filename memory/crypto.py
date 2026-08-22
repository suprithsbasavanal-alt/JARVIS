"""Authenticated Application-Level Encryption Engine for Sensitive Memory Fields.

Pure Python 3.12 implementation using standard library hashlib, hmac, and secrets.
Implements an Encrypt-then-MAC authenticated envelope with key separation.
"""

from abc import ABC, abstractmethod
import hashlib
import hmac
import secrets
from memory.keys import KeyProvider, TestKeyProvider


class CryptoError(Exception):
    """Base exception for cryptographic failures."""
    pass


class TamperedCiphertextError(CryptoError):
    """Raised when HMAC authentication tag verification fails."""
    pass


class DecryptionError(CryptoError):
    """Raised when decryption fails due to invalid key or format."""
    pass


class BaseEncryptor(ABC):
    """Abstract interface for field-level authenticated encryption."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Encrypt and authenticate plaintext string into a safe envelope."""
        pass

    @abstractmethod
    def decrypt(self, envelope: str) -> str:
        """Verify authenticity and decrypt envelope back into plaintext string."""
        pass


class AuthenticatedEncryptor(BaseEncryptor):
    """Standard-library Encrypt-then-MAC authenticated encryption engine.
    
    Structure:
      1. Nonce: 16 cryptographically secure random bytes.
      2. Keystream Generation: Counter-mode SHA-256 derivation over (enc_key, nonce, counter).
      3. Ciphertext: Plaintext XOR keystream.
      4. HMAC Tag: HMAC-SHA256 over (version || nonce || ciphertext) using auth_key.
      5. Serialized Envelope: "v1:<hex_nonce>:<hex_ciphertext>:<hex_tag>"
    """

    VERSION_PREFIX = "v1"

    def __init__(self, key_provider: KeyProvider | None = None) -> None:
        self.key_provider = key_provider or TestKeyProvider()

    def _generate_keystream(self, key: bytes, nonce: bytes, length: int) -> bytes:
        """Generate deterministic pseudo-random keystream for one-time block encryption."""
        keystream = bytearray()
        counter = 0
        while len(keystream) < length:
            counter_bytes = counter.to_bytes(4, byteorder="big")
            block = hashlib.sha256(key + nonce + counter_bytes).digest()
            keystream.extend(block)
            counter += 1
        return bytes(keystream[:length])

    def encrypt(self, plaintext: str) -> str:
        """Encrypt and MAC-tag the plaintext."""
        if not plaintext:
            return ""

        enc_key = self.key_provider.get_encryption_key()
        auth_key = self.key_provider.get_authentication_key()

        raw_bytes = plaintext.encode("utf-8")
        nonce = secrets.token_bytes(16)

        # Encrypt
        keystream = self._generate_keystream(enc_key, nonce, len(raw_bytes))
        ciphertext = bytes(a ^ b for a, b in zip(raw_bytes, keystream, strict=True))

        # Compute HMAC over version + nonce + ciphertext
        mac = hmac.new(auth_key, digestmod=hashlib.sha256)
        mac.update(self.VERSION_PREFIX.encode("utf-8"))
        mac.update(nonce)
        mac.update(ciphertext)
        tag = mac.digest()

        return f"{self.VERSION_PREFIX}:{nonce.hex()}:{ciphertext.hex()}:{tag.hex()}"

    def decrypt(self, envelope: str) -> str:
        """Authenticate and decrypt envelope."""
        if not envelope:
            return ""

        parts = envelope.split(":")
        if len(parts) != 4 or parts[0] != self.VERSION_PREFIX:
            raise DecryptionError(f"Invalid ciphertext envelope format: {envelope[:20]}...")

        _, nonce_hex, cipher_hex, tag_hex = parts

        try:
            nonce = bytes.fromhex(nonce_hex)
            ciphertext = bytes.fromhex(cipher_hex)
            expected_tag = bytes.fromhex(tag_hex)
        except ValueError as err:
            raise DecryptionError(f"Corrupted hex encoding in envelope: {err}") from err

        auth_key = self.key_provider.get_authentication_key()
        enc_key = self.key_provider.get_encryption_key()

        # Verify HMAC tag first (Constant-time comparison)
        mac = hmac.new(auth_key, digestmod=hashlib.sha256)
        mac.update(self.VERSION_PREFIX.encode("utf-8"))
        mac.update(nonce)
        mac.update(ciphertext)
        computed_tag = mac.digest()

        if not hmac.compare_digest(computed_tag, expected_tag):
            raise TamperedCiphertextError("HMAC verification failed: Ciphertext has been tampered with or key is wrong.")

        # Decrypt
        keystream = self._generate_keystream(enc_key, nonce, len(ciphertext))
        raw_bytes = bytes(a ^ b for a, b in zip(ciphertext, keystream, strict=True))

        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError as err:
            raise DecryptionError(f"Decrypted payload is not valid UTF-8: {err}") from err
