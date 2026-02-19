from cryptography.fernet import Fernet
import pytest
from django.test import override_settings

from app.slack.encryption import decrypt_token, encrypt_token


@override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode())
def test_token_encryption_roundtrip():
    plaintext = "xoxb-secret-token"
    encrypted = encrypt_token(plaintext)

    assert encrypted != plaintext
    assert decrypt_token(encrypted) == plaintext


@override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode())
def test_decrypt_with_wrong_key_raises():
    plaintext = "xoxb-secret-token"
    encrypted = encrypt_token(plaintext)

    with override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode()):
        with pytest.raises(Exception):
            decrypt_token(encrypted)
