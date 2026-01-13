"""
Dashboard API Router

Provides dashboard analytics endpoints with optional Redis caching.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, List
from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.cache import get_cache, CacheService, DashboardCacheKeys, CacheTTL
from ..models import User
from ..services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/insight")
async def get_daily_insight(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
) -> Dict:
    """
    Get the daily actionable insight

    Returns the most relevant insight based on spending patterns
    """
    cache_key = DashboardCacheKeys.insight(current_user.id)

    # Try to get from cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    # Generate fresh data
    service = DashboardService(db, current_user.id)
    result = service.get_daily_insight()

    # Cache for 5 minutes
    await cache.set(cache_key, result, CacheTTL.DEFAULT)

    return result


@router.get("/velocity")
async def get_spending_velocity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
) -> Dict:
    """
    Get spending velocity for current month

    Shows:
    - Amount spent so far
    - Projection for month end
    - Comparison to last month
    - Daily average
    """
    cache_key = DashboardCacheKeys.velocity(current_user.id)

    # Try to get from cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    # Generate fresh data
    service = DashboardService(db, current_user.id)
    result = service.get_spending_velocity()

    # Cache for 5 minutes
    await cache.set(cache_key, result, CacheTTL.DEFAULT)

    return result


@router.get("/comparison")
async def get_monthly_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
) -> Dict:
    """
    Compare this month vs last month by category

    Shows side-by-side comparison with trends
    """
    cache_key = DashboardCacheKeys.comparison(current_user.id)

    # Try to get from cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    # Generate fresh data
    service = DashboardService(db, current_user.id)
    result = service.get_monthly_comparison()

    # Cache for 10 minutes (monthly data changes less frequently)
    await cache.set(cache_key, result, CacheTTL.MEDIUM)

    return result


@router.get("/categories")
async def get_category_breakdown(
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
) -> Dict:
    """
    Get spending breakdown by category

    Query params:
    - month: Month number (1-12), defaults to current month
    - year: Year, defaults to current year

    Returns categories sorted by amount with percentages
    """
    cache_key = DashboardCacheKeys.categories(current_user.id, month, year)

    # Try to get from cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    # Generate fresh data
    service = DashboardService(db, current_user.id)
    result = service.get_category_breakdown(month, year)

    # Cache for 5 minutes
    await cache.set(cache_key, result, CacheTTL.DEFAULT)

    return result


@router.get("/top-merchants")
async def get_top_merchants(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
) -> List[Dict]:
    """
    Get top merchants for current month

    Query params:
    - limit: Number of merchants to return (default 10)

    Returns merchants with visit counts and insights
    """
    cache_key = DashboardCacheKeys.top_merchants(current_user.id, limit)

    # Try to get from cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    # Generate fresh data
    service = DashboardService(db, current_user.id)
    result = service.get_top_merchants(limit)

    # Cache for 5 minutes
    await cache.set(cache_key, result, CacheTTL.DEFAULT)

    return result


@router.get("/recent-transactions")
async def get_recent_transactions(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """
    Get recent transactions

    Query params:
    - limit: Number of transactions to return (default 10)

    Returns recent enriched transactions
    """
    service = DashboardService(db, current_user.id)
    return service.get_recent_transactions(limit)


@router.get("/category/{category}/merchants")
async def get_category_merchants(
    category: str,
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Get merchant breakdown for a specific category

    Shows which merchants contribute to this category's spending
    """
    service = DashboardService(db, current_user.id)
    return service.get_category_breakdown_with_merchants(category, month, year)


@router.get("/transactions/by-period")
async def get_transactions_by_period(
    period: str = 'month',
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """
    Get transactions grouped by day for a time period

    Query params:
    - period: 'day', 'week', or 'month' (default: 'month')

    Returns transactions grouped by day with daily totals
    """
    service = DashboardService(db, current_user.id)
    return service.get_transactions_by_period(period)


@router.get("/spending-trend")
async def get_spending_trend(
    budget: float = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
) -> Dict:
    """
    Get daily cumulative spending for trend visualization

    Query params:
    - budget: Optional budget amount (defaults to last month's total)

    Returns:
    - Daily spending data with cumulative totals
    - Budget pace line
    - Last month comparison
    """
    cache_key = DashboardCacheKeys.spending_trend(current_user.id, budget)

    # Try to get from cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    # Generate fresh data
    service = DashboardService(db, current_user.id)
    result = service.get_spending_trend(budget)

    # Cache for 5 minutes
    await cache.set(cache_key, result, CacheTTL.DEFAULT)

    return result


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
) -> Dict:
    """
    Get all dashboard data in one call (for initial load)

    Returns:
    - insight
    - velocity
    - comparison
    - categories
    - top_merchants
    - recent_transactions
    - spending_trend
    """
    cache_key = DashboardCacheKeys.stats(current_user.id)

    # Try to get from cache
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    # Generate fresh data
    service = DashboardService(db, current_user.id)

    result = {
        'insight': service.get_daily_insight(),
        'velocity': service.get_spending_velocity(),
        'comparison': service.get_monthly_comparison(),
        'categories': service.get_category_breakdown(),
        'top_merchants': service.get_top_merchants(5),
        'recent_transactions': service.get_recent_transactions(5),
        'spending_trend': service.get_spending_trend()
    }

    # Cache for 5 minutes
    await cache.set(cache_key, result, CacheTTL.DEFAULT)

    return result
