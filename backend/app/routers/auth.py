"""
Authentication Router

Handles user registration, login, token refresh, password reset, and current user info.
Rate limiting is applied to protect against brute force attacks.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, decode_token,
    create_password_reset_token, verify_password_reset_token
)
from ..core.auth import get_current_user
from ..core.rate_limiter import (
    limiter,
    REGISTER_RATE_LIMIT,
    LOGIN_RATE_LIMIT,
    REFRESH_RATE_LIMIT,
    PASSWORD_RESET_REQUEST_LIMIT,
    PASSWORD_RESET_CONFIRM_LIMIT
)
from ..models import User
from ..models.models import generate_uuid
from ..schemas import (
    UserRegister, UserLogin, TokenRefresh, TokenResponse, UserResponse,
    PasswordResetRequest, PasswordResetConfirm, PasswordResetResponse
)
from ..services.email_service import EmailService

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

    # Always run password verification to prevent timing attacks
    # If no user, verify against a dummy hash so response time is consistent
    dummy_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYA/gBVK5Li6"
    password_valid = verify_password(
        credentials.password,
        user.hashed_password if user and user.hashed_password else dummy_hash
    )

    # Determine specific error reason (for logging/monitoring, not exposed to user)
    error_reason = None
    if not user:
        error_reason = "account_not_found"
    elif not password_valid:
        error_reason = "invalid_password"

    if error_reason:
        # Specific reason available for logging/monitoring but not exposed to client
        # import logging; logging.warning(f"Login failed: {error_reason} for {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
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


@router.post("/forgot-password", response_model=PasswordResetResponse)
@limiter.limit(PASSWORD_RESET_REQUEST_LIMIT)
async def forgot_password(
    request: Request,
    body: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset email.

    Always returns success message to prevent email enumeration.
    Rate limited to 3 requests per minute per IP.
    """
    # Look up user (but don't reveal if they exist)
    user = db.query(User).filter(User.email == body.email).first()

    if user and user.is_active:
        # Generate reset token and send email
        reset_token = create_password_reset_token(body.email)
        await EmailService.send_password_reset_email(body.email, reset_token)

    # Always return same response to prevent enumeration
    return PasswordResetResponse(
        message="If an account exists with that email, you will receive a password reset link."
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
@limiter.limit(PASSWORD_RESET_CONFIRM_LIMIT)
async def reset_password(
    request: Request,
    body: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset password using the token from email.

    Rate limited to 5 requests per minute per IP.
    """
    # Verify token
    email = verify_password_reset_token(body.token)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Find user
    user = db.query(User).filter(User.email == email).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Update password
    user.hashed_password = get_password_hash(body.new_password)
    user.updated_at = datetime.utcnow()
    db.commit()

    return PasswordResetResponse(message="Password has been reset successfully")
