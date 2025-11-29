from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _get_fernet() -> MultiFernet:
    keys = getattr(settings, "FERNET_KEYS", None)
    if not keys:
        raise ImproperlyConfigured("FERNET_KEYS not configured for encryption.")
    try:
        fernets = [Fernet(key) for key in keys]
    except Exception as exc:
        raise ImproperlyConfigured(f"Invalid FERNET_KEYS configured: {exc}") from exc
    return MultiFernet(fernets)


def encrypt_bytes(data: bytes) -> bytes:
    if data is None:
        return b""
    return _get_fernet().encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    if not data:
        return b""
    return _get_fernet().decrypt(data)
