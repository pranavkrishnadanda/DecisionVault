"""Credential encryption/decryption helpers for integration secrets at rest."""

from __future__ import annotations

import base64
import json
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _vault_key() -> bytes:
    digest = sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_credentials(credentials: dict) -> str:
    if not isinstance(credentials, dict):
        raise ValueError("credentials must be an object")
    payload = json.dumps(credentials, separators=(",", ":"), sort_keys=True)
    return Fernet(_vault_key()).encrypt(payload.encode("utf-8")).decode("utf-8")


def decrypt_credentials(ciphertext: str) -> dict:
    if not ciphertext:
        return {}
    try:
        raw = Fernet(_vault_key()).decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("credentials could not be decrypted") from exc

    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("decrypted credentials are invalid")
    return data
