"""
Goal Management Service

CRUD operations and auto-suggestion for financial goals.
"""
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, List, Optional

from ..models import Goal, Transaction, Account
from ..models.models import generate_uuid


class GoalService:
    """Service for goal management and suggestions."""

    # Spending patterns that suggest goals
    GOAL_TRIGGERS = {
        'dining': {
            'threshold_monthly': 300,
            'suggestion': 'Reduce dining expenses',
            'savings_target': 0.3,  # Suggest saving 30% of overspend
        },
        'fast food': {
            'threshold_monthly': 200,
            'suggestion': 'Cut fast food spending',
            'savings_target': 0.4,
        },
        'shopping': {
            'threshold_monthly': 500,
            'suggestion': 'Build shopping budget',
            'savings_target': 0.25,
        },
        'subscription': {
            'threshold_monthly': 100,
            'suggestion': 'Audit subscriptions',
            'savings_target': 0.5,
        },
        'software': {
            'threshold_monthly': 100,
            'suggestion': 'Review software costs',
            'savings_target': 0.3,
        }
    }

    def __init__(self, db: Session):
        self.db = db

    # ================== CRUD Operations ==================

    def create_goal(self, user_id: str, data: Dict) -> Goal:
        """Create a new financial goal."""
        goal = Goal(
            id=generate_uuid(),
            user_id=user_id,
            name=data['name'],
            description=data.get('description'),
            target_amount=data['target_amount'],
            current_amount=data.get('current_amount', 0.0),
            monthly_allocation=data.get('monthly_allocation'),
            deadline=data.get('deadline'),
            priority=data.get('priority', 'medium'),
            auto_suggested=data.get('auto_suggested', False),
            suggestion_reason=data.get('suggestion_reason'),
            related_category=data.get('related_category')
        )

        # Auto-calculate monthly allocation if deadline provided
        if goal.deadline and not goal.monthly_allocation:
            goal.monthly_allocation = self._calculate_monthly_allocation(goal)

        self.db.add(goal)
        self.db.commit()
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID."""
        return self.db.query(Goal).filter(Goal.id == goal_id).first()

    def get_user_goals(self, user_id: str, status: Optional[str] = None) -> List[Goal]:
        """Get all goals for a user, optionally filtered by status."""
        query = self.db.query(Goal).filter(Goal.user_id == user_id)

        if status:
            query = query.filter(Goal.status == status)

        return query.order_by(Goal.priority.desc(), Goal.deadline.asc()).all()

    def update_goal(self, goal_id: str, data: Dict) -> Optional[Goal]:
        """Update a goal."""
        goal = self.get_goal(goal_id)
        if not goal:
            return None

        for key, value in data.items():
            if value is not None and hasattr(goal, key):
                setattr(goal, key, value)

        # Check if completed
        if goal.current_amount >= goal.target_amount and goal.status == 'active':
            goal.status = 'completed'
            goal.completed_at = datetime.utcnow()

        goal.updated_at = datetime.utcnow()
        self.db.commit()
        return goal

    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal."""
        goal = self.get_goal(goal_id)
        if goal:
            self.db.delete(goal)
            self.db.commit()
            return True
        return False

    def add_progress(self, goal_id: str, amount: float) -> Optional[Goal]:
        """Add progress to a goal."""
        goal = self.get_goal(goal_id)
        if not goal:
            return None

        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.status = 'completed'
            goal.completed_at = datetime.utcnow()

        goal.updated_at = datetime.utcnow()
        self.db.commit()
        return goal

    # ================== Goal Calculations ==================

    def get_goal_with_progress(self, goal: Goal) -> Dict:
        """Get goal with calculated progress metrics."""
        progress_pct = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0

        months_to_goal = None
        on_track = None

        if goal.monthly_allocation and goal.monthly_allocation > 0:
            remaining = goal.target_amount - goal.current_amount
            months_to_goal = int(remaining / goal.monthly_allocation) if remaining > 0 else 0

            # Check if on track based on deadline
            if goal.deadline:
                months_until_deadline = (goal.deadline.year - datetime.now().year) * 12 + (goal.deadline.month - datetime.now().month)
                on_track = months_to_goal <= months_until_deadline

        return {
            'id': goal.id,
            'user_id': goal.user_id,
            'name': goal.name,
            'description': goal.description,
            'target_amount': goal.target_amount,
            'current_amount': goal.current_amount,
            'monthly_allocation': goal.monthly_allocation,
            'deadline': goal.deadline,
            'priority': goal.priority,
            'status': goal.status,
            'auto_suggested': goal.auto_suggested,
            'suggestion_reason': goal.suggestion_reason,
            'related_category': goal.related_category,
            'created_at': goal.created_at,
            'updated_at': goal.updated_at,
            'completed_at': goal.completed_at,
            'progress_percentage': round(progress_pct, 1),
            'months_to_goal': months_to_goal,
            'on_track': on_track
        }

    def _calculate_monthly_allocation(self, goal: Goal) -> float:
        """Calculate required monthly savings to reach goal by deadline."""
        if not goal.deadline:
            return 0.0

        today = date.today()
        months_remaining = (goal.deadline.year - today.year) * 12 + (goal.deadline.month - today.month)

        if months_remaining <= 0:
            return goal.target_amount - goal.current_amount  # Due immediately

        remaining = goal.target_amount - goal.current_amount
        return round(remaining / months_remaining, 2)

    # ================== Goal Suggestions ==================

    def suggest_goals(self, user_id: str, monthly_income: Optional[float] = None) -> List[Dict]:
        """
        Analyze spending patterns and suggest goals.

        Returns list of suggested goals based on:
        1. High spending categories
        2. Spending trends (increasing)
        3. Standard financial goals (emergency fund)
        """
        suggestions = []

        # Get last month's spending by category
        spending = self._get_category_spending(user_id)

        # Check each trigger
        for category, trigger in self.GOAL_TRIGGERS.items():
            cat_spending = spending.get(category.lower(), 0)

            if cat_spending > trigger['threshold_monthly']:
                overspend = cat_spending - trigger['threshold_monthly']
                monthly_savings = overspend * trigger['savings_target']

                suggestions.append({
                    'name': trigger['suggestion'],
                    'target_amount': round(monthly_savings * 6, 2),  # 6 months target
                    'monthly_allocation': round(monthly_savings, 2),
                    'reason': f"You spent ${cat_spending:.0f} on {category} last month, which is ${overspend:.0f} above typical.",
                    'related_category': category,
                    'priority': 'high' if overspend > 200 else 'medium'
                })

        # Standard suggestions based on income
        if monthly_income:
            # Emergency fund (3-6 months expenses)
            if not self._has_goal_type(user_id, 'emergency'):
                suggestions.append({
                    'name': 'Emergency Fund',
                    'target_amount': monthly_income * 3,
                    'monthly_allocation': monthly_income * 0.1,  # 10% of income
                    'reason': 'Financial experts recommend 3-6 months of expenses in an emergency fund.',
                    'related_category': None,
                    'priority': 'high'
                })

        return suggestions

    def _get_category_spending(self, user_id: str) -> Dict[str, float]:
        """Get last month's spending by category."""
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        last_month_start = month_start - relativedelta(months=1)

        results = self.db.query(
            Transaction.enriched_category,
            func.sum(func.abs(Transaction.amount)).label('total')
        ).join(Account).filter(
            and_(
                Transaction.date >= last_month_start,
                Transaction.date < month_start,
                Transaction.enriched_category.isnot(None),
                Transaction.amount < 0  # Expenses
            )
        ).group_by(Transaction.enriched_category).all()

        return {row.enriched_category.lower(): row.total for row in results if row.enriched_category}

    def _has_goal_type(self, user_id: str, keyword: str) -> bool:
        """Check if user already has a goal containing keyword."""
        exists = self.db.query(Goal).filter(
            and_(
                Goal.user_id == user_id,
                Goal.name.ilike(f'%{keyword}%'),
                Goal.status == 'active'
            )
        ).first()
        return exists is not None
