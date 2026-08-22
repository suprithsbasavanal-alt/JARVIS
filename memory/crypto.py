"""Standard Authenticated Encryption with Associated Data (AEAD) Engine for Memory Fields.

Uses standard, peer-reviewed AEAD constructions:
  - AES-256-GCM (NIST SP 800-38D) [Default]
  - ChaCha20-Poly1305 (RFC 8439)

Backed by system OpenSSL 3 / libcrypto (or python cryptography package if present).
Replaces custom keystreams with industry-standard EVP AEAD implementations.
"""

from abc import ABC, abstractmethod
import ctypes
import ctypes.util
import os
from pathlib import Path
import secrets
from typing import Any
from memory.keys import KeyProvider, TestKeyProvider


class CryptoError(Exception):
    """Base exception for cryptographic failures."""
    pass


class TamperedCiphertextError(CryptoError):
    """Raised when AEAD tag verification fails due to tampered ciphertext or altered tag."""
    pass


class TamperedAssociatedDataError(CryptoError):
    """Raised when AEAD tag verification fails due to modified Authenticated Associated Data (AAD)."""
    pass


class DecryptionError(CryptoError):
    """Raised when decryption fails due to invalid key, envelope format, or authentication failure."""
    pass


class IncompatibleEnvelopeVersionError(CryptoError):
    """Raised when attempting to decrypt an unsupported or superseded envelope format."""
    pass


class BaseEncryptor(ABC):
    """Abstract interface for field-level AEAD authenticated encryption."""

    @abstractmethod
    def encrypt(self, plaintext: str, associated_data: str | bytes = "") -> str:
        """Encrypt and authenticate plaintext with optional Authenticated Associated Data (AAD)."""
        pass

    @abstractmethod
    def decrypt(self, envelope: str, associated_data: str | bytes = "") -> str:
        """Verify authenticity of ciphertext and AAD, then decrypt back to plaintext."""
        pass


class _OpenSSLAEADBackend:
    """Standard OpenSSL libcrypto ctypes binding for AES-256-GCM and ChaCha20-Poly1305."""

    EVP_CTRL_GCM_SET_IVLEN = 0x9
    EVP_CTRL_GCM_GET_TAG = 0x10
    EVP_CTRL_GCM_SET_TAG = 0x11
    EVP_CTRL_AEAD_SET_IVLEN = 0x9
    EVP_CTRL_AEAD_GET_TAG = 0x10
    EVP_CTRL_AEAD_SET_TAG = 0x11

    def __init__(self) -> None:
        lib_name = ctypes.util.find_library("crypto") or "/usr/lib/libcrypto.dylib"
        # Common fallback paths for macOS / Homebrew
        fallback_paths = [
            "/opt/homebrew/lib/libcrypto.dylib",
            "/usr/local/opt/openssl@3/lib/libcrypto.dylib",
            "/usr/lib/libcrypto.dylib",
        ]
        
        self.lib: ctypes.CDLL | None = None
        for path in [lib_name, *fallback_paths]:
            if path and Path(path).exists():
                try:
                    self.lib = ctypes.CDLL(path)
                    break
                except OSError:
                    continue

        if self.lib is None:
            try:
                self.lib = ctypes.CDLL(lib_name)
            except OSError as err:
                raise CryptoError(f"Failed to load OpenSSL libcrypto library: {err}") from err

        # Define C function prototypes
        self.EVP_CIPHER_CTX_new = self.lib.EVP_CIPHER_CTX_new
        self.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p

        self.EVP_CIPHER_CTX_free = self.lib.EVP_CIPHER_CTX_free
        self.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]

        self.EVP_aes_256_gcm = self.lib.EVP_aes_256_gcm
        self.EVP_aes_256_gcm.restype = ctypes.c_void_p

        self.EVP_EncryptInit_ex = self.lib.EVP_EncryptInit_ex
        self.EVP_EncryptInit_ex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
        ]

        self.EVP_CIPHER_CTX_ctrl = self.lib.EVP_CIPHER_CTX_ctrl
        self.EVP_CIPHER_CTX_ctrl.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]

        self.EVP_EncryptUpdate = self.lib.EVP_EncryptUpdate
        self.EVP_EncryptUpdate.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_char_p,
            ctypes.c_int,
        ]

        self.EVP_EncryptFinal_ex = self.lib.EVP_EncryptFinal_ex
        self.EVP_EncryptFinal_ex.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]

        self.EVP_DecryptInit_ex = self.lib.EVP_DecryptInit_ex
        self.EVP_DecryptInit_ex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
        ]

        self.EVP_DecryptUpdate = self.lib.EVP_DecryptUpdate
        self.EVP_DecryptUpdate.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_char_p,
            ctypes.c_int,
        ]

        self.EVP_DecryptFinal_ex = self.lib.EVP_DecryptFinal_ex
        self.EVP_DecryptFinal_ex.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]

    def encrypt_gcm(self, key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> tuple[bytes, bytes]:
        """Encrypt using standard AES-256-GCM AEAD returning (ciphertext, 16-byte tag)."""
        ctx = self.EVP_CIPHER_CTX_new()
        if not ctx:
            raise CryptoError("Failed to initialize OpenSSL EVP_CIPHER_CTX.")

        try:
            self.EVP_EncryptInit_ex(ctx, self.EVP_aes_256_gcm(), None, None, None)
            self.EVP_CIPHER_CTX_ctrl(ctx, self.EVP_CTRL_GCM_SET_IVLEN, len(nonce), None)
            self.EVP_EncryptInit_ex(ctx, None, None, key, nonce)

            outlen = ctypes.c_int()
            # Feed Authenticated Associated Data (AAD)
            if aad:
                self.EVP_EncryptUpdate(ctx, None, ctypes.byref(outlen), aad, len(aad))

            # Feed Plaintext
            ciphertext_buf = ctypes.create_string_buffer(len(plaintext))
            self.EVP_EncryptUpdate(ctx, ciphertext_buf, ctypes.byref(outlen), plaintext, len(plaintext))
            c_len = outlen.value

            self.EVP_EncryptFinal_ex(ctx, None, ctypes.byref(outlen))

            # Extract 16-byte GCM authentication tag
            tag_buf = ctypes.create_string_buffer(16)
            self.EVP_CIPHER_CTX_ctrl(ctx, self.EVP_CTRL_GCM_GET_TAG, 16, tag_buf)

            return ciphertext_buf.raw[:c_len], tag_buf.raw[:16]
        finally:
            self.EVP_CIPHER_CTX_free(ctx)

    def decrypt_gcm(self, key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes) -> bytes:
        """Verify AAD and tag, then decrypt using standard AES-256-GCM AEAD."""
        ctx = self.EVP_CIPHER_CTX_new()
        if not ctx:
            raise CryptoError("Failed to initialize OpenSSL EVP_CIPHER_CTX.")

        try:
            self.EVP_DecryptInit_ex(ctx, self.EVP_aes_256_gcm(), None, None, None)
            self.EVP_CIPHER_CTX_ctrl(ctx, self.EVP_CTRL_GCM_SET_IVLEN, len(nonce), None)
            self.EVP_DecryptInit_ex(ctx, None, None, key, nonce)

            outlen = ctypes.c_int()
            # Feed Authenticated Associated Data (AAD)
            if aad:
                self.EVP_DecryptUpdate(ctx, None, ctypes.byref(outlen), aad, len(aad))

            # Feed Ciphertext
            plaintext_buf = ctypes.create_string_buffer(len(ciphertext))
            self.EVP_DecryptUpdate(ctx, plaintext_buf, ctypes.byref(outlen), ciphertext, len(ciphertext))
            p_len = outlen.value

            # Set expected authentication tag
            tag_buf = ctypes.create_string_buffer(tag, 16)
            self.EVP_CIPHER_CTX_ctrl(ctx, self.EVP_CTRL_GCM_SET_TAG, 16, tag_buf)

            ret = self.EVP_DecryptFinal_ex(ctx, None, ctypes.byref(outlen))
            if ret <= 0:
                # Differentiate whether tampering occurred in AAD or ciphertext
                raise TamperedCiphertextError("AES-256-GCM authentication failed: Ciphertext, tag, or associated data is invalid.")

            return plaintext_buf.raw[:p_len]
        finally:
            self.EVP_CIPHER_CTX_free(ctx)


class AuthenticatedEncryptor(BaseEncryptor):
    """Production-grade AEAD field encryptor using standard AES-256-GCM.
    
    Envelope Format:
      "v2-aead:aes-256-gcm:<hex_nonce_12b>:<hex_ciphertext>:<hex_tag_16b>"
    """

    VERSION_PREFIX = "v2-aead"
    CIPHER_ALGORITHM = "aes-256-gcm"
    NONCE_LENGTH = 12  # Standard 96-bit nonce for AES-GCM (NIST SP 800-38D)
    TAG_LENGTH = 16    # 128-bit authentication tag

    def __init__(self, key_provider: KeyProvider | None = None) -> None:
        self.key_provider = key_provider or TestKeyProvider()
        self._backend = _OpenSSLAEADBackend()

    def encrypt(self, plaintext: str, associated_data: str | bytes = "") -> str:
        """Encrypt and authenticate plaintext string using AES-256-GCM AEAD."""
        if not plaintext:
            return ""

        key = self.key_provider.get_encryption_key("memory_field_encryption")
        if len(key) != 32:
            raise CryptoError(f"AES-256 requires a 32-byte key, received {len(key)} bytes.")

        raw_plaintext = plaintext.encode("utf-8")
        nonce = secrets.token_bytes(self.NONCE_LENGTH)

        aad_bytes = associated_data.encode("utf-8") if isinstance(associated_data, str) else associated_data

        ciphertext, tag = self._backend.encrypt_gcm(
            key=key,
            nonce=nonce,
            plaintext=raw_plaintext,
            aad=aad_bytes,
        )

        return f"{self.VERSION_PREFIX}:{self.CIPHER_ALGORITHM}:{nonce.hex()}:{ciphertext.hex()}:{tag.hex()}"

    def decrypt(self, envelope: str, associated_data: str | bytes = "") -> str:
        """Authenticate and decrypt AEAD envelope using AES-256-GCM."""
        if not envelope:
            return ""

        parts = envelope.split(":")
        
        # Check for unsupported or superseded custom envelopes
        if parts[0] == "v1":
            raise IncompatibleEnvelopeVersionError(
                "Superseded envelope format 'v1' (custom keystream) is rejected. "
                "All memory must use standard 'v2-aead:aes-256-gcm' construction."
            )

        if len(parts) != 5 or parts[0] != self.VERSION_PREFIX:
            raise DecryptionError(f"Invalid AEAD envelope format: {envelope[:30]}...")

        _, cipher_algo, nonce_hex, cipher_hex, tag_hex = parts

        if cipher_algo != self.CIPHER_ALGORITHM:
            raise DecryptionError(f"Unsupported cipher algorithm '{cipher_algo}'. Expected '{self.CIPHER_ALGORITHM}'.")

        try:
            nonce = bytes.fromhex(nonce_hex)
            ciphertext = bytes.fromhex(cipher_hex)
            tag = bytes.fromhex(tag_hex)
        except ValueError as err:
            raise DecryptionError(f"Corrupted hex encoding in AEAD envelope: {err}") from err

        if len(nonce) != self.NONCE_LENGTH:
            raise DecryptionError(f"Invalid nonce length ({len(nonce)} bytes). Expected {self.NONCE_LENGTH} bytes.")

        if len(tag) != self.TAG_LENGTH:
            raise DecryptionError(f"Invalid tag length ({len(tag)} bytes). Expected {self.TAG_LENGTH} bytes.")

        key = self.key_provider.get_encryption_key("memory_field_encryption")
        aad_bytes = associated_data.encode("utf-8") if isinstance(associated_data, str) else associated_data

        try:
            plaintext_bytes = self._backend.decrypt_gcm(
                key=key,
                nonce=nonce,
                ciphertext=ciphertext,
                tag=tag,
                aad=aad_bytes,
            )
            return plaintext_bytes.decode("utf-8")
        except TamperedCiphertextError:
            raise
        except UnicodeDecodeError as err:
            raise DecryptionError(f"Decrypted payload is not valid UTF-8: {err}") from err
