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
        key_b64 = key_b64 or getattr(settings, "phi_encryption_key", None)
        if not key_b64:
            raise ValueError("PHI_ENCRYPTION_KEY is missing in environment (.env).")

        try:
            key = base64.b64decode(key_b64)
        except Exception as e:
            raise ValueError("PHI_ENCRYPTION_KEY must be base64-encoded.") from e

        if len(key) != 32:
            raise ValueError(
                f"PHI_ENCRYPTION_KEY must decode to 32 bytes for AES-256. Got {len(key)} bytes."
            )

        self._aesgcm = AESGCM(key)

    def encrypt_text(self, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None:
            return None
        nonce = os.urandom(12)  # GCM standard nonce size
        ct = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode("utf-8")

    def decrypt_text(self, token_b64: Optional[str]) -> Optional[str]:
        if token_b64 is None:
            return None
        raw = base64.b64decode(token_b64)
        if len(raw) < 13:
            raise ValueError("Invalid ciphertext (too short).")
        nonce, ct = raw[:12], raw[12:]
        pt = self._aesgcm.decrypt(nonce, ct, None)
        return pt.decode("utf-8")

    def encrypt_json(self, data: Optional[Dict[str, Any]]) -> Optional[str]:
        if data is None:
            return None
        # deterministic serialization (stable)
        payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return self.encrypt_text(payload)

    def decrypt_json(self, token_b64: Optional[str]) -> Optional[Dict[str, Any]]:
        if token_b64 is None:
            return None
        payload = self.decrypt_text(token_b64)
        return json.loads(payload)


# Convenience functions (if your code previously used module-level funcs)
_service = None

def get_encryption_service() -> EncryptionService:
    global _service
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
