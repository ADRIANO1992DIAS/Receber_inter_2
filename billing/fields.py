from django.db import models
from billing.utils.crypto import encrypt_bytes, decrypt_bytes


class EncryptedTextField(models.TextField):
    description = "Texto armazenado criptografado com Fernet"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        raw = value.encode("utf-8") if isinstance(value, str) else str(value).encode("utf-8")
        token = encrypt_bytes(raw)
        return token.decode("utf-8")

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return decrypt_bytes(value.encode("utf-8")).decode("utf-8")
        except Exception:
            return value

    def to_python(self, value):
        if value is None:
            return value
        return value
