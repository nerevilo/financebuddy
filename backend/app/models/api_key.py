"""
API Key model for programmatic access to the Ledgi API.

Supports LLM access (like Claude Code) and other integrations.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from ..core.database import Base


def generate_uuid():
    import uuid
    return str(uuid.uuid4())


class APIKey(Base):
    """
    API keys for programmatic access to user data.

    Keys are stored as SHA-256 hashes - the raw key is only shown once at creation.
    """
    __tablename__ = "api_keys"
    __table_args__ = (
        Index('ix_api_keys_user_active', 'user_id', 'is_active'),
        Index('ix_api_keys_key_hash', 'key_hash', unique=True),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Key identification
    name = Column(String, nullable=False)  # User-friendly name like "Claude Code"
    key_hash = Column(String, nullable=False, unique=True)  # SHA-256 hash of the key
    key_prefix = Column(String, nullable=False)  # First 8 chars for identification (fb_sk_a1b2)

    # Permissions - JSON array of scopes
    # e.g., ["transactions:read", "transactions:write", "analytics:read"]
    scopes = Column(Text, nullable=False, default='["*"]')  # Default: all scopes

    # Rate limiting tier
    tier = Column(String, nullable=False, default="beta")  # beta, free, pro

    # Status
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration

    # Audit
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="api_keys")
