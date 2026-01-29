"""
LLM-Friendly API Router

Clean, structured endpoints optimized for programmatic access by LLMs and other applications.
All endpoints support API key authentication and return consistent JSON responses.
"""
import uuid
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..core.auth import get_current_user_and_api_key
from ..core.rate_limit import check_api_rate_limit
from ..models import User
from ..models.api_key import APIKey
from ..models.models import (
    Transaction, Account, Institution, Goal, IncomeSource, Insight,
    TransactionTag, MerchantCategoryRule
)
from ..services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/v1", tags=["LLM API"])


def make_response(data: dict, rate_limit_info: Optional[dict] = None) -> dict:
    """Create consistent API response wrapper."""
    meta = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if rate_limit_info:
        meta["rate_limit"] = {
            "remaining_minute": rate_limit_info.get("remaining_minute", 0),
            "remaining_day": rate_limit_info.get("remaining_day", 0),
            "limit_minute": rate_limit_info.get("limit_minute", 0),
            "limit_day": rate_limit_info.get("limit_day", 0),
        }

    return {
        "success": True,
        "data": data,
        "meta": meta,
    }


async def get_user_with_rate_limit(
    auth_result: Tuple[User, Optional[APIKey]] = Depends(get_current_user_and_api_key),
) -> Tuple[User, Optional[dict]]:
    """Get user and apply rate limiting if using API key."""
    user, api_key = auth_result

    rate_limit_info = None
    if api_key:
        # Apply rate limiting for API key access
        rate_limit_info = await check_api_rate_limit(api_key.id, api_key.tier)

    return user, rate_limit_info


@router.get("/summary")
async def get_summary(
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """
    Get a quick summary of the user's financial state.

    Returns:
    - Total balance across all accounts
    - Spending this month vs last month
    - Number of unreviewed anomalies
    - Active goals progress
    """
    user, rate_limit_info = auth

    # Get accounts and balances
    accounts = db.query(Account).join(Institution).filter(
        Institution.user_id == user.id,
        Institution.status == "active"
    ).all()

    total_balance = sum(a.current_balance or 0 for a in accounts)
    account_count = len(accounts)

    # Get this month's spending
    today = date.today()
    first_of_month = today.replace(day=1)
    last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)

    account_ids = [a.id for a in accounts]

    this_month_spending = db.query(func.sum(Transaction.amount)).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.date >= first_of_month,
        Transaction.amount < 0,
        Transaction.is_transfer == False
    ).scalar() or 0

    last_month_spending = db.query(func.sum(Transaction.amount)).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.date >= last_month_start,
        Transaction.date < first_of_month,
        Transaction.amount < 0,
        Transaction.is_transfer == False
    ).scalar() or 0

    # Get anomaly count
    anomaly_count = db.query(Transaction).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.is_anomaly == True,
        Transaction.user_reviewed == False
    ).count()

    # Get active goals
    goals = db.query(Goal).filter(
        Goal.user_id == user.id,
        Goal.status == "active"
    ).all()

    goals_summary = []
    for goal in goals:
        progress = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        goals_summary.append({
            "name": goal.name,
            "target": goal.target_amount,
            "current": goal.current_amount,
            "progress_percent": round(progress, 1),
        })

    data = {
        "balances": {
            "total": round(total_balance, 2),
            "account_count": account_count,
        },
        "spending": {
            "this_month": round(abs(this_month_spending), 2),
            "last_month": round(abs(last_month_spending), 2),
            "change_percent": round(
                ((abs(this_month_spending) - abs(last_month_spending)) / abs(last_month_spending) * 100)
                if last_month_spending else 0, 1
            ),
        },
        "anomalies": {
            "unreviewed_count": anomaly_count,
        },
        "goals": goals_summary,
    }

    return make_response(data, rate_limit_info)


@router.get("/transactions")
async def get_transactions(
    start_date: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    merchant: Optional[str] = Query(None, description="Filter by merchant name (partial match)"),
    min_amount: Optional[float] = Query(None, description="Minimum amount (use negative for expenses)"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    is_anomaly: Optional[bool] = Query(None, description="Filter anomalies only"),
    limit: int = Query(50, ge=1, le=500, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """
    Get transactions with filtering and pagination.

    All transactions include enriched data (category, merchant, anomaly flags).
    """
    user, rate_limit_info = auth

    # Get user's account IDs
    accounts = db.query(Account).join(Institution).filter(
        Institution.user_id == user.id
    ).all()
    account_ids = [a.id for a in accounts]

    if not account_ids:
        return make_response({"transactions": [], "total": 0, "has_more": False}, rate_limit_info)

    # Build query
    query = db.query(Transaction).filter(Transaction.account_id.in_(account_ids))

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if category:
        query = query.filter(
            (Transaction.enriched_category == category) |
            (Transaction.teller_category == category)
        )
    if merchant:
        query = query.filter(
            Transaction.merchant_name.ilike(f"%{merchant}%") |
            Transaction.enriched_merchant.ilike(f"%{merchant}%")
        )
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)
    if is_anomaly is not None:
        query = query.filter(Transaction.is_anomaly == is_anomaly)

    # Get total count
    total = query.count()

    # Get paginated results
    transactions = query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()

    # Format transactions
    tx_list = []
    for tx in transactions:
        tx_list.append({
            "id": tx.id,
            "date": tx.date.isoformat(),
            "amount": tx.amount,
            "description": tx.description,
            "merchant": tx.enriched_merchant or tx.merchant_name,
            "category": tx.enriched_category or tx.teller_category or "Uncategorized",
            "type": tx.type,
            "status": tx.status,
            "is_transfer": tx.is_transfer,
            "is_anomaly": tx.is_anomaly,
            "anomaly_score": tx.anomaly_score,
            "anomaly_reason": tx.anomaly_reason,
            "is_one_time": tx.is_one_time,
            "categorization_source": tx.categorization_source,
            "categorization_confidence": tx.categorization_confidence,
        })

    data = {
        "transactions": tx_list,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }

    return make_response(data, rate_limit_info)


@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get full details of a single transaction."""
    user, rate_limit_info = auth

    # Get user's account IDs
    accounts = db.query(Account).join(Institution).filter(
        Institution.user_id == user.id
    ).all()
    account_ids = [a.id for a in accounts]

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.account_id.in_(account_ids)
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Get tags
    tags = [{"id": t.id, "name": t.name, "color": t.color} for t in tx.tags]

    data = {
        "id": tx.id,
        "date": tx.date.isoformat(),
        "amount": tx.amount,
        "description": tx.description,
        "merchant": tx.enriched_merchant or tx.merchant_name,
        "category": tx.enriched_category or tx.teller_category or "Uncategorized",
        "type": tx.type,
        "status": tx.status,
        "is_transfer": tx.is_transfer,
        "is_anomaly": tx.is_anomaly,
        "anomaly_score": tx.anomaly_score,
        "anomaly_reason": tx.anomaly_reason,
        "is_one_time": tx.is_one_time,
        "one_time_reason": tx.one_time_reason,
        "exclude_from_budget": tx.exclude_from_budget,
        "user_reviewed": tx.user_reviewed,
        "categorization_source": tx.categorization_source,
        "categorization_confidence": tx.categorization_confidence,
        "tags": tags,
        "account_id": tx.account_id,
    }

    return make_response(data, rate_limit_info)


@router.patch("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: str,
    category: Optional[str] = None,
    is_one_time: Optional[bool] = None,
    one_time_reason: Optional[str] = None,
    exclude_from_budget: Optional[bool] = None,
    user_reviewed: Optional[bool] = None,
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """
    Update a transaction's classification.

    Allows setting category, one-time flags, and review status.
    """
    user, rate_limit_info = auth

    # Get user's account IDs
    accounts = db.query(Account).join(Institution).filter(
        Institution.user_id == user.id
    ).all()
    account_ids = [a.id for a in accounts]

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.account_id.in_(account_ids)
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update fields
    if category is not None:
        tx.enriched_category = category
        tx.categorization_source = "user"
        tx.categorization_confidence = 1.0

    if is_one_time is not None:
        tx.is_one_time = is_one_time

    if one_time_reason is not None:
        tx.one_time_reason = one_time_reason

    if exclude_from_budget is not None:
        tx.exclude_from_budget = exclude_from_budget

    if user_reviewed is not None:
        tx.user_reviewed = user_reviewed

    db.commit()

    data = {
        "id": tx.id,
        "category": tx.enriched_category,
        "is_one_time": tx.is_one_time,
        "exclude_from_budget": tx.exclude_from_budget,
        "user_reviewed": tx.user_reviewed,
        "updated": True,
    }

    return make_response(data, rate_limit_info)


@router.get("/spending/by-category")
async def get_spending_by_category(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """
    Get spending breakdown by category.

    Defaults to current month if no dates provided.
    """
    user, rate_limit_info = auth

    service = DashboardService(db, user.id)

    # Use dashboard service's category breakdown
    if start_date and end_date:
        # Custom date range - need to implement or approximate
        month = start_date.month
        year = start_date.year
    else:
        month = None
        year = None

    result = service.get_category_breakdown(month, year)

    return make_response(result, rate_limit_info)


@router.get("/spending/by-merchant")
async def get_spending_by_merchant(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get spending breakdown by merchant for current month."""
    user, rate_limit_info = auth

    service = DashboardService(db, user.id)
    result = service.get_top_merchants(limit)

    return make_response({"merchants": result}, rate_limit_info)


@router.get("/spending/trends")
async def get_spending_trends(
    view: str = Query("monthly", description="View type: daily, monthly, or yearly"),
    budget: Optional[float] = Query(None, description="Optional budget amount"),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """
    Get spending trends over time.

    Views:
    - daily: Days in current month with cumulative totals
    - monthly: Past 12 months
    - yearly: Past 5 years
    """
    user, rate_limit_info = auth

    if view not in ["daily", "monthly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid view. Use: daily, monthly, yearly")

    service = DashboardService(db, user.id)
    result = service.get_spending_trend_by_view(view, budget)

    return make_response(result, rate_limit_info)


@router.get("/accounts")
async def get_accounts(
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get all accounts with current balances."""
    user, rate_limit_info = auth

    accounts = db.query(Account).join(Institution).filter(
        Institution.user_id == user.id
    ).all()

    account_list = []
    for acc in accounts:
        account_list.append({
            "id": acc.id,
            "name": acc.name,
            "type": acc.type,
            "subtype": acc.subtype,
            "current_balance": acc.current_balance,
            "available_balance": acc.available_balance,
            "currency": acc.currency,
            "last_four": acc.last_four,
            "institution": acc.institution.name if acc.institution else None,
            "last_synced": acc.last_synced_at.isoformat() if acc.last_synced_at else None,
        })

    total_balance = sum(a["current_balance"] or 0 for a in account_list)

    data = {
        "accounts": account_list,
        "total_balance": round(total_balance, 2),
        "count": len(account_list),
    }

    return make_response(data, rate_limit_info)


@router.get("/recurring")
async def get_recurring_payments(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get detected recurring payments (subscriptions)."""
    user, rate_limit_info = auth

    service = DashboardService(db, user.id)
    result = service.get_recurring_payments(limit)

    return make_response(result, rate_limit_info)


@router.get("/anomalies")
async def get_anomalies(
    include_reviewed: bool = Query(False, description="Include reviewed anomalies"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get unusual transactions flagged by the system."""
    user, rate_limit_info = auth

    # Get user's account IDs
    accounts = db.query(Account).join(Institution).filter(
        Institution.user_id == user.id
    ).all()
    account_ids = [a.id for a in accounts]

    query = db.query(Transaction).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.is_anomaly == True
    )

    if not include_reviewed:
        query = query.filter(Transaction.user_reviewed == False)

    anomalies = query.order_by(Transaction.date.desc()).limit(limit).all()

    anomaly_list = []
    for tx in anomalies:
        anomaly_list.append({
            "id": tx.id,
            "date": tx.date.isoformat(),
            "amount": tx.amount,
            "merchant": tx.enriched_merchant or tx.merchant_name,
            "category": tx.enriched_category or tx.teller_category,
            "description": tx.description,
            "anomaly_score": tx.anomaly_score,
            "anomaly_reason": tx.anomaly_reason,
            "user_reviewed": tx.user_reviewed,
            "is_one_time": tx.is_one_time,
        })

    data = {
        "anomalies": anomaly_list,
        "total": len(anomaly_list),
    }

    return make_response(data, rate_limit_info)


@router.get("/insights")
async def get_insights(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get AI-generated financial insights."""
    user, rate_limit_info = auth

    insights = db.query(Insight).filter(
        Insight.user_id == user.id
    ).order_by(Insight.generated_at.desc()).limit(limit).all()

    insight_list = []
    for insight in insights:
        insight_list.append({
            "id": insight.id,
            "type": insight.type,
            "title": insight.title,
            "description": insight.description,
            "action": insight.action,
            "category": insight.category,
            "amount_referenced": insight.amount_referenced,
            "priority_score": insight.priority_score,
            "generated_at": insight.generated_at.isoformat(),
            "is_read": insight.is_read,
            "feedback": insight.feedback,
        })

    data = {
        "insights": insight_list,
        "total": len(insight_list),
    }

    return make_response(data, rate_limit_info)


@router.get("/goals")
async def get_goals(
    status: Optional[str] = Query(None, description="Filter by status: active, completed, paused, cancelled"),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get financial goals with progress."""
    user, rate_limit_info = auth

    query = db.query(Goal).filter(Goal.user_id == user.id)

    if status:
        query = query.filter(Goal.status == status)

    goals = query.order_by(Goal.created_at.desc()).all()

    goal_list = []
    for goal in goals:
        progress = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        goal_list.append({
            "id": goal.id,
            "name": goal.name,
            "description": goal.description,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "monthly_allocation": goal.monthly_allocation,
            "progress_percent": round(progress, 1),
            "deadline": goal.deadline.isoformat() if goal.deadline else None,
            "priority": goal.priority,
            "status": goal.status,
            "auto_suggested": goal.auto_suggested,
            "created_at": goal.created_at.isoformat(),
        })

    data = {
        "goals": goal_list,
        "total": len(goal_list),
    }

    return make_response(data, rate_limit_info)


@router.get("/income")
async def get_income(
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get income sources and summary."""
    user, rate_limit_info = auth

    sources = db.query(IncomeSource).filter(
        IncomeSource.user_id == user.id,
        IncomeSource.is_active == True
    ).all()

    income_list = []
    total_monthly = 0

    for source in sources:
        # Normalize to monthly
        amount = source.amount
        if source.frequency == "weekly":
            monthly = amount * 4.33
        elif source.frequency == "biweekly":
            monthly = amount * 2.17
        elif source.frequency == "yearly":
            monthly = amount / 12
        else:
            monthly = amount

        total_monthly += monthly

        income_list.append({
            "id": source.id,
            "name": source.name,
            "amount": source.amount,
            "frequency": source.frequency,
            "monthly_equivalent": round(monthly, 2),
            "auto_detected": source.auto_detected,
            "next_expected": source.next_expected_date.isoformat() if source.next_expected_date else None,
        })

    data = {
        "income_sources": income_list,
        "total_monthly_income": round(total_monthly, 2),
        "count": len(income_list),
    }

    return make_response(data, rate_limit_info)


@router.get("/rules/merchant-categories")
async def get_merchant_category_rules(
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict]] = Depends(get_user_with_rate_limit),
):
    """Get user-defined merchant categorization rules."""
    user, rate_limit_info = auth

    rules = db.query(MerchantCategoryRule).filter(
        MerchantCategoryRule.user_id == user.id,
        MerchantCategoryRule.is_active == True
    ).order_by(MerchantCategoryRule.times_applied.desc()).all()

    rule_list = []
    for rule in rules:
        rule_list.append({
            "id": rule.id,
            "merchant_name": rule.merchant_name,
            "category": rule.category,
            "times_applied": rule.times_applied,
            "created_at": rule.created_at.isoformat(),
        })

    data = {
        "rules": rule_list,
        "total": len(rule_list),
    }

    return make_response(data, rate_limit_info)
