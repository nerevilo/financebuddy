"""
Fernet symmetric encryption for sensitive data at rest (e.g. Teller tokens).

Requires ENCRYPTION_KEY env var — generate with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from cryptography.fernet import Fernet, InvalidToken
from .config import get_settings
from .logging_config import get_logger

logger = get_logger(__name__)

_fernet = None


def _get_fernet() -> Fernet | None:
    global _fernet
    if _fernet is not None:
        return _fernet
    key = get_settings().encryption_key
    if not key:
        logger.warning("ENCRYPTION_KEY not set — token encryption disabled")
        return None
    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string. Returns ciphertext or plaintext if encryption unavailable."""
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a string. Falls back to returning the input if decryption fails (unencrypted legacy data)."""
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # Legacy unencrypted value — return as-is
        return ciphertext
