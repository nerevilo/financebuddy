"""
API Key Management Router

Allows users to create, list, and revoke API keys for programmatic access.
These endpoints require JWT authentication (managed via web UI).
"""
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.api_keys import generate_api_key
from ..models import User
from ..models.api_key import APIKey
from ..schemas.api_key import (
    APIKeyCreate,
    APIKeyUpdate,
    APIKeyResponse,
    APIKeyCreatedResponse,
    APIKeyListResponse,
)

router = APIRouter(prefix="/api/keys", tags=["API Keys"])

# Maximum number of API keys per user
MAX_KEYS_PER_USER = 10


@router.post("/", response_model=APIKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key.

    The raw API key is returned only once in this response.
    Store it securely - it cannot be retrieved later.

    Requires JWT authentication (web login).
    """
    # Check key limit
    existing_count = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).count()

    if existing_count >= MAX_KEYS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {MAX_KEYS_PER_USER} active API keys allowed. Revoke an existing key first."
        )

    # Generate new key
    raw_key, key_hash, key_prefix = generate_api_key()

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    # Create database record
    api_key = APIKey(
        user_id=current_user.id,
        name=request.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=json.dumps(request.scopes or ["*"]),
        tier="beta",  # All new keys start as beta tier
        expires_at=expires_at,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Parse scopes for response
    scopes = json.loads(api_key.scopes) if api_key.scopes else ["*"]

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,  # Only time this is returned!
        key_prefix=api_key.key_prefix,
        scopes=scopes,
        tier=api_key.tier,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all API keys for the current user.

    Note: The actual key values are not returned, only the prefix for identification.
    """
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).order_by(APIKey.created_at.desc()).limit(50).all()

    key_responses = []
    for key in keys:
        scopes = json.loads(key.scopes) if key.scopes else ["*"]
        key_responses.append(APIKeyResponse(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            scopes=scopes,
            tier=key.tier,
            is_active=key.is_active,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            created_at=key.created_at,
        ))

    return APIKeyListResponse(
        keys=key_responses,
        total=len(key_responses),
    )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific API key."""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    scopes = json.loads(api_key.scopes) if api_key.scopes else ["*"]

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=scopes,
        tier=api_key.tier,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.patch("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: APIKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an API key's name, scopes, or active status.

    Note: You cannot change the key itself. If compromised, revoke and create a new one.
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Update fields
    if request.name is not None:
        api_key.name = request.name

    if request.scopes is not None:
        api_key.scopes = json.dumps(request.scopes)

    if request.is_active is not None:
        api_key.is_active = request.is_active
        if not request.is_active:
            api_key.revoked_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(api_key)

    scopes = json.loads(api_key.scopes) if api_key.scopes else ["*"]

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=scopes,
        tier=api_key.tier,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke (deactivate) an API key.

    The key will immediately stop working. This cannot be undone.
    """
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    api_key.is_active = False
    api_key.revoked_at = datetime.now(timezone.utc)

    db.commit()

    return None
