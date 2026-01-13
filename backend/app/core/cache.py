"""
Redis Caching Module

Provides optional Redis caching for expensive dashboard queries.
If Redis is not configured, caching operations are no-ops and the app
continues to work normally.
"""
import json
import logging
from typing import Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Redis client - initialized lazily
_redis_client = None
_redis_available = False


async def _get_redis():
    """Get or create Redis connection."""
    global _redis_client, _redis_available

    if _redis_client is not None:
        return _redis_client if _redis_available else None

    from .config import get_settings
    settings = get_settings()

    if not settings.redis_url:
        logger.info("Redis URL not configured - caching disabled")
        _redis_available = False
        return None

    try:
        import redis.asyncio as redis
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        # Test connection
        await _redis_client.ping()
        _redis_available = True
        logger.info("Redis connection established - caching enabled")
        return _redis_client
    except ImportError:
        logger.warning("redis package not installed - caching disabled")
        _redis_available = False
        return None
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e} - caching disabled")
        _redis_available = False
        return None


class CacheService:
    """
    Redis cache service with graceful degradation.

    If Redis is unavailable, all operations silently no-op and return None/False.
    This ensures the application works with or without Redis.
    """

    def __init__(self, prefix: str = "financebuddy"):
        """
        Initialize cache service.

        Args:
            prefix: Key prefix for all cache keys (default: "financebuddy")
        """
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Generate full cache key with prefix."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or error
        """
        try:
            client = await _get_redis()
            if client is None:
                return None

            full_key = self._make_key(key)
            value = await client.get(full_key)

            if value is None:
                return None

            return json.loads(value)
        except Exception as e:
            logger.warning(f"Cache get error for key '{key}': {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set a cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: 300 = 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        try:
            client = await _get_redis()
            if client is None:
                return False

            full_key = self._make_key(key)
            serialized = json.dumps(value, default=str)
            await client.set(full_key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a cached value.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            client = await _get_redis()
            if client is None:
                return False

            full_key = self._make_key(key)
            await client.delete(full_key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key '{key}': {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "user:123:*")

        Returns:
            Number of keys deleted
        """
        try:
            client = await _get_redis()
            if client is None:
                return 0

            full_pattern = self._make_key(pattern)
            deleted = 0

            # Use SCAN to find matching keys (safe for production)
            async for key in client.scan_iter(match=full_pattern):
                await client.delete(key)
                deleted += 1

            if deleted > 0:
                logger.debug(f"Invalidated {deleted} cache keys matching '{pattern}'")

            return deleted
        except Exception as e:
            logger.warning(f"Cache invalidate_pattern error for '{pattern}': {e}")
            return 0

    async def invalidate_user_dashboard(self, user_id: str) -> int:
        """
        Invalidate all dashboard cache for a specific user.

        Args:
            user_id: User ID

        Returns:
            Number of keys deleted
        """
        return await self.invalidate_pattern(f"dashboard:{user_id}:*")


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache() -> CacheService:
    """
    Dependency function to get cache service.

    Usage:
        @router.get("/endpoint")
        async def endpoint(cache: CacheService = Depends(get_cache)):
            cached = await cache.get("my_key")
            ...
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# Cache key builders for dashboard
class DashboardCacheKeys:
    """Helper class for building consistent dashboard cache keys."""

    @staticmethod
    def stats(user_id: str) -> str:
        """Key for full dashboard stats."""
        return f"dashboard:{user_id}:stats"

    @staticmethod
    def insight(user_id: str) -> str:
        """Key for daily insight."""
        return f"dashboard:{user_id}:insight"

    @staticmethod
    def velocity(user_id: str) -> str:
        """Key for spending velocity."""
        return f"dashboard:{user_id}:velocity"

    @staticmethod
    def comparison(user_id: str) -> str:
        """Key for monthly comparison."""
        return f"dashboard:{user_id}:comparison"

    @staticmethod
    def categories(user_id: str, month: Optional[int] = None, year: Optional[int] = None) -> str:
        """Key for category breakdown."""
        if month and year:
            return f"dashboard:{user_id}:categories:{year}:{month}"
        return f"dashboard:{user_id}:categories:current"

    @staticmethod
    def top_merchants(user_id: str, limit: int) -> str:
        """Key for top merchants."""
        return f"dashboard:{user_id}:top_merchants:{limit}"

    @staticmethod
    def spending_trend(user_id: str, budget: Optional[float] = None) -> str:
        """Key for spending trend."""
        if budget:
            return f"dashboard:{user_id}:spending_trend:{budget}"
        return f"dashboard:{user_id}:spending_trend:default"


# TTL constants (in seconds)
class CacheTTL:
    """Cache TTL constants for different data types."""

    SHORT = 60  # 1 minute - for very dynamic data
    DEFAULT = 300  # 5 minutes - default dashboard data
    MEDIUM = 600  # 10 minutes - for monthly comparisons
    LONG = 1800  # 30 minutes - for historical data
