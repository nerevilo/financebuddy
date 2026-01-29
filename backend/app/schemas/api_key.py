"""
Pydantic schemas for API key management.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class APIKeyCreate(BaseModel):
    """Request body for creating a new API key."""
    name: str = Field(..., min_length=1, max_length=100, description="Friendly name for the key")
    scopes: Optional[List[str]] = Field(
        default=["*"],
        description="Permission scopes. Use ['*'] for full access or specific scopes like ['transactions:read']"
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        ge=1,
        le=365,
        description="Days until expiration. None for no expiration."
    )


class APIKeyUpdate(BaseModel):
    """Request body for updating an API key."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None


class APIKeyResponse(BaseModel):
    """Response containing API key info (without the actual key)."""
    id: str
    name: str
    key_prefix: str  # e.g., "fb_sk_a1b2" for identification
    scopes: List[str]
    tier: str
    is_active: bool
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreatedResponse(BaseModel):
    """Response when creating a new API key - includes the raw key (shown only once)."""
    id: str
    name: str
    key: str  # The full API key - only shown once!
    key_prefix: str
    scopes: List[str]
    tier: str
    expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Response containing list of API keys."""
    keys: List[APIKeyResponse]
    total: int


# LLM API Response Schemas

class RateLimitInfo(BaseModel):
    """Rate limit information included in API responses."""
    remaining_minute: int
    remaining_day: int
    limit_minute: int
    limit_day: int
    reset_minute: int  # Unix timestamp
    reset_day: int  # Unix timestamp


class APIResponseMeta(BaseModel):
    """Metadata included in all LLM API responses."""
    request_id: str
    timestamp: datetime
    rate_limit: Optional[RateLimitInfo] = None


class APIResponse(BaseModel):
    """Standard wrapper for all LLM API responses."""
    success: bool = True
    data: dict
    meta: APIResponseMeta


class APIErrorResponse(BaseModel):
    """Error response for LLM API."""
    success: bool = False
    error: str
    message: str
    meta: APIResponseMeta
