"""
Authentication Router

Handles user registration, login, token refresh, and current user info.
Rate limiting is applied to protect against brute force attacks.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token
)
from ..core.auth import get_current_user
from ..core.rate_limiter import (
    limiter,
    REGISTER_RATE_LIMIT,
    LOGIN_RATE_LIMIT,
    REFRESH_RATE_LIMIT
)
from ..models import User
from ..models.models import generate_uuid
from ..schemas import UserRegister, UserLogin, TokenRefresh, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
@limiter.limit(REGISTER_RATE_LIMIT)
async def register(request: Request, user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Returns access and refresh tokens on success.
    Rate limited to 5 requests per minute per IP.
    """
    # Check if email already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = User(
        id=generate_uuid(),
        email=user_data.email,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate tokens
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token(data={"sub": user.id, "email": user.email})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return tokens.
    Rate limited to 10 requests per minute per IP.
    """
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not user.hashed_password or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token(data={"sub": user.id, "email": user.email})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(REFRESH_RATE_LIMIT)
async def refresh_token(request: Request, token_data: TokenRefresh, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.
    Rate limited to 20 requests per minute per IP.
    """
    token_info = decode_token(token_data.refresh_token)

    if not token_info or not token_info.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Verify it's a refresh token
    if token_info.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    user = db.query(User).filter(User.id == token_info.user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.id, "email": user.email})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info.
    """
    return UserResponse.model_validate(current_user)
