"""
This file encrypts sensitive health data before saving it.

It uses a secure key from the environment and produces safe text output
that can be stored in a database.

# =============================================================================
# FILE MAP - QUICK NAVIGATION
# =============================================================================
# IMPORTS.............................. Line 20
#
# CLASS: EncryptionService
#   - __init__()...................... Line 30  (Load/validate key)
#   - encrypt_text()................... Line 50  (Encrypt string)
#   - decrypt_text()................... Line 60  (Decrypt string)
#   - encrypt_json()................... Line 73  (Encrypt dict as JSON)
#   - decrypt_json()................... Line 80  (Decrypt JSON to dict)
#
# SINGLETON: encryption_service........ Line 95  (Module-level instance)
#
# BUSINESS CONTEXT:
# - AES-256-GCM encryption for PHI (HIPAA compliant)
# - Key from PHI_ENCRYPTION_KEY env var
# - Used for medical_history_encrypted field
# =============================================================================
"""

import base64
import json
import os
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


class EncryptionService:
    """
    AES-256-GCM encryption for PHI.
    Output format: base64(nonce(12) + ciphertext+tag)
    """

    def __init__(self, key_b64: Optional[str] = None):
        # Get the secret key from the environment or from the caller.
        key_b64 = key_b64 or getattr(settings, "phi_encryption_key", None)
        if not key_b64:
            raise ValueError("PHI_ENCRYPTION_KEY is missing in environment (.env).")

        try:
            # Turn the base64 key into raw bytes.
            key = base64.b64decode(key_b64)
        except Exception as e:
            raise ValueError("PHI_ENCRYPTION_KEY must be base64-encoded.") from e

        if len(key) != 32:
            raise ValueError(
                f"PHI_ENCRYPTION_KEY must decode to 32 bytes for AES-256. Got {len(key)} bytes."
            )

        # Create the encryption tool with the key.
        self._aesgcm = AESGCM(key)

    def encrypt_text(self, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None:
            return None
        # Make a random value for this encryption.
        nonce = os.urandom(12)  # GCM standard nonce size
        # Encrypt the text.
        ct = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # Return base64 text so it can be stored in the database.
        return base64.b64encode(nonce + ct).decode("utf-8")

    def decrypt_text(self, token_b64: Optional[str]) -> Optional[str]:
        if token_b64 is None:
            return None
        # Decode the base64 text back into bytes.
        raw = base64.b64decode(token_b64)
        if len(raw) < 13:
            raise ValueError("Invalid ciphertext (too short).")
        # Split the random part from the encrypted part.
        nonce, ct = raw[:12], raw[12:]
        # Decrypt the text.
        pt = self._aesgcm.decrypt(nonce, ct, None)
        return pt.decode("utf-8")

    def encrypt_json(self, data: Optional[Dict[str, Any]]) -> Optional[str]:
        if data is None:
            return None
        # Turn JSON into a stable string before encrypting.
        payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return self.encrypt_text(payload)

    def decrypt_json(self, token_b64: Optional[str]) -> Optional[Dict[str, Any]]:
        if token_b64 is None:
            return None
        payload = self.decrypt_text(token_b64)
        return json.loads(payload)


# Simple helpers for old code that used these functions directly.
_service = None

def get_encryption_service() -> EncryptionService:
    global _service
    # Create the service once and reuse it.
    if _service is None:
        _service = EncryptionService()
    return _service

def encrypt_phi(value: Optional[str]) -> Optional[str]:
    return get_encryption_service().encrypt_text(value)

def decrypt_phi(value: Optional[str]) -> Optional[str]:
    return get_encryption_service().decrypt_text(value)

def encrypt_phi_json(value: Optional[Dict[str, Any]]) -> Optional[str]:
    return get_encryption_service().encrypt_json(value)

def decrypt_phi_json(value: Optional[str]) -> Optional[Dict[str, Any]]:
    return get_encryption_service().decrypt_json(value)


# Export an instance for convenience
encryption_service = get_encryption_service()
