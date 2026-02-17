"""
MCP Server for Ledgi — Exposes financial data tools over the Model Context Protocol.

Authenticates via X-API-Key header (same keys as REST API).
Each tool call gets its own DB session, validates the API key, enforces
the transactions:read scope, and delegates to FinanceDataService.
"""
from contextlib import contextmanager
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request

from ..core.database import SessionLocal
from ..core.api_keys import validate_api_key, check_scope
from ..services.finance_data_service import FinanceDataService

mcp = FastMCP("Ledgi Finance")


class MCPAuthError(Exception):
    pass


def _extract_api_key(request) -> str:
    """Pull API key from X-API-Key header or Authorization: Bearer."""
    key = request.headers.get("x-api-key")
    if key:
        return key

    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    raise MCPAuthError("Missing API key. Provide X-API-Key header or Authorization: Bearer <key>.")


@contextmanager
def mcp_auth_context():
    """Authenticate the current MCP HTTP request and yield (user, db).

    Validates the API key, checks transactions:read scope, and manages
    the DB session lifetime.
    """
    request = get_http_request()
    raw_key = _extract_api_key(request)

    db = SessionLocal()
    try:
        result = validate_api_key(raw_key, db)
        if result is None:
            raise MCPAuthError("Invalid or expired API key.")

        user, api_key = result

        if not check_scope(api_key, "transactions:read"):
            raise MCPAuthError("API key missing required scope: transactions:read")

        yield user, db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_financial_summary() -> dict:
    """Get overview of your finances: total balances across all accounts, this month vs last month spending comparison with percent change, count of unreviewed anomalous transactions, and active savings goals with progress."""
    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_summary()


@mcp.tool()
def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    merchant: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    is_anomaly: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Search and filter transactions. Dates are YYYY-MM-DD strings. Amounts are signed (negative = expense). Supports pagination via limit/offset. Returns enriched data including category, merchant, anomaly flags."""
    from datetime import date as date_type

    kwargs: dict = {}
    if start_date:
        kwargs["start_date"] = date_type.fromisoformat(start_date)
    if end_date:
        kwargs["end_date"] = date_type.fromisoformat(end_date)
    if category:
        kwargs["category"] = category
    if merchant:
        kwargs["merchant"] = merchant
    if min_amount is not None:
        kwargs["min_amount"] = min_amount
    if max_amount is not None:
        kwargs["max_amount"] = max_amount
    if is_anomaly is not None:
        kwargs["is_anomaly"] = is_anomaly
    kwargs["limit"] = min(limit, 500)
    kwargs["offset"] = max(offset, 0)

    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_transactions(**kwargs)


@mcp.tool()
def get_spending_by_category(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Get spending breakdown by category for a given period. Defaults to current month. Returns categories sorted by amount with percentages."""
    from datetime import date as date_type

    kwargs: dict = {}
    if start_date:
        kwargs["start_date"] = date_type.fromisoformat(start_date)
    if end_date:
        kwargs["end_date"] = date_type.fromisoformat(end_date)

    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_spending_by_category(**kwargs)


@mcp.tool()
def get_spending_by_merchant(limit: int = 20) -> dict:
    """Get top merchants by spending for the current month. Returns merchant name, total spent, visit count, and average per visit."""
    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_spending_by_merchant(min(limit, 100))


@mcp.tool()
def get_spending_trends(
    view: str = "monthly",
    budget: Optional[float] = None,
) -> dict:
    """Get spending trends over time. Views: 'daily' (days in current month with cumulative totals), 'monthly' (past 12 months), 'yearly' (past 5 years). Optionally compare against a budget amount."""
    if view not in ("daily", "monthly", "yearly"):
        return {"error": "Invalid view. Use: daily, monthly, yearly"}

    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_spending_trends(view, budget)


@mcp.tool()
def get_accounts() -> dict:
    """Get all connected bank accounts with current and available balances, account type, institution name, and last sync time."""
    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_accounts()


@mcp.tool()
def get_recurring_payments(limit: int = 20) -> dict:
    """Get detected recurring payments and subscriptions. Shows merchant, amount, frequency (weekly/biweekly/monthly/yearly), category, and next expected date."""
    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_recurring(min(limit, 100))


@mcp.tool()
def get_anomalies(
    include_reviewed: bool = False,
    limit: int = 50,
) -> dict:
    """Get unusual transactions flagged by the anomaly detection system. Shows amount, merchant, anomaly score and reason. Set include_reviewed=true to include already-reviewed anomalies."""
    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_anomalies(
            include_reviewed=include_reviewed,
            limit=min(limit, 200),
        )


@mcp.tool()
def get_insights(limit: int = 10) -> dict:
    """Get AI-generated financial insights. Each insight has a type, title, description, suggested action, priority score, and read status."""
    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_insights(min(limit, 50))


@mcp.tool()
def get_goals(status: Optional[str] = None) -> dict:
    """Get financial goals with progress tracking. Filter by status: active, completed, paused, cancelled. Shows target amount, current amount, progress percentage, and deadline."""
    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_goals(status)


@mcp.tool()
def get_income() -> dict:
    """Get income sources and summary. Shows each source's amount, frequency, monthly equivalent, and next expected date. Includes total estimated monthly income."""
    with mcp_auth_context() as (user, db):
        return FinanceDataService(db, user.id).get_income()
