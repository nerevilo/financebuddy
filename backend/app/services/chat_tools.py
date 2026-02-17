"""
Chat Tools - Function definitions and executors for the chat agent.

These tools give the chatbot access to financial data and actions.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..models import Transaction, Account, Institution, Goal, TransactionTag
from ..models.models import generate_uuid
from .dashboard_service import DashboardService


# Tool definitions in Claude/OpenAI function calling format
TOOL_DEFINITIONS = [
    {
        "name": "search_transactions",
        "description": "Search user's transactions by merchant name, description, category, or date range. Use this when the user asks about specific purchases, merchants, or wants to find transactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for merchant name or description (e.g., 'Starbucks', 'grocery')"
                },
                "category": {
                    "type": "string",
                    "description": "Filter by spending category (e.g., 'dining', 'groceries', 'gas')"
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of transactions to return (default 10, max 50)",
                    "default": 10
                }
            },
            "required": []
        }
    },
    {
        "name": "get_spending_summary",
        "description": "Get spending breakdown by category for a time period. Use this when the user asks about overall spending, category totals, or budget questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["this_month", "last_month", "this_week", "last_30_days", "this_year"],
                    "description": "Time period for the summary",
                    "default": "this_month"
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top categories to return",
                    "default": 10
                }
            },
            "required": []
        }
    },
    {
        "name": "get_spending_pace",
        "description": "Get current month's spending velocity and projection. Use when the user asks 'am I on budget?', 'how am I doing this month?', or about spending pace.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_category_spending",
        "description": "Get detailed spending for a specific category with merchant breakdown. Use when user asks about a specific category like 'how much did I spend on dining?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "The spending category to analyze"
                },
                "period": {
                    "type": "string",
                    "enum": ["this_month", "last_month", "last_30_days"],
                    "default": "this_month"
                }
            },
            "required": ["category"]
        }
    },
    {
        "name": "get_goals",
        "description": "Get user's financial goals and progress. Use when user asks about their savings goals, progress, or financial targets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "completed", "all"],
                    "default": "active"
                }
            },
            "required": []
        }
    },
    {
        "name": "update_transaction_tags",
        "description": "Add or remove tags from a transaction. Use when user wants to tag, label, or categorize a specific transaction.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_id": {
                    "type": "string",
                    "description": "ID of the transaction to update"
                },
                "add_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tag names to add to the transaction"
                },
                "remove_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tag names to remove from the transaction"
                }
            },
            "required": ["transaction_id"]
        }
    },
    {
        "name": "get_unusual_transactions",
        "description": "Get transactions flagged as unusual or anomalous. Use when user asks about suspicious activity, unusual spending, or anomalies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "default": 5
                }
            },
            "required": []
        }
    },
    {
        "name": "compare_periods",
        "description": "Compare spending between two time periods. Use when user asks 'how does this month compare to last month?' or similar comparisons.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period1": {
                    "type": "string",
                    "enum": ["this_month", "last_month", "this_week", "last_week"],
                    "default": "this_month"
                },
                "period2": {
                    "type": "string",
                    "enum": ["last_month", "same_month_last_year", "last_week"],
                    "default": "last_month"
                }
            },
            "required": []
        }
    }
]


class ChatToolExecutor:
    """Executes tool calls made by the LLM."""

    # Emoji mapping for categories
    CATEGORY_EMOJIS = {
        'groceries': '🛒',
        'dining': '🍽️',
        'restaurant': '🍽️',
        'fast food': '🍔',
        'coffee': '☕',
        'gas': '⛽',
        'fuel': '⛽',
        'shopping': '🛍️',
        'retail': '🛍️',
        'entertainment': '🎬',
        'travel': '✈️',
        'transportation': '🚗',
        'utilities': '💡',
        'subscription': '📱',
        'software': '💻',
        'healthcare': '🏥',
        'pharmacy': '💊',
        'insurance': '🛡️',
        'rent': '🏠',
        'mortgage': '🏠',
        'education': '📚',
        'fitness': '💪',
        'gym': '💪',
        'personal care': '💅',
        'pet': '🐾',
        'default': '💰'
    }

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.dashboard_service = DashboardService(db, user_id)

    def _get_emoji(self, category: str) -> str:
        """Get emoji for a category."""
        if not category:
            return self.CATEGORY_EMOJIS['default']
        cat_lower = category.lower()
        for key, emoji in self.CATEGORY_EMOJIS.items():
            if key in cat_lower:
                return emoji
        return self.CATEGORY_EMOJIS['default']

    def _user_filter(self):
        """Return filter for user's active institutions."""
        return and_(
            Institution.user_id == self.user_id,
            Institution.status == "active"
        )

    async def execute(self, tool_name: str, arguments: Dict) -> Any:
        """Route tool call to appropriate handler."""
        handlers = {
            "search_transactions": self._search_transactions,
            "get_spending_summary": self._get_spending_summary,
            "get_spending_pace": self._get_spending_pace,
            "get_category_spending": self._get_category_spending,
            "get_goals": self._get_goals,
            "update_transaction_tags": self._update_transaction_tags,
            "get_unusual_transactions": self._get_unusual_transactions,
            "compare_periods": self._compare_periods,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            return await handler(**arguments)
        except Exception as e:
            return {"error": str(e)}

    async def _search_transactions(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10
    ) -> Dict:
        """Search transactions with filters."""
        # Build query with user filter
        q = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).join(
            Institution, Account.institution_id == Institution.id
        ).filter(self._user_filter())

        if query:
            search_term = f"%{query}%"
            q = q.filter(or_(
                Transaction.description.ilike(search_term),
                Transaction.merchant_name.ilike(search_term),
                Transaction.enriched_merchant.ilike(search_term)
            ))

        if category:
            q = q.filter(or_(
                Transaction.enriched_category.ilike(f"%{category}%"),
                Transaction.teller_category.ilike(f"%{category}%")
            ))

        if start_date:
            q = q.filter(Transaction.date >= start_date)

        if end_date:
            q = q.filter(Transaction.date <= end_date)

        transactions = q.order_by(Transaction.date.desc()).limit(min(limit, 50)).all()

        return {
            "count": len(transactions),
            "transactions": [
                {
                    "id": t.id,
                    "date": t.date.isoformat() if t.date else None,
                    "merchant": t.enriched_merchant or t.merchant_name or t.description[:30],
                    "description": t.description,
                    "amount": abs(t.amount),
                    "category": t.enriched_category or t.teller_category or "uncategorized",
                    "emoji": self._get_emoji(t.enriched_category or t.teller_category),
                    "is_expense": t.amount < 0 if t.account.type == 'depository' else t.amount > 0
                }
                for t in transactions
            ]
        }

    async def _get_spending_summary(
        self,
        period: str = "this_month",
        top_n: int = 10
    ) -> Dict:
        """Get spending breakdown by category."""
        # Calculate date range based on period
        now = datetime.now()
        if period == "this_month":
            start = datetime(now.year, now.month, 1)
            end = now
        elif period == "last_month":
            first_of_month = datetime(now.year, now.month, 1)
            end = first_of_month - timedelta(days=1)
            start = datetime(end.year, end.month, 1)
        elif period == "this_week":
            start = now - timedelta(days=now.weekday())
            end = now
        elif period == "last_30_days":
            start = now - timedelta(days=30)
            end = now
        elif period == "this_year":
            start = datetime(now.year, 1, 1)
            end = now
        else:
            start = datetime(now.year, now.month, 1)
            end = now

        # Query spending by category
        results = self.db.query(
            Transaction.enriched_category,
            func.sum(func.abs(Transaction.amount)).label('total'),
            func.count(Transaction.id).label('count')
        ).join(
            Account, Transaction.account_id == Account.id
        ).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                self._user_filter(),
                Transaction.date >= start.date(),
                Transaction.date <= end.date(),
                or_(
                    and_(Account.type == 'depository', Transaction.amount < 0),
                    and_(Account.type == 'credit', Transaction.amount > 0)
                ),
                # Exclude transfers
                or_(Transaction.is_transfer.is_(None), Transaction.is_transfer == False)
            )
        ).group_by(Transaction.enriched_category).order_by(
            func.sum(func.abs(Transaction.amount)).desc()
        ).limit(top_n).all()

        total_spent = sum(r.total for r in results if r.total)

        categories = []
        for r in results:
            if r.enriched_category and r.total:
                categories.append({
                    "category": r.enriched_category,
                    "emoji": self._get_emoji(r.enriched_category),
                    "amount": r.total,
                    "count": r.count,
                    "percentage": (r.total / total_spent * 100) if total_spent > 0 else 0
                })

        return {
            "period": period,
            "total_spent": total_spent,
            "categories": categories
        }

    async def _get_spending_pace(self) -> Dict:
        """Get spending velocity for current month."""
        return self.dashboard_service.get_spending_velocity()

    async def _get_category_spending(
        self,
        category: str,
        period: str = "this_month"
    ) -> Dict:
        """Get detailed spending for a category with merchants."""
        now = datetime.now()
        if period == "this_month":
            start = datetime(now.year, now.month, 1)
            end = now
        elif period == "last_month":
            first_of_month = datetime(now.year, now.month, 1)
            end = first_of_month - timedelta(days=1)
            start = datetime(end.year, end.month, 1)
        else:  # last_30_days
            start = now - timedelta(days=30)
            end = now

        # Query transactions in this category
        transactions = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                self._user_filter(),
                Transaction.date >= start.date(),
                Transaction.date <= end.date(),
                or_(
                    Transaction.enriched_category.ilike(f"%{category}%"),
                    Transaction.teller_category.ilike(f"%{category}%")
                ),
                or_(
                    and_(Account.type == 'depository', Transaction.amount < 0),
                    and_(Account.type == 'credit', Transaction.amount > 0)
                )
            )
        ).order_by(Transaction.date.desc()).all()

        # Aggregate by merchant
        merchant_totals = {}
        for t in transactions:
            merchant = t.enriched_merchant or t.merchant_name or "Unknown"
            if merchant not in merchant_totals:
                merchant_totals[merchant] = {"total": 0, "count": 0}
            merchant_totals[merchant]["total"] += abs(t.amount)
            merchant_totals[merchant]["count"] += 1

        # Sort by total spent
        top_merchants = sorted(
            [{"merchant": k, **v} for k, v in merchant_totals.items()],
            key=lambda x: x["total"],
            reverse=True
        )[:10]

        total = sum(abs(t.amount) for t in transactions)

        return {
            "category": category,
            "emoji": self._get_emoji(category),
            "period": period,
            "total": total,
            "transaction_count": len(transactions),
            "top_merchants": top_merchants,
            "recent_transactions": [
                {
                    "id": t.id,
                    "date": t.date.isoformat() if t.date else None,
                    "merchant": t.enriched_merchant or t.merchant_name,
                    "amount": abs(t.amount)
                }
                for t in transactions[:5]
            ]
        }

    async def _get_goals(self, status: str = "active") -> Dict:
        """Get user's financial goals."""
        query = self.db.query(Goal).filter(Goal.user_id == self.user_id)

        if status != "all":
            query = query.filter(Goal.status == status)

        goals = query.order_by(Goal.created_at.desc()).all()

        return {
            "count": len(goals),
            "goals": [
                {
                    "id": g.id,
                    "name": g.name,
                    "description": g.description,
                    "target": g.target_amount,
                    "current": g.current_amount,
                    "progress_pct": (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0,
                    "deadline": g.deadline.isoformat() if g.deadline else None,
                    "status": g.status,
                    "monthly_allocation": g.monthly_allocation
                }
                for g in goals
            ]
        }

    async def _update_transaction_tags(
        self,
        transaction_id: str,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None
    ) -> Dict:
        """Update tags on a transaction."""
        # Verify transaction belongs to user
        transaction = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                Transaction.id == transaction_id,
                self._user_filter()
            )
        ).first()

        if not transaction:
            return {"error": "Transaction not found or access denied"}

        changes = []

        if add_tags:
            for tag_name in add_tags:
                # Find or create tag
                tag = self.db.query(TransactionTag).filter(
                    and_(
                        TransactionTag.user_id == self.user_id,
                        TransactionTag.name == tag_name
                    )
                ).first()

                if not tag:
                    tag = TransactionTag(
                        id=generate_uuid(),
                        user_id=self.user_id,
                        name=tag_name,
                        tag_type="custom"
                    )
                    self.db.add(tag)
                    self.db.flush()

                if tag not in transaction.tags:
                    transaction.tags.append(tag)
                    changes.append(f"Added tag '{tag_name}'")

        if remove_tags:
            for tag_name in remove_tags:
                tag = self.db.query(TransactionTag).filter(
                    and_(
                        TransactionTag.user_id == self.user_id,
                        TransactionTag.name == tag_name
                    )
                ).first()

                if tag and tag in transaction.tags:
                    transaction.tags.remove(tag)
                    changes.append(f"Removed tag '{tag_name}'")

        self.db.commit()

        return {
            "success": True,
            "transaction_id": transaction_id,
            "merchant": transaction.enriched_merchant or transaction.merchant_name,
            "changes": changes,
            "current_tags": [t.name for t in transaction.tags]
        }

    async def _get_unusual_transactions(self, limit: int = 5) -> Dict:
        """Get unusual/anomalous transactions."""
        transactions = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                self._user_filter(),
                Transaction.is_anomaly == True,
                Transaction.user_reviewed == False
            )
        ).order_by(Transaction.anomaly_score.desc()).limit(limit).all()

        return {
            "count": len(transactions),
            "transactions": [
                {
                    "id": t.id,
                    "date": t.date.isoformat() if t.date else None,
                    "merchant": t.enriched_merchant or t.merchant_name,
                    "amount": abs(t.amount),
                    "category": t.enriched_category,
                    "emoji": self._get_emoji(t.enriched_category),
                    "anomaly_reason": t.anomaly_reason,
                    "anomaly_score": t.anomaly_score
                }
                for t in transactions
            ]
        }

    async def _compare_periods(
        self,
        period1: str = "this_month",
        period2: str = "last_month"
    ) -> Dict:
        """Compare spending between periods."""
        comparison = self.dashboard_service.get_monthly_comparison()

        # Calculate totals
        total_this_month = sum(
            data['this_month'] for data in comparison['categories'].values()
        )
        total_last_month = sum(
            data['last_month'] for data in comparison['categories'].values()
        )

        # Get top changes
        categories_list = []
        for cat, data in comparison['categories'].items():
            if cat:  # Skip None categories
                categories_list.append({
                    "category": cat,
                    "emoji": self._get_emoji(cat),
                    "this_month": data['this_month'],
                    "last_month": data['last_month'],
                    "change": data['change'],
                    "change_pct": data['change_pct'],
                    "trend": data['trend']
                })

        # Sort by absolute change
        categories_list.sort(key=lambda x: abs(x['change']), reverse=True)

        return {
            "period1": period1,
            "period2": period2,
            "total_period1": total_this_month,
            "total_period2": total_last_month,
            "total_change": total_this_month - total_last_month,
            "total_change_pct": ((total_this_month - total_last_month) / total_last_month * 100) if total_last_month > 0 else 0,
            "categories": categories_list[:10]  # Top 10 changes
        }
