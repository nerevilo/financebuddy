"""
Analytics Router

API endpoints for spending analysis and insights.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import Optional
from datetime import date, timedelta
from collections import defaultdict

from ..core.database import get_db
from ..models import Transaction, Account, Institution
from ..schemas import SpendingByCategory, SpendingByMerchant

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_date_range(period: str) -> tuple[date, date]:
    """Get start and end dates for common periods."""
    today = date.today()

    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        end = today
    elif period == "last_week":
        start = today - timedelta(days=today.weekday() + 7)
        end = today - timedelta(days=today.weekday() + 1)
    elif period == "this_month":
        start = today.replace(day=1)
        end = today
    elif period == "last_month":
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
    elif period == "last_3_months":
        start = today - timedelta(days=90)
        end = today
    elif period == "last_6_months":
        start = today - timedelta(days=180)
        end = today
    elif period == "this_year":
        start = today.replace(month=1, day=1)
        end = today
    elif period == "last_year":
        start = today.replace(year=today.year - 1, month=1, day=1)
        end = today.replace(year=today.year - 1, month=12, day=31)
    else:
        # Default to this month
        start = today.replace(day=1)
        end = today

    return start, end


@router.get("/spending/by-category")
async def get_spending_by_category(
    period: str = Query(default="this_month"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    Get spending breakdown by category.

    Period options: this_week, last_week, this_month, last_month,
                   last_3_months, last_6_months, this_year, last_year
    """
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = get_date_range(period)

    # Get all expense transactions (negative amounts)
    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0  # Expenses are negative
        )
    ).all()

    # Aggregate by category
    category_totals = defaultdict(lambda: {"total": 0, "count": 0})

    for tx in transactions:
        category = tx.teller_category or "uncategorized"
        category_totals[category]["total"] += abs(tx.amount)
        category_totals[category]["count"] += 1

    # Calculate percentages
    grand_total = sum(cat["total"] for cat in category_totals.values())

    result = []
    for category, data in sorted(category_totals.items(), key=lambda x: x[1]["total"], reverse=True):
        percentage = (data["total"] / grand_total * 100) if grand_total > 0 else 0
        result.append(SpendingByCategory(
            category=category,
            total=round(data["total"], 2),
            count=data["count"],
            percentage=round(percentage, 1)
        ))

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_spending": round(grand_total, 2),
        "categories": result
    }


@router.get("/spending/by-merchant")
async def get_spending_by_merchant(
    period: str = Query(default="this_month"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db)
):
    """
    Get top merchants by spending.

    Returns the top N merchants sorted by total spending.
    """
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = get_date_range(period)

    # Get all expense transactions
    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0
        )
    ).all()

    # Aggregate by merchant
    merchant_totals = defaultdict(lambda: {"total": 0, "count": 0})

    for tx in transactions:
        merchant = tx.merchant_name or tx.description[:30] or "Unknown"
        merchant_totals[merchant]["total"] += abs(tx.amount)
        merchant_totals[merchant]["count"] += 1

    # Calculate percentages and sort
    grand_total = sum(m["total"] for m in merchant_totals.values())

    result = []
    sorted_merchants = sorted(merchant_totals.items(), key=lambda x: x[1]["total"], reverse=True)

    for merchant, data in sorted_merchants[:limit]:
        percentage = (data["total"] / grand_total * 100) if grand_total > 0 else 0
        result.append(SpendingByMerchant(
            merchant=merchant,
            total=round(data["total"], 2),
            count=data["count"],
            percentage=round(percentage, 1)
        ))

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_spending": round(grand_total, 2),
        "merchants": result
    }


@router.get("/spending/trends")
async def get_spending_trends(
    granularity: str = Query(default="monthly"),  # daily, weekly, monthly
    months: int = Query(default=6, le=24),
    db: Session = Depends(get_db)
):
    """Get spending trends over time."""
    start_date = date.today() - timedelta(days=months * 30)

    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= start_date
        )
    ).all()

    # Aggregate by period
    period_data = defaultdict(lambda: {"income": 0, "expenses": 0})

    for tx in transactions:
        if granularity == "monthly":
            period_key = tx.date.strftime("%Y-%m")
        elif granularity == "weekly":
            # Get ISO week number
            period_key = tx.date.strftime("%Y-W%W")
        else:  # daily
            period_key = tx.date.isoformat()

        if tx.amount > 0:
            period_data[period_key]["income"] += tx.amount
        else:
            period_data[period_key]["expenses"] += abs(tx.amount)

    result = []
    for period, data in sorted(period_data.items()):
        result.append({
            "period": period,
            "income": round(data["income"], 2),
            "expenses": round(data["expenses"], 2),
            "net": round(data["income"] - data["expenses"], 2)
        })

    return {"granularity": granularity, "trends": result}


@router.get("/comparison")
async def get_period_comparison(
    current_period: str = Query(default="this_month"),
    db: Session = Depends(get_db)
):
    """Compare spending between current and previous period."""
    current_start, current_end = get_date_range(current_period)

    # Calculate previous period
    period_length = (current_end - current_start).days
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length)

    # Get current period spending
    current_spending = db.query(func.sum(func.abs(Transaction.amount))).join(
        Account
    ).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= current_start,
            Transaction.date <= current_end,
            Transaction.amount < 0
        )
    ).scalar() or 0

    # Get previous period spending
    previous_spending = db.query(func.sum(func.abs(Transaction.amount))).join(
        Account
    ).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= previous_start,
            Transaction.date <= previous_end,
            Transaction.amount < 0
        )
    ).scalar() or 0

    change_amount = current_spending - previous_spending
    change_percentage = (change_amount / previous_spending * 100) if previous_spending > 0 else 0

    # Get category comparison
    categories_comparison = []

    # Current period by category
    current_by_cat = defaultdict(float)
    current_txs = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= current_start,
            Transaction.date <= current_end,
            Transaction.amount < 0
        )
    ).all()

    for tx in current_txs:
        cat = tx.teller_category or "uncategorized"
        current_by_cat[cat] += abs(tx.amount)

    # Previous period by category
    previous_by_cat = defaultdict(float)
    previous_txs = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= previous_start,
            Transaction.date <= previous_end,
            Transaction.amount < 0
        )
    ).all()

    for tx in previous_txs:
        cat = tx.teller_category or "uncategorized"
        previous_by_cat[cat] += abs(tx.amount)

    all_categories = set(current_by_cat.keys()) | set(previous_by_cat.keys())

    for cat in all_categories:
        curr = current_by_cat.get(cat, 0)
        prev = previous_by_cat.get(cat, 0)
        change = curr - prev
        pct_change = (change / prev * 100) if prev > 0 else (100 if curr > 0 else 0)

        categories_comparison.append({
            "category": cat,
            "current": round(curr, 2),
            "previous": round(prev, 2),
            "change": round(change, 2),
            "change_percentage": round(pct_change, 1)
        })

    # Sort by absolute change
    categories_comparison.sort(key=lambda x: abs(x["change"]), reverse=True)

    return {
        "current_period": {"start": current_start.isoformat(), "end": current_end.isoformat()},
        "previous_period": {"start": previous_start.isoformat(), "end": previous_end.isoformat()},
        "current_total": round(current_spending, 2),
        "previous_total": round(previous_spending, 2),
        "change_amount": round(change_amount, 2),
        "change_percentage": round(change_percentage, 1),
        "categories": categories_comparison[:10]  # Top 10 categories by change
    }


@router.get("/income-expenses")
async def get_income_expenses(
    period: str = Query(default="this_month"),
    db: Session = Depends(get_db)
):
    """Get income vs expenses summary."""
    start, end = get_date_range(period)

    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= start,
            Transaction.date <= end
        )
    ).all()

    income = sum(tx.amount for tx in transactions if tx.amount > 0)
    expenses = sum(abs(tx.amount) for tx in transactions if tx.amount < 0)
    net = income - expenses
    savings_rate = (net / income * 100) if income > 0 else 0

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "net": round(net, 2),
        "savings_rate": round(savings_rate, 1)
    }
