"""
Authentication dependencies for FastAPI routes.

Provides get_current_user dependency for protected routes.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .security import decode_token
from ..models import User

# Bearer token security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


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
