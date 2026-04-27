"""
Redis Caching Module

Provides optional Redis caching for expensive dashboard queries.
If Redis is not configured, falls back to in-memory LRU cache.
"""
import json
import logging
import time
from typing import Any, Optional, Tuple
from collections import OrderedDict
import threading

logger = logging.getLogger(__name__)

# Redis client - initialized lazily
_redis_client = None
_redis_available = False


class InMemoryCache:
    """
    Simple in-memory LRU cache with TTL support.
    Used as fallback when Redis is not available.
    Thread-safe.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()  # key -> (value, expiry_time)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value if exists and not expired."""
        with self._lock:
            if key not in self._cache:
                return None

            value, expiry = self._cache[key]
            if expiry and time.time() > expiry:
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value with optional TTL."""
        with self._lock:
            expiry = time.time() + ttl if ttl else None

            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, expiry)

            # Evict oldest if over size
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

            return True

    def delete(self, key: str) -> bool:
        """Delete a key."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """Clear all entries."""
        with self._lock:
            self._cache.clear()


# In-memory cache fallback
_memory_cache = InMemoryCache(max_size=5000)


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

    def __init__(self, prefix: str = "ledgi"):
        """
        Initialize cache service.

        Args:
            prefix: Key prefix for all cache keys (default: "ledgi")
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
        full_key = self._make_key(key)

        # Try Redis first
        try:
            client = await _get_redis()
            if client is not None:
                value = await client.get(full_key)
                if value is not None:
                    return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis get error for key '{key}': {e}")

        # Fallback to in-memory cache
        return _memory_cache.get(full_key)

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
        full_key = self._make_key(key)

        # Always store in memory cache (fallback)
        _memory_cache.set(full_key, value, ttl)

        # Try Redis as primary
        try:
            client = await _get_redis()
            if client is not None:
                serialized = json.dumps(value, default=str)
                await client.set(full_key, serialized, ex=ttl)
                return True
        except Exception as e:
            logger.warning(f"Redis set error for key '{key}': {e}")

        return True  # Still successful via memory cache

    async def delete(self, key: str) -> bool:
        """
        Delete a cached value.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        full_key = self._make_key(key)

        # Delete from memory cache
        _memory_cache.delete(full_key)

        # Try Redis
        try:
            client = await _get_redis()
            if client is not None:
                await client.delete(full_key)
        except Exception as e:
            logger.warning(f"Redis delete error for key '{key}': {e}")

        return True

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

    @staticmethod
    def recurring_payments(user_id: str, limit: int = 20) -> str:
        """Key for recurring payments."""
        return f"dashboard:{user_id}:recurring_payments:{limit}"


# TTL constants (in seconds)
class CacheTTL:
    """Cache TTL constants for different data types."""

    SHORT = 60  # 1 minute - for very dynamic data
    DEFAULT = 300  # 5 minutes - default dashboard data
    MEDIUM = 600  # 10 minutes - for monthly comparisons
    LONG = 1800  # 30 minutes - for historical data
    LLM_ENRICHMENT = 86400 * 7  # 7 days - merchant categorization rarely changes


# Cache key builders for LLM enrichment
class EnrichmentCacheKeys:
    """Helper class for building consistent enrichment cache keys."""

    @staticmethod
    def _normalize_description(description: str) -> str:
        """
        Normalize description for consistent cache keys.

        OPTIMIZED: Extract canonical merchant name for better cache hit rates.

        Examples:
        - "STARBUCKS #12345 NYC" → "STARBUCKS"
        - "STARBUCKS COFFEE #98765 LA" → "STARBUCKS" (cache HIT!)
        - "COSTCO GAS #1234" → "COSTCO_GAS"
        - "COSTCO WHSE #5678" → "COSTCO_WHSE"
        """
        import re
        import hashlib

        # 1. Uppercase and strip
        normalized = description.upper().strip()

        # 2. Remove common transaction prefixes
        prefixes = [
            "DEBIT CARD PURCHASE - ",
            "CREDIT CARD PURCHASE - ",
            "ONLINE PURCHASE - ",
            "PURCHASE - ",
            "POS PURCHASE ",
            "POS ",
            "ACH ",
            "CHECKCARD ",
            "VISA ",
            "MASTERCARD ",
        ]
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break

        # 3. Remove ALL numbers (store numbers, locations, dates, etc.)
        # This is more aggressive than before but increases cache hits
        normalized = re.sub(r'#?\d{3,}', '', normalized)

        # 4. Remove common suffixes that don't help identify merchants
        suffixes = [
            ' COFFEE', ' STORE', ' STORES', ' WHSE', ' WAREHOUSE',
            ' INC', ' LLC', ' CORP', ' CO', ' LTD',
            ' COM', '.COM', ' WEB', ' ONLINE',
        ]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break

        # 5. Clean up special characters and whitespace
        normalized = re.sub(r'[#*@.,\-_]+', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        # 6. Take first 2-3 significant words only (skip tiny words)
        words = normalized.split()
        significant_words = [w for w in words if len(w) > 2][:3]

        if significant_words:
            cache_key = '_'.join(significant_words)
        else:
            # Fallback: use first 2 words if no significant words found
            cache_key = '_'.join(words[:2]) if words else 'UNKNOWN'

        # 7. Limit length, hash if too long
        if len(cache_key) > 40:
            return hashlib.md5(cache_key.encode()).hexdigest()[:16]

        return cache_key[:40]

    @staticmethod
    def llm_result(description: str) -> str:
        """Key for LLM enrichment result."""
        normalized = EnrichmentCacheKeys._normalize_description(description)
        return f"enrichment:llm:{normalized}"

    @staticmethod
    def gemini_result(description: str) -> str:
        """Key for Gemini enrichment result."""
        normalized = EnrichmentCacheKeys._normalize_description(description)
        return f"enrichment:gemini:{normalized}"
