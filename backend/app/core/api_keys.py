"""
API Key generation and validation utilities.

Keys use the format: fb_sk_{32_random_chars}
Example: fb_sk_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Keys are stored as SHA-256 hashes - the raw key is only returned once at creation.
"""
import hmac
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from ..models.api_key import APIKey
from ..models import User


# Key prefix for Ledgi API keys
API_KEY_PREFIX = "fb_sk_"


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (raw_key, key_hash, key_prefix)
        - raw_key: The full key to show to user once (fb_sk_xxxxx)
        - key_hash: SHA-256 hash to store in database
        - key_prefix: First 12 chars for identification (fb_sk_xxxx)
    """
    # Generate 32 random bytes, encode as hex (64 chars)
    random_part = secrets.token_hex(16)  # 32 hex chars
    raw_key = f"{API_KEY_PREFIX}{random_part}"

    # Hash the key for storage
    key_hash = hash_api_key(raw_key)

    # Store prefix for identification (fb_sk_ + first 4 chars of random)
    key_prefix = raw_key[:12]

    return raw_key, key_hash, key_prefix


def hash_api_key(key: str) -> str:
    """
    Hash an API key using SHA-256.

    Args:
        key: The raw API key

    Returns:
        SHA-256 hash of the key
    """
    return hashlib.sha256(key.encode()).hexdigest()


def is_api_key(token: str) -> bool:
    """
    Check if a token is an API key (vs JWT).

    Args:
        token: The token to check

    Returns:
        True if the token looks like an API key
    """
    return token.startswith(API_KEY_PREFIX)


def validate_api_key(key: str, db: Session) -> Optional[Tuple[User, APIKey]]:
    """
    Validate an API key and return the associated user.

    Args:
        key: The raw API key
        db: Database session

    Returns:
        Tuple of (User, APIKey) if valid, None if invalid
    """
    if not is_api_key(key):
        return None

    key_hash = hash_api_key(key)
    key_prefix = key[:12]

    # Find candidates by prefix, then verify with timing-safe comparison
    api_key = db.query(APIKey).filter(
        APIKey.key_prefix == key_prefix,
        APIKey.is_active == True
    ).first()

    if not api_key or not hmac.compare_digest(api_key.key_hash, key_hash):
        return None

    # Check expiration
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return None

    # Get the user
    user = db.query(User).filter(
        User.id == api_key.user_id,
        User.is_active == True
    ).first()

    if not user:
        return None

    # Update last used timestamp
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return user, api_key


def check_scope(api_key: APIKey, required_scope: str) -> bool:
    """
    Check if an API key has the required scope.

    Args:
        api_key: The API key to check
        required_scope: The scope required (e.g., "transactions:read")

    Returns:
        True if the key has the scope or wildcard access
    """
    import json

    try:
        scopes = json.loads(api_key.scopes)
    except (json.JSONDecodeError, TypeError):
        scopes = ["*"]

    # Wildcard grants all access
    if "*" in scopes:
        return True

    # Check exact match
    if required_scope in scopes:
        return True

    # Check category wildcard (e.g., "transactions:*" grants "transactions:read")
    category = required_scope.split(":")[0]
    if f"{category}:*" in scopes:
        return True

    return False
