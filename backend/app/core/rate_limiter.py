"""
Rate Limiting Module

Configures rate limiting for API endpoints using slowapi.
Provides protection against brute force attacks on authentication endpoints.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Create the limiter instance using client IP for rate limiting
limiter = Limiter(key_func=get_remote_address)

# Rate limit configurations for auth endpoints
REGISTER_RATE_LIMIT = "5/minute"  # 5 requests per minute per IP
LOGIN_RATE_LIMIT = "10/minute"    # 10 requests per minute per IP
REFRESH_RATE_LIMIT = "20/minute"  # 20 requests per minute per IP
