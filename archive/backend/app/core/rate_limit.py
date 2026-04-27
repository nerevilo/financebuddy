"""
Tiered rate limiting for API key access.

Supports Redis for distributed rate limiting with graceful fallback to in-memory.
"""
import logging
import time
from typing import Optional, Dict, Tuple
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


# Rate limit tiers (requests per minute / requests per day)
RATE_LIMITS = {
    "beta": {"requests_per_minute": 1000, "requests_per_day": 50000},
    "free": {"requests_per_minute": 100, "requests_per_day": 5000},
    "pro": {"requests_per_minute": 1000, "requests_per_day": 100000},
}


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window.

    Used when Redis is not available. Note: Not suitable for
    distributed deployments - use Redis for that.
    """

    def __init__(self):
        self._minute_counts: Dict[str, list] = defaultdict(list)
        self._day_counts: Dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def _cleanup_old_entries(self, entries: list, window_seconds: int) -> list:
        """Remove entries older than the window."""
        cutoff = time.time() - window_seconds
        return [t for t in entries if t > cutoff]

    def check_rate_limit(self, key: str, tier: str) -> Tuple[bool, dict]:
        """
        Check if request is within rate limits.

        Args:
            key: Unique identifier (e.g., api_key_id)
            tier: Rate limit tier (beta, free, pro)

        Returns:
            Tuple of (allowed, info_dict)
        """
        limits = RATE_LIMITS.get(tier, RATE_LIMITS["free"])
        now = time.time()

        with self._lock:
            # Cleanup and count minute window
            minute_key = f"{key}:minute"
            self._minute_counts[minute_key] = self._cleanup_old_entries(
                self._minute_counts[minute_key], 60
            )
            minute_count = len(self._minute_counts[minute_key])

            # Cleanup and count day window
            day_key = f"{key}:day"
            self._day_counts[day_key] = self._cleanup_old_entries(
                self._day_counts[day_key], 86400
            )
            day_count = len(self._day_counts[day_key])

            # Check limits
            minute_limit = limits["requests_per_minute"]
            day_limit = limits["requests_per_day"]

            if minute_count >= minute_limit:
                return False, {
                    "remaining_minute": 0,
                    "remaining_day": max(0, day_limit - day_count),
                    "reset_minute": int(now + 60),
                    "reset_day": int(now + 86400),
                    "limit_minute": minute_limit,
                    "limit_day": day_limit,
                }

            if day_count >= day_limit:
                return False, {
                    "remaining_minute": max(0, minute_limit - minute_count),
                    "remaining_day": 0,
                    "reset_minute": int(now + 60),
                    "reset_day": int(now + 86400),
                    "limit_minute": minute_limit,
                    "limit_day": day_limit,
                }

            # Record this request
            self._minute_counts[minute_key].append(now)
            self._day_counts[day_key].append(now)

            return True, {
                "remaining_minute": minute_limit - minute_count - 1,
                "remaining_day": day_limit - day_count - 1,
                "reset_minute": int(now + 60),
                "reset_day": int(now + 86400),
                "limit_minute": minute_limit,
                "limit_day": day_limit,
            }


class RedisRateLimiter:
    """
    Redis-based rate limiter using sliding window.

    Suitable for distributed deployments.
    """

    def __init__(self, prefix: str = "ledgi:ratelimit"):
        self.prefix = prefix

    async def check_rate_limit(self, key: str, tier: str) -> Tuple[bool, dict]:
        """
        Check if request is within rate limits.

        Args:
            key: Unique identifier (e.g., api_key_id)
            tier: Rate limit tier (beta, free, pro)

        Returns:
            Tuple of (allowed, info_dict)
        """
        from .cache import _get_redis

        client = await _get_redis()
        if client is None:
            # Fall back to allowing (no distributed limiting)
            limits = RATE_LIMITS.get(tier, RATE_LIMITS["free"])
            return True, {
                "remaining_minute": limits["requests_per_minute"],
                "remaining_day": limits["requests_per_day"],
                "reset_minute": int(time.time() + 60),
                "reset_day": int(time.time() + 86400),
                "limit_minute": limits["requests_per_minute"],
                "limit_day": limits["requests_per_day"],
            }

        limits = RATE_LIMITS.get(tier, RATE_LIMITS["free"])
        now = time.time()

        minute_key = f"{self.prefix}:{key}:minute"
        day_key = f"{self.prefix}:{key}:day"

        try:
            # Use pipeline for atomic operations
            pipe = client.pipeline()

            # Remove old entries from minute window
            pipe.zremrangebyscore(minute_key, 0, now - 60)
            # Remove old entries from day window
            pipe.zremrangebyscore(day_key, 0, now - 86400)
            # Count current entries
            pipe.zcard(minute_key)
            pipe.zcard(day_key)

            results = await pipe.execute()
            minute_count = results[2]
            day_count = results[3]

            minute_limit = limits["requests_per_minute"]
            day_limit = limits["requests_per_day"]

            if minute_count >= minute_limit:
                return False, {
                    "remaining_minute": 0,
                    "remaining_day": max(0, day_limit - day_count),
                    "reset_minute": int(now + 60),
                    "reset_day": int(now + 86400),
                    "limit_minute": minute_limit,
                    "limit_day": day_limit,
                }

            if day_count >= day_limit:
                return False, {
                    "remaining_minute": max(0, minute_limit - minute_count),
                    "remaining_day": 0,
                    "reset_minute": int(now + 60),
                    "reset_day": int(now + 86400),
                    "limit_minute": minute_limit,
                    "limit_day": day_limit,
                }

            # Record this request
            pipe2 = client.pipeline()
            pipe2.zadd(minute_key, {str(now): now})
            pipe2.zadd(day_key, {str(now): now})
            pipe2.expire(minute_key, 120)  # 2 minute TTL
            pipe2.expire(day_key, 90000)  # 25 hour TTL
            await pipe2.execute()

            return True, {
                "remaining_minute": minute_limit - minute_count - 1,
                "remaining_day": day_limit - day_count - 1,
                "reset_minute": int(now + 60),
                "reset_day": int(now + 86400),
                "limit_minute": minute_limit,
                "limit_day": day_limit,
            }

        except Exception as e:
            logger.warning(f"Redis rate limit error: {e}")
            # Allow on error
            return True, {
                "remaining_minute": limits["requests_per_minute"],
                "remaining_day": limits["requests_per_day"],
                "reset_minute": int(now + 60),
                "reset_day": int(now + 86400),
                "limit_minute": limits["requests_per_minute"],
                "limit_day": limits["requests_per_day"],
            }


# Global instances
_memory_limiter: Optional[InMemoryRateLimiter] = None
_redis_limiter: Optional[RedisRateLimiter] = None


def get_memory_limiter() -> InMemoryRateLimiter:
    """Get the in-memory rate limiter singleton."""
    global _memory_limiter
    if _memory_limiter is None:
        _memory_limiter = InMemoryRateLimiter()
    return _memory_limiter


def get_redis_limiter() -> RedisRateLimiter:
    """Get the Redis rate limiter singleton."""
    global _redis_limiter
    if _redis_limiter is None:
        _redis_limiter = RedisRateLimiter()
    return _redis_limiter


async def check_api_rate_limit(api_key_id: str, tier: str) -> dict:
    """
    Check rate limit for an API key.

    Tries Redis first, falls back to in-memory.

    Args:
        api_key_id: The API key ID
        tier: The rate limit tier

    Returns:
        Rate limit info dict

    Raises:
        HTTPException 429 if rate limited
    """
    # Try Redis first
    redis_limiter = get_redis_limiter()
    allowed, info = await redis_limiter.check_rate_limit(api_key_id, tier)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please slow down.",
                "rate_limit": info,
            },
            headers={
                "X-RateLimit-Limit-Minute": str(info["limit_minute"]),
                "X-RateLimit-Remaining-Minute": str(info["remaining_minute"]),
                "X-RateLimit-Reset-Minute": str(info["reset_minute"]),
                "Retry-After": "60",
            },
        )

    return info
