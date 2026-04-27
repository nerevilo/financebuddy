"""
Finance Data Service — Shared query layer for REST API and MCP server.

Extracts the data access logic from llm_api.py so both the REST router
and MCP tools can call the same code without duplication.
"""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.models import (
    Transaction, Account, Institution, Goal, IncomeSource, Insight,
    MerchantCategoryRule,
)
from ..services.dashboard_service import DashboardService


class FinanceDataService:
    """User-scoped read access to financial data."""

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id

    # -- helpers --

    def _user_account_ids(self) -> list[str]:
        accounts = (
            self.db.query(Account)
            .join(Institution)
            .filter(Institution.user_id == self.user_id)
            .limit(100)
            .all()
        )
        return [a.id for a in accounts]

    def _user_accounts(self, *, active_only: bool = False):
        q = self.db.query(Account).join(Institution).filter(
            Institution.user_id == self.user_id
        )
        if active_only:
            q = q.filter(Institution.status == "active")
        return q.limit(100).all()

    # -- public methods --

    def get_summary(self) -> dict:
        accounts = self._user_accounts(active_only=True)
        total_balance = sum(a.current_balance or 0 for a in accounts)
        account_ids = [a.id for a in accounts]

        today = date.today()
        first_of_month = today.replace(day=1)
        last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)

        this_month_spending = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= first_of_month,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
        ).scalar() or 0

        last_month_spending = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= last_month_start,
            Transaction.date < first_of_month,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
        ).scalar() or 0

        anomaly_count = self.db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.is_anomaly == True,
            Transaction.user_reviewed == False,
        ).count()

        goals = self.db.query(Goal).filter(
            Goal.user_id == self.user_id,
            Goal.status == "active",
        ).limit(50).all()

        goals_summary = []
        for goal in goals:
            progress = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
            goals_summary.append({
                "name": goal.name,
                "target": goal.target_amount,
                "current": goal.current_amount,
                "progress_percent": round(progress, 1),
            })

        return {
            "balances": {
                "total": round(total_balance, 2),
                "account_count": len(accounts),
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

    def get_transactions(
        self,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        merchant: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        is_anomaly: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        account_ids = self._user_account_ids()
        if not account_ids:
            return {"transactions": [], "total": 0, "has_more": False}

        query = self.db.query(Transaction).filter(Transaction.account_id.in_(account_ids))

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
            safe = merchant.replace("%", r"\%").replace("_", r"\_")
            query = query.filter(
                Transaction.merchant_name.ilike(f"%{safe}%") |
                Transaction.enriched_merchant.ilike(f"%{safe}%")
            )
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        if is_anomaly is not None:
            query = query.filter(Transaction.is_anomaly == is_anomaly)

        total = query.count()
        transactions = query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()

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
                "account_id": tx.account_id,
            })

        return {
            "transactions": tx_list,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        }

    def get_spending_by_category(
        self,
        *,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        service = DashboardService(self.db, self.user_id)
        if start_date and end_date:
            month = start_date.month
            year = start_date.year
        else:
            month = None
            year = None
        return service.get_category_breakdown(month, year)

    def get_spending_by_merchant(self, limit: int = 20) -> dict:
        service = DashboardService(self.db, self.user_id)
        result = service.get_top_merchants(limit)
        return {"merchants": result}

    def get_spending_trends(
        self,
        view: str = "monthly",
        budget: Optional[float] = None,
    ) -> dict:
        service = DashboardService(self.db, self.user_id)
        return service.get_spending_trend_by_view(view, budget)

    def get_accounts(self) -> dict:
        accounts = self._user_accounts()

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

        return {
            "accounts": account_list,
            "total_balance": round(total_balance, 2),
            "count": len(account_list),
        }

    def get_recurring(self, limit: int = 20) -> dict:
        service = DashboardService(self.db, self.user_id)
        return service.get_recurring_payments(limit)

    def get_anomalies(
        self,
        *,
        include_reviewed: bool = False,
        limit: int = 50,
    ) -> dict:
        account_ids = self._user_account_ids()

        query = self.db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.is_anomaly == True,
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

        return {
            "anomalies": anomaly_list,
            "total": len(anomaly_list),
        }

    def get_insights(self, limit: int = 10) -> dict:
        insights = (
            self.db.query(Insight)
            .filter(Insight.user_id == self.user_id)
            .order_by(Insight.generated_at.desc())
            .limit(limit)
            .all()
        )

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

        return {
            "insights": insight_list,
            "total": len(insight_list),
        }

    def get_goals(self, status: Optional[str] = None) -> dict:
        query = self.db.query(Goal).filter(Goal.user_id == self.user_id)
        if status:
            query = query.filter(Goal.status == status)

        goals = query.order_by(Goal.created_at.desc()).limit(50).all()

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

        return {
            "goals": goal_list,
            "total": len(goal_list),
        }

    def get_income(self) -> dict:
        sources = (
            self.db.query(IncomeSource)
            .filter(
                IncomeSource.user_id == self.user_id,
                IncomeSource.is_active == True,
            )
            .limit(50)
            .all()
        )

        income_list = []
        total_monthly = 0

        for source in sources:
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

        return {
            "income_sources": income_list,
            "total_monthly_income": round(total_monthly, 2),
            "count": len(income_list),
        }
