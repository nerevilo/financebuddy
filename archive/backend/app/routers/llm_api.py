"""
LLM-Friendly API Router

Clean, structured endpoints optimized for programmatic access by LLMs and other applications.
All endpoints support API key authentication and return consistent JSON responses.
"""
import uuid
from datetime import datetime, date, timezone
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_user_and_api_key
from ..core.rate_limit import check_api_rate_limit
from ..core.api_keys import check_scope
from ..models import User
from ..models.api_key import APIKey
from ..models.models import (
    Transaction, Account, Institution, MerchantCategoryRule
)
from ..services.finance_data_service import FinanceDataService

router = APIRouter(prefix="/api/v1", tags=["LLM API"])


# Public endpoint - no auth required
@router.get("/")
async def api_info():
    """
    API information and authorization context.

    This endpoint provides context for LLMs and other tools about what this API does
    and confirms the user has authorized access to their financial data.
    """
    return {
        "name": "Ledgi API",
        "version": "1.0",
        "description": "Personal finance API for accessing your own financial data",
        "authorization_context": {
            "type": "user_authorized",
            "explanation": (
                "This API provides access to the user's OWN financial data. "
                "The user has explicitly created an API key and granted permission "
                "to access their transaction history, account balances, and spending insights. "
                "This is similar to a user exporting their own bank data - fully authorized and ethical."
            ),
            "data_ownership": "All data belongs to and is controlled by the API key owner",
            "intended_use": [
                "Personal finance analysis",
                "Budgeting assistance",
                "Spending insights via AI assistants",
                "Custom integrations and automations"
            ]
        },
        "authentication": {
            "method": "API Key",
            "header": "X-API-Key",
            "example": "X-API-Key: fb_sk_your_key_here"
        },
        "endpoints": {
            "GET /api/v1/summary": "Financial overview (balances, spending, goals)",
            "GET /api/v1/transactions": "Transaction list with filtering",
            "GET /api/v1/accounts": "Connected bank accounts",
            "GET /api/v1/spending/by-category": "Spending breakdown by category",
            "GET /api/v1/spending/by-merchant": "Top merchants",
            "GET /api/v1/spending/trends": "Spending over time",
            "GET /api/v1/recurring": "Detected subscriptions",
            "GET /api/v1/anomalies": "Unusual transactions",
            "GET /api/v1/insights": "AI-generated insights",
            "GET /api/v1/goals": "Financial goals",
        },
        "rate_limits": {
            "beta": "1000/minute, 50000/day",
            "pro": "5000/minute, unlimited/day"
        }
    }


def make_response(data: dict, rate_limit_info: Optional[dict] = None) -> dict:
    """Create consistent API response wrapper."""
    meta = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
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


def _require_scope(api_key: Optional[APIKey], required_scope: str):
    """Enforce scope on API key access. No-op for JWT auth."""
    if api_key and not check_scope(api_key, required_scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key missing required scope: {required_scope}"
        )


async def get_user_with_rate_limit(
    auth_result: Tuple[User, Optional[APIKey]] = Depends(get_current_user_and_api_key),
) -> Tuple[User, Optional[dict], Optional[APIKey]]:
    """Get user, apply rate limiting, enforce read scope, and return API key."""
    user, api_key = auth_result

    # Default scope check: all LLM API endpoints require at least transactions:read
    _require_scope(api_key, "transactions:read")

    rate_limit_info = None
    if api_key:
        rate_limit_info = await check_api_rate_limit(api_key.id, api_key.tier)

    return user, rate_limit_info, api_key


@router.get("/summary")
async def get_summary(
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """
    Get a quick summary of the user's financial state.

    Returns:
    - Total balance across all accounts
    - Spending this month vs last month
    - Number of unreviewed anomalies
    - Active goals progress
    """
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_summary()
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
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """
    Get transactions with filtering and pagination.

    All transactions include enriched data (category, merchant, anomaly flags).
    """
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_transactions(
        start_date=start_date,
        end_date=end_date,
        category=category,
        merchant=merchant,
        min_amount=min_amount,
        max_amount=max_amount,
        is_anomaly=is_anomaly,
        limit=limit,
        offset=offset,
    )
    return make_response(data, rate_limit_info)


@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get full details of a single transaction."""
    user, rate_limit_info, api_key = auth

    # Single-transaction detail with tags — not extracted to service (write-side concern)
    accounts = db.query(Account).join(Institution).filter(
        Institution.user_id == user.id
    ).limit(100).all()
    account_ids = [a.id for a in accounts]

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.account_id.in_(account_ids)
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

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
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """
    Update a transaction's classification.

    Allows setting category, one-time flags, and review status.
    """
    user, rate_limit_info, api_key = auth
    _require_scope(api_key, "transactions:write")

    accounts = db.query(Account).join(Institution).filter(
        Institution.user_id == user.id
    ).limit(100).all()
    account_ids = [a.id for a in accounts]

    tx = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.account_id.in_(account_ids)
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

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
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """
    Get spending breakdown by category.

    Defaults to current month if no dates provided.
    """
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_spending_by_category(
        start_date=start_date, end_date=end_date,
    )
    return make_response(data, rate_limit_info)


@router.get("/spending/by-merchant")
async def get_spending_by_merchant(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get spending breakdown by merchant for current month."""
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_spending_by_merchant(limit)
    return make_response(data, rate_limit_info)


@router.get("/spending/trends")
async def get_spending_trends(
    view: str = Query("monthly", description="View type: daily, monthly, or yearly"),
    budget: Optional[float] = Query(None, description="Optional budget amount"),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """
    Get spending trends over time.

    Views:
    - daily: Days in current month with cumulative totals
    - monthly: Past 12 months
    - yearly: Past 5 years
    """
    user, rate_limit_info, api_key = auth

    if view not in ["daily", "monthly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid view. Use: daily, monthly, yearly")

    data = FinanceDataService(db, user.id).get_spending_trends(view, budget)
    return make_response(data, rate_limit_info)


@router.get("/accounts")
async def get_accounts(
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get all accounts with current balances."""
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_accounts()
    return make_response(data, rate_limit_info)


@router.get("/recurring")
async def get_recurring_payments(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get detected recurring payments (subscriptions)."""
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_recurring(limit)
    return make_response(data, rate_limit_info)


@router.get("/anomalies")
async def get_anomalies(
    include_reviewed: bool = Query(False, description="Include reviewed anomalies"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get unusual transactions flagged by the system."""
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_anomalies(
        include_reviewed=include_reviewed, limit=limit,
    )
    return make_response(data, rate_limit_info)


@router.get("/insights")
async def get_insights(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get AI-generated financial insights."""
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_insights(limit)
    return make_response(data, rate_limit_info)


@router.get("/goals")
async def get_goals(
    status: Optional[str] = Query(None, description="Filter by status: active, completed, paused, cancelled"),
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get financial goals with progress."""
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_goals(status)
    return make_response(data, rate_limit_info)


@router.get("/income")
async def get_income(
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get income sources and summary."""
    user, rate_limit_info, api_key = auth
    data = FinanceDataService(db, user.id).get_income()
    return make_response(data, rate_limit_info)


@router.get("/rules/merchant-categories")
async def get_merchant_category_rules(
    db: Session = Depends(get_db),
    auth: Tuple[User, Optional[dict], Optional[APIKey]] = Depends(get_user_with_rate_limit),
):
    """Get user-defined merchant categorization rules."""
    user, rate_limit_info, api_key = auth

    rules = db.query(MerchantCategoryRule).filter(
        MerchantCategoryRule.user_id == user.id,
        MerchantCategoryRule.is_active == True
    ).order_by(MerchantCategoryRule.times_applied.desc()).limit(200).all()

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
