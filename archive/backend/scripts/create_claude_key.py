#!/usr/bin/env python3
"""
Create an API key for Claude Code access.

Usage:
    python -m scripts.create_claude_key <email>
    python -m scripts.create_claude_key --list <email>

Run from the backend/ directory.
"""
import sys
import os

# Add parent dir so imports work when run as `python -m scripts.create_claude_key`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.api_keys import generate_api_key
from app.models import User
from app.models.api_key import APIKey


def create_key(email: str) -> str:
    """Create an API key with full access for the given user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email, User.is_active == True).first()
        if not user:
            print(f"Error: No active user found with email '{email}'", file=sys.stderr)
            sys.exit(1)

        raw_key, key_hash, key_prefix = generate_api_key()

        api_key = APIKey(
            user_id=user.id,
            name="Claude Code",
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes='["*"]',
            tier="pro",
        )
        db.add(api_key)
        db.commit()

        # Print ONLY the raw key to stdout (for piping)
        print(raw_key)
        # Context info to stderr (doesn't interfere with piping)
        print(f"Created API key for {email} (prefix: {key_prefix})", file=sys.stderr)
        return raw_key
    finally:
        db.close()


def list_keys(email: str):
    """List active API keys for a user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email, User.is_active == True).first()
        if not user:
            print(f"Error: No active user found with email '{email}'", file=sys.stderr)
            sys.exit(1)

        keys = db.query(APIKey).filter(
            APIKey.user_id == user.id,
            APIKey.is_active == True,
        ).all()

        if not keys:
            print("No active API keys.")
            return

        for k in keys:
            used = k.last_used_at.isoformat() if k.last_used_at else "never"
            print(f"  {k.key_prefix}...  name={k.name}  tier={k.tier}  last_used={used}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.create_claude_key <email>", file=sys.stderr)
        print("       python -m scripts.create_claude_key --list <email>", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--list":
        if len(sys.argv) < 3:
            print("Usage: python -m scripts.create_claude_key --list <email>", file=sys.stderr)
            sys.exit(1)
        list_keys(sys.argv[2])
    else:
        create_key(sys.argv[1])
