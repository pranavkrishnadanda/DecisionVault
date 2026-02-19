from cryptography.fernet import Fernet
from django.conf import settings


def _cipher() -> Fernet:
    key = getattr(settings, "TOKEN_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is required")
    return Fernet(key.encode())


def encrypt_token(plaintext: str) -> str:
    return _cipher().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    return _cipher().decrypt(ciphertext.encode()).decode()
