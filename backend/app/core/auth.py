"""
Authentication dependencies for FastAPI routes.

Provides get_current_user dependency for protected routes.
Supports both JWT tokens and API keys for flexible access.
"""
from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .security import decode_token
from .api_keys import is_api_key, validate_api_key
from ..models import User
from ..models.api_key import APIKey

# Bearer token security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
# For API key only routes
api_key_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.

    Use this in routes that require authentication:
        @router.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            ...

    Raises:
        HTTPException 401: If token is missing or invalid
        HTTPException 403: If user account is deactivated
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    token_data = decode_token(token)

    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional auth dependency - returns None if no valid token.

    Useful for endpoints that work with or without authentication:
        @router.get("/public-or-private")
        async def mixed_route(current_user: Optional[User] = Depends(get_current_user_optional)):
            if current_user:
                # Authenticated access
            else:
                # Anonymous access
    """
    if credentials is None:
        return None

    token_data = decode_token(credentials.credentials)
    if token_data is None or token_data.user_id is None:
        return None

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user and user.is_active:
        return user
    return None


async def get_current_user_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> User:
    """
    Flexible auth dependency that accepts either JWT or API key.

    Checks in order:
    1. X-API-Key header
    2. Bearer token that looks like an API key (fb_sk_...)
    3. Bearer token as JWT

    Use this for endpoints that should work with both web UI and programmatic access.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check X-API-Key header first
    if x_api_key:
        result = validate_api_key(x_api_key, db)
        if result:
            user, api_key = result
            return user
        raise credentials_exception

    # Check Bearer token
    if credentials is None:
        raise credentials_exception

    token = credentials.credentials

    # Check if it's an API key in Bearer format
    if is_api_key(token):
        result = validate_api_key(token, db)
        if result:
            user, api_key = result
            return user
        raise credentials_exception

    # Try as JWT token
    token_data = decode_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    return user


async def get_current_user_and_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> Tuple[User, Optional[APIKey]]:
    """
    Get current user with API key info (if authenticated via API key).

    Returns tuple of (User, APIKey or None).
    Use this when you need to check scopes or apply rate limiting.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Check X-API-Key header first
    if x_api_key:
        result = validate_api_key(x_api_key, db)
        if result:
            return result  # (user, api_key)
        raise credentials_exception

    # Check Bearer token
    if credentials is None:
        raise credentials_exception

    token = credentials.credentials

    # Check if it's an API key in Bearer format
    if is_api_key(token):
        result = validate_api_key(token, db)
        if result:
            return result  # (user, api_key)
        raise credentials_exception

    # Try as JWT token
    token_data = decode_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    return user, None  # JWT auth, no API key
