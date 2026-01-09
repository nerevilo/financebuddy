"""
Dashboard API Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, List
from ..core.database import get_db
from ..services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/insight")
async def get_daily_insight(db: Session = Depends(get_db)) -> Dict:
    """
    Get the daily actionable insight

    Returns the most relevant insight based on spending patterns
    """
    service = DashboardService(db)
    return service.get_daily_insight()


@router.get("/velocity")
async def get_spending_velocity(db: Session = Depends(get_db)) -> Dict:
    """
    Get spending velocity for current month

    Shows:
    - Amount spent so far
    - Projection for month end
    - Comparison to last month
    - Daily average
    """
    service = DashboardService(db)
    return service.get_spending_velocity()


@router.get("/comparison")
async def get_monthly_comparison(db: Session = Depends(get_db)) -> Dict:
    """
    Compare this month vs last month by category

    Shows side-by-side comparison with trends
    """
    service = DashboardService(db)
    return service.get_monthly_comparison()


@router.get("/categories")
async def get_category_breakdown(
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get spending breakdown by category

    Query params:
    - month: Month number (1-12), defaults to current month
    - year: Year, defaults to current year

    Returns categories sorted by amount with percentages
    """
    service = DashboardService(db)
    return service.get_category_breakdown(month, year)


@router.get("/top-merchants")
async def get_top_merchants(
    limit: int = 10,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """
    Get top merchants for current month

    Query params:
    - limit: Number of merchants to return (default 10)

    Returns merchants with visit counts and insights
    """
    service = DashboardService(db)
    return service.get_top_merchants(limit)


@router.get("/recent-transactions")
async def get_recent_transactions(
    limit: int = 10,
    db: Session = Depends(get_db)
) -> List[Dict]:
    """
    Get recent transactions

    Query params:
    - limit: Number of transactions to return (default 10)

    Returns recent enriched transactions
    """
    service = DashboardService(db)
    return service.get_recent_transactions(limit)


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)) -> Dict:
    """
    Get all dashboard data in one call (for initial load)

    Returns:
    - insight
    - velocity
    - comparison
    - categories
    - top_merchants
    - recent_transactions
    """
    service = DashboardService(db)

    return {
        'insight': service.get_daily_insight(),
        'velocity': service.get_spending_velocity(),
        'comparison': service.get_monthly_comparison(),
        'categories': service.get_category_breakdown(),
        'top_merchants': service.get_top_merchants(5),
        'recent_transactions': service.get_recent_transactions(5)
    }
