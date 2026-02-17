"""
Analytics Router

API endpoints for spending analysis and insights.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, Query as SQLQuery
from sqlalchemy import func, and_, or_, not_
from typing import Optional
from datetime import date, timedelta

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models import Transaction, Account, Institution, User
from ..schemas import SpendingByCategory, SpendingByMerchant

router = APIRouter(prefix="/analytics", tags=["analytics"])


def apply_transfer_filters(query: SQLQuery) -> SQLQuery:
    """
    Apply SQL-level filters to exclude obvious transfers.

    This filters out:
    - Transactions with teller_category = 'transfer'
    - Transactions flagged as is_transfer = True
    - Common transfer patterns in description

    More complex transfer detection (account matching, custom rules)
    still happens in Python for edge cases.
    """
    # Categories that indicate transfers (not real spending)
    transfer_categories = ['transfer', 'investment']

    # Common transfer keywords to filter at SQL level
    transfer_keywords = [
        '%CREDIT CARD PAYMENT%', '%CC PAYMENT%', '%CARD PAYMENT%',
        '%INTERNAL TRANSFER%', '%BETWEEN ACCOUNTS%',
        '%LOAN PAYMENT%', '%MORTGAGE PAYMENT%'
    ]

    # Base exclusions
    query = query.filter(
        or_(
            Transaction.teller_category.is_(None),
            not_(Transaction.teller_category.in_(transfer_categories))
        )
    ).filter(
        or_(
            Transaction.is_transfer.is_(None),
            Transaction.is_transfer == False
        )
    )

    # Build OR condition for keyword exclusions
    keyword_conditions = [Transaction.description.ilike(kw) for kw in transfer_keywords]
    if keyword_conditions:
        query = query.filter(not_(or_(*keyword_conditions)))

    return query


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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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

    # Use SQL aggregation instead of loading all transactions into memory
    base_query = db.query(
        func.coalesce(Transaction.teller_category, 'uncategorized').label('category'),
        func.sum(func.abs(Transaction.amount)).label('total'),
        func.count(Transaction.id).label('count')
    ).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0  # Expenses are negative
        )
    )

    # Apply SQL-level transfer filters
    base_query = apply_transfer_filters(base_query)

    # Group by category and execute
    results = base_query.group_by(
        func.coalesce(Transaction.teller_category, 'uncategorized')
    ).limit(50).all()

    # Calculate percentages
    grand_total = sum(r.total for r in results) if results else 0

    result = []
    for r in sorted(results, key=lambda x: x.total, reverse=True):
        percentage = (r.total / grand_total * 100) if grand_total > 0 else 0
        result.append(SpendingByCategory(
            category=r.category,
            total=round(float(r.total), 2),
            count=r.count,
            percentage=round(percentage, 1)
        ))

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_spending": round(float(grand_total), 2),
        "categories": result
    }


@router.get("/spending/by-merchant")
async def get_spending_by_merchant(
    period: str = Query(default="this_month"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get top merchants by spending.

    Returns the top N merchants sorted by total spending.
    """
    if start_date and end_date:
        start, end = start_date, end_date
    else:
        start, end = get_date_range(period)

    # Use SQL aggregation with COALESCE for merchant name
    base_query = db.query(
        func.coalesce(
            Transaction.merchant_name,
            func.substring(Transaction.description, 1, 30),
            'Unknown'
        ).label('merchant'),
        func.sum(func.abs(Transaction.amount)).label('total'),
        func.count(Transaction.id).label('count')
    ).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0
        )
    )

    # Apply SQL-level transfer filters
    base_query = apply_transfer_filters(base_query)

    # Group by merchant, order by total, and limit
    results = base_query.group_by(
        func.coalesce(
            Transaction.merchant_name,
            func.substring(Transaction.description, 1, 30),
            'Unknown'
        )
    ).order_by(func.sum(func.abs(Transaction.amount)).desc()).limit(limit).all()

    # Calculate grand total for percentages
    total_query = db.query(
        func.sum(func.abs(Transaction.amount))
    ).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0
        )
    )
    total_query = apply_transfer_filters(total_query)
    grand_total = total_query.scalar() or 0

    result = []
    for r in results:
        percentage = (float(r.total) / float(grand_total) * 100) if grand_total > 0 else 0
        result.append(SpendingByMerchant(
            merchant=r.merchant,
            total=round(float(r.total), 2),
            count=r.count,
            percentage=round(percentage, 1)
        ))

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_spending": round(float(grand_total), 2),
        "merchants": result
    }


@router.get("/spending/trends")
async def get_spending_trends(
    granularity: str = Query(default="monthly", pattern="^(daily|weekly|monthly)$"),
    months: int = Query(default=6, le=24),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get spending trends over time."""
    start_date_val = date.today() - timedelta(days=months * 30)

    # Determine period extraction based on granularity
    if granularity == "monthly":
        period_expr = func.to_char(Transaction.date, 'YYYY-MM')
    elif granularity == "weekly":
        period_expr = func.to_char(Transaction.date, 'YYYY-"W"IW')
    else:  # daily
        period_expr = func.to_char(Transaction.date, 'YYYY-MM-DD')

    # Query for income (positive amounts)
    income_query = db.query(
        period_expr.label('period'),
        func.sum(Transaction.amount).label('income')
    ).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            Transaction.date >= start_date_val,
            Transaction.amount > 0
        )
    )
    income_query = apply_transfer_filters(income_query)
    income_results = {r.period: float(r.income) for r in income_query.group_by(period_expr).all()}

    # Query for expenses (negative amounts)
    expense_query = db.query(
        period_expr.label('period'),
        func.sum(func.abs(Transaction.amount)).label('expenses')
    ).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            Transaction.date >= start_date_val,
            Transaction.amount < 0
        )
    )
    expense_query = apply_transfer_filters(expense_query)
    expense_results = {r.period: float(r.expenses) for r in expense_query.group_by(period_expr).all()}

    # Combine results
    all_periods = set(income_results.keys()) | set(expense_results.keys())
    result = []
    for period in sorted(all_periods):
        income = income_results.get(period, 0)
        expenses = expense_results.get(period, 0)
        result.append({
            "period": period,
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "net": round(income - expenses, 2)
        })

    return {"granularity": granularity, "trends": result}


@router.get("/comparison")
async def get_period_comparison(
    current_period: str = Query(default="this_month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare spending between current and previous period."""
    current_start, current_end = get_date_range(current_period)

    # Calculate previous period
    period_length = (current_end - current_start).days
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=period_length)

    def get_period_totals(start: date, end: date):
        """Get total spending and by-category breakdown using SQL aggregation."""
        # Total spending
        total_query = db.query(
            func.sum(func.abs(Transaction.amount))
        ).join(Account).join(Institution).filter(
            and_(
                Institution.status == "active",
                Institution.user_id == current_user.id,
                Transaction.date >= start,
                Transaction.date <= end,
                Transaction.amount < 0
            )
        )
        total_query = apply_transfer_filters(total_query)
        total = total_query.scalar() or 0

        # By category
        cat_query = db.query(
            func.coalesce(Transaction.teller_category, 'uncategorized').label('category'),
            func.sum(func.abs(Transaction.amount)).label('total')
        ).join(Account).join(Institution).filter(
            and_(
                Institution.status == "active",
                Institution.user_id == current_user.id,
                Transaction.date >= start,
                Transaction.date <= end,
                Transaction.amount < 0
            )
        )
        cat_query = apply_transfer_filters(cat_query)
        by_cat = {r.category: float(r.total) for r in cat_query.group_by(
            func.coalesce(Transaction.teller_category, 'uncategorized')
        ).limit(100).all()}

        return float(total), by_cat

    current_spending, current_by_cat = get_period_totals(current_start, current_end)
    previous_spending, previous_by_cat = get_period_totals(previous_start, previous_end)

    change_amount = current_spending - previous_spending
    change_percentage = (change_amount / previous_spending * 100) if previous_spending > 0 else 0

    # Build category comparison
    all_categories = set(current_by_cat.keys()) | set(previous_by_cat.keys())
    categories_comparison = []

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get income vs expenses summary."""
    start, end = get_date_range(period)

    # Query for income using SQL aggregation
    income_query = db.query(
        func.sum(Transaction.amount)
    ).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount > 0
        )
    )
    income_query = apply_transfer_filters(income_query)
    income = float(income_query.scalar() or 0)

    # Query for expenses using SQL aggregation
    expense_query = db.query(
        func.sum(func.abs(Transaction.amount))
    ).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount < 0
        )
    )
    expense_query = apply_transfer_filters(expense_query)
    expenses = float(expense_query.scalar() or 0)

    net = income - expenses
    savings_rate = (net / income * 100) if income > 0 else 0

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "net": round(net, 2),
        "savings_rate": round(savings_rate, 1)
    }
