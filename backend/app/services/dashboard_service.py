"""
Dashboard Service - Analytics and Insights Generation
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
from typing import Dict, List, Optional
from ..models.models import Transaction, Account, Institution
import statistics


class DashboardService:
    """Generate insights and analytics for the dashboard"""

    def __init__(self, db: Session, user_id: str = None):
        self.db = db
        self.user_id = user_id

    def _user_filter(self):
        """Return filter for user's active institutions"""
        if self.user_id:
            return and_(
                Institution.user_id == self.user_id,
                Institution.status == "active"
            )
        return Institution.status == "active"

    def _is_expense(self, exclude_one_time: bool = True):
        """
        Filter for expense transactions across all account types.

        - Depository accounts (checking/savings): amount < 0 = expense
        - Credit accounts: amount > 0 = expense (increases balance owed)

        Excludes (not real spending):
        - Investment transfers (teller_category = 'investment')
        - Internal transfers (teller_category = 'transfer' or is_transfer = True)
        - Credit card payments (teller_category contains 'credit card payment')
        - Inter-account transfers (enriched_category contains 'transfer')
        - One-time expenses (when exclude_one_time=True, for budget calculations)

        Args:
            exclude_one_time: If True, excludes transactions marked as one-time
                            or exclude_from_budget=True. Use for budget baselines.
        """
        # Categories that are transfers/payments, not real spending
        non_spending_teller_categories = ['investment', 'transfer']
        non_spending_enriched_categories = [
            'inter account transfer', 'transfer to stock broker',
            'credit card payment', 'payment'
        ]

        base_filter = and_(
            or_(
                and_(Account.type == 'depository', Transaction.amount < 0),
                and_(Account.type == 'credit', Transaction.amount > 0)
            ),
            # Exclude non-spending by teller_category
            or_(Transaction.teller_category.is_(None), ~Transaction.teller_category.in_(non_spending_teller_categories)),
            # Exclude non-spending by enriched_category
            or_(Transaction.enriched_category.is_(None), ~Transaction.enriched_category.in_(non_spending_enriched_categories)),
            # Exclude flagged transfers
            or_(Transaction.is_transfer.is_(None), Transaction.is_transfer == False)
        )

        # Optionally exclude one-time expenses from budget calculations
        if exclude_one_time:
            base_filter = and_(
                base_filter,
                or_(
                    Transaction.exclude_from_budget.is_(None),
                    Transaction.exclude_from_budget == False
                )
            )

        return base_filter

    def get_daily_insight(self) -> Dict:
        """
        Generate the most relevant daily insight

        Priority:
        1. Urgent (spending >50% above normal)
        2. Important (trends >20%)
        3. Informational (positive reinforcement)
        4. Motivational (fallback)
        """
        # Get this month vs last month comparison
        comparison = self.get_monthly_comparison()

        # Find biggest anomaly
        biggest_change = None
        biggest_change_pct = 0

        for category, data in comparison['categories'].items():
            if data['change_pct'] and abs(data['change_pct']) > abs(biggest_change_pct):
                biggest_change_pct = data['change_pct']
                biggest_change = {
                    'category': category,
                    'this_month': data['this_month'],
                    'last_month': data['last_month'],
                    'change_pct': data['change_pct']
                }

        # Generate insight based on biggest change
        if biggest_change and abs(biggest_change_pct) > 50:
            # Urgent/Important
            direction = "more" if biggest_change_pct > 0 else "less"
            emoji = "🔥" if biggest_change_pct > 0 else "🎉"

            insight = {
                'type': 'urgent' if abs(biggest_change_pct) > 100 else 'important',
                'emoji': emoji,
                'title': f"You're spending {abs(biggest_change_pct):.0f}% {direction} on {biggest_change['category']} this month",
                'description': f"${biggest_change['this_month']:.2f} vs ${biggest_change['last_month']:.2f} last month",
                'action': self._get_action_suggestion(biggest_change['category'], biggest_change_pct),
                'category': biggest_change['category']
            }
        else:
            # Positive reinforcement
            insight = {
                'type': 'motivational',
                'emoji': '✨',
                'title': "You're doing great!",
                'description': f"Spending is relatively stable compared to last month",
                'action': "Keep up the good work with your budget!",
                'category': None
            }

        return insight

    def _get_action_suggestion(self, category: str, change_pct: float) -> str:
        """Get actionable suggestion based on category and change"""

        if change_pct > 0:  # Spending increased
            suggestions = {
                'groceries': "Try meal planning to reduce grocery store trips",
                'dining': "Consider cooking at home more often",
                'software': "Review subscriptions - cancel unused services",
                'shopping': "Wait 24 hours before making purchases",
                'coffee': "Brew coffee at home to save money",
                'gas': "Consider carpooling or public transit",
                'fast food': "Meal prep on Sundays to avoid takeout"
            }
        else:  # Spending decreased
            suggestions = {
                'groceries': "Great job planning meals!",
                'dining': "Awesome - you cooked more this month!",
                'software': "Nice work cutting subscriptions!",
                'shopping': "You're being more mindful of purchases!",
                'coffee': "Brewing at home is paying off!",
                'gas': "Good savings on transportation!",
                'fast food': "Cooking at home is working!"
            }

        return suggestions.get(category.lower(), "Keep monitoring your spending patterns")

    def get_spending_velocity(self) -> Dict:
        """
        Calculate spending pace for current month

        Returns:
        - Amount spent so far
        - Days elapsed
        - Daily average
        - Projected month-end total
        - Comparison to last month
        """
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        days_elapsed = (now - month_start).days + 1
        days_in_month = (datetime(now.year, now.month + 1, 1) if now.month < 12
                        else datetime(now.year + 1, 1, 1)) - month_start
        days_in_month = days_in_month.days

        # This month spending (excluding internal transfers)
        # Join with Account and Institution to filter by user
        this_month_total = self.db.query(
            func.sum(func.abs(Transaction.amount))
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                extract('year', Transaction.date) == now.year,
                extract('month', Transaction.date) == now.month,
                Transaction.enriched_merchant.isnot(None),  # Only real merchants
                self._is_expense(),
                self._user_filter()
            )
        ).scalar() or 0

        # Last month total
        last_month = month_start - timedelta(days=1)
        last_month_total = self.db.query(
            func.sum(func.abs(Transaction.amount))
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                extract('year', Transaction.date) == last_month.year,
                extract('month', Transaction.date) == last_month.month,
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).scalar() or 0

        # Calculate projections
        daily_average = this_month_total / days_elapsed if days_elapsed > 0 else 0
        projected_total = daily_average * days_in_month

        # Progress percentage
        time_progress = (days_elapsed / days_in_month) * 100
        spending_progress = (this_month_total / projected_total * 100) if projected_total > 0 else 0

        return {
            'spent_so_far': this_month_total,
            'days_elapsed': days_elapsed,
            'days_in_month': days_in_month,
            'time_progress': time_progress,
            'spending_progress': min(spending_progress, 100),  # Cap at 100%
            'daily_average': daily_average,
            'projected_total': projected_total,
            'last_month_total': last_month_total,
            'vs_last_month': projected_total - last_month_total,
            'vs_last_month_pct': ((projected_total - last_month_total) / last_month_total * 100) if last_month_total > 0 else 0,
            'on_track': spending_progress <= (time_progress + 10)  # Within 10% is "on track"
        }

    def get_monthly_comparison(self) -> Dict:
        """
        Compare this month vs last month by category

        Returns dict of categories with this_month, last_month, change
        """
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        last_month = month_start - timedelta(days=1)
        last_month_start = datetime(last_month.year, last_month.month, 1)

        # This month by category (join with Account and Institution to filter by user)
        this_month_query = self.db.query(
            Transaction.enriched_category,
            func.sum(func.abs(Transaction.amount)).label('total')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                extract('year', Transaction.date) == now.year,
                extract('month', Transaction.date) == now.month,
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(Transaction.enriched_category).all()

        # Last month by category
        last_month_query = self.db.query(
            Transaction.enriched_category,
            func.sum(func.abs(Transaction.amount)).label('total')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                extract('year', Transaction.date) == last_month.year,
                extract('month', Transaction.date) == last_month.month,
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(Transaction.enriched_category).all()

        # Build comparison dict
        this_month_dict = {row.enriched_category: abs(row.total) for row in this_month_query if row.enriched_category}
        last_month_dict = {row.enriched_category: abs(row.total) for row in last_month_query if row.enriched_category}

        # Combine all categories
        all_categories = set(this_month_dict.keys()) | set(last_month_dict.keys())

        categories = {}
        for category in all_categories:
            this_val = this_month_dict.get(category, 0)
            last_val = last_month_dict.get(category, 0)

            change = this_val - last_val
            change_pct = (change / last_val * 100) if last_val > 0 else (100 if this_val > 0 else 0)

            categories[category] = {
                'this_month': this_val,
                'last_month': last_val,
                'change': change,
                'change_pct': change_pct,
                'trend': 'up' if change > 0 else ('down' if change < 0 else 'same')
            }

        # Sort by this month spending
        categories = dict(sorted(categories.items(), key=lambda x: x[1]['this_month'], reverse=True))

        return {
            'month': now.strftime('%B %Y'),
            'last_month': last_month.strftime('%B %Y'),
            'categories': categories
        }

    def get_category_breakdown_with_merchants(self, category: str, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        """
        Get merchant breakdown for a specific category

        Returns merchants contributing to this category
        """
        now = datetime.now()
        target_month = month or now.month
        target_year = year or now.year

        results = self.db.query(
            Transaction.enriched_merchant,
            func.sum(func.abs(Transaction.amount)).label('total'),
            func.count(Transaction.id).label('count')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                extract('year', Transaction.date) == target_year,
                extract('month', Transaction.date) == target_month,
                Transaction.enriched_category == category,
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(Transaction.enriched_merchant).all()

        total = sum(row.total for row in results)

        merchants = []
        for row in results:
            if not row.enriched_merchant:
                continue

            amount = row.total  # Already absolute from query
            percentage = (amount / total * 100) if total > 0 else 0

            merchants.append({
                'merchant': row.enriched_merchant,
                'amount': amount,
                'count': row.count,
                'percentage': percentage
            })

        merchants.sort(key=lambda x: x['amount'], reverse=True)

        return {
            'category': category,
            'total': total,
            'merchants': merchants
        }

    def get_category_breakdown(self, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        """
        Get spending breakdown by category for a specific month

        Returns categories sorted by amount with percentages
        """
        now = datetime.now()
        target_month = month or now.month
        target_year = year or now.year

        # Get total and by category (join with Account and Institution to filter by user)
        results = self.db.query(
            Transaction.enriched_category,
            func.sum(func.abs(Transaction.amount)).label('total'),
            func.count(Transaction.id).label('count')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                extract('year', Transaction.date) == target_year,
                extract('month', Transaction.date) == target_month,
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(Transaction.enriched_category).all()

        # Calculate total
        total = sum(row.total for row in results)

        # Build category list
        categories = []
        for row in results:
            if not row.enriched_category:
                continue

            amount = row.total  # Already absolute from query
            percentage = (amount / total * 100) if total > 0 else 0

            categories.append({
                'category': row.enriched_category,
                'amount': amount,
                'count': row.count,
                'percentage': percentage,
                'emoji': self._get_category_emoji(row.enriched_category)
            })

        # Sort by amount
        categories.sort(key=lambda x: x['amount'], reverse=True)

        return {
            'total': total,
            'categories': categories
        }

    def _get_category_emoji(self, category: str) -> str:
        """Get emoji for category"""
        emoji_map = {
            'groceries': '🛒',
            'dining': '🍔',
            'fast food': '🍔',
            'restaurant': '🍽️',
            'gas': '⛽',
            'gas station': '⛽',
            'software': '💻',
            'subscription': '💻',
            'travel': '✈️',
            'education': '🏫',
            'coffee': '☕',
            'shopping': '🛍️',
            'healthcare': '🏥',
            'medical': '🏥',
            'entertainment': '🎬',
            'utilities': '💡',
            'pharmacy': '💊'
        }

        category_lower = category.lower() if category else ''

        for key, emoji in emoji_map.items():
            if key in category_lower:
                return emoji

        return '📦'

    def get_top_merchants(self, limit: int = 10) -> List[Dict]:
        """
        Get top merchants with context/insights

        Returns merchants sorted by total spend with visit counts
        """
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)

        results = self.db.query(
            Transaction.enriched_merchant,
            func.sum(func.abs(Transaction.amount)).label('total'),
            func.count(Transaction.id).label('visits'),
            func.avg(func.abs(Transaction.amount)).label('avg_amount')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                extract('year', Transaction.date) == now.year,
                extract('month', Transaction.date) == now.month,
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(Transaction.enriched_merchant).all()

        merchants = []
        for row in results:
            total = row.total  # Already absolute from query
            avg = row.avg_amount  # Already absolute from query

            # Generate insight
            insight = None
            if row.visits >= 15:
                insight = "Most visited"
            elif avg > 100:
                insight = "High avg spend"
            elif total > 500:
                insight = "Large total spend"

            merchants.append({
                'merchant': row.enriched_merchant,
                'total': total,
                'visits': row.visits,
                'avg_per_visit': avg,
                'insight': insight
            })

        # Sort by total
        merchants.sort(key=lambda x: x['total'], reverse=True)

        return merchants[:limit]

    def get_transactions_by_period(self, period: str = 'month', date: Optional[datetime] = None) -> List[Dict]:
        """
        Get transactions for a specific time period

        Args:
            period: 'day', 'week', or 'month'
            date: Reference date (defaults to today)

        Returns list of transactions grouped by day
        """
        target_date = date or datetime.now()

        if period == 'day':
            start_date = datetime(target_date.year, target_date.month, target_date.day)
            end_date = start_date + timedelta(days=1)
        elif period == 'week':
            # Start from Monday of the week
            start_date = target_date - timedelta(days=target_date.weekday())
            start_date = datetime(start_date.year, start_date.month, start_date.day)
            end_date = start_date + timedelta(days=7)
        else:  # month
            start_date = datetime(target_date.year, target_date.month, 1)
            if target_date.month == 12:
                end_date = datetime(target_date.year + 1, 1, 1)
            else:
                end_date = datetime(target_date.year, target_date.month + 1, 1)

        # Get transactions (join with Account and Institution to filter by user)
        results = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                Transaction.date >= start_date,
                Transaction.date < end_date,
                Transaction.enriched_merchant.isnot(None),
                self._user_filter()
            )
        ).order_by(Transaction.date.desc()).all()

        # Group by day
        transactions_by_day = {}
        for txn in results:
            day_key = txn.date.strftime('%Y-%m-%d')
            if day_key not in transactions_by_day:
                transactions_by_day[day_key] = {
                    'date': day_key,
                    'total': 0,
                    'transactions': []
                }

            transactions_by_day[day_key]['total'] += abs(txn.amount)
            transactions_by_day[day_key]['transactions'].append({
                'id': txn.id,
                'merchant': txn.enriched_merchant,
                'category': txn.enriched_category,
                'amount': abs(txn.amount),
                'time': txn.date.strftime('%H:%M') if txn.date else None,
                'description': txn.description,
                'emoji': self._get_category_emoji(txn.enriched_category)
            })

        # Convert to list and sort
        daily_transactions = list(transactions_by_day.values())
        daily_transactions.sort(key=lambda x: x['date'], reverse=True)

        return daily_transactions

    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        """Get recent transactions with enrichment data"""

        results = self.db.query(Transaction).join(
            Account, Transaction.account_id == Account.id
        ).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                Transaction.enriched_merchant.isnot(None),
                self._user_filter()
            )
        ).order_by(Transaction.date.desc()).limit(limit).all()

        transactions = []
        for txn in results:
            transactions.append({
                'id': txn.id,
                'merchant': txn.enriched_merchant,
                'category': txn.enriched_category,
                'amount': abs(txn.amount),
                'date': txn.date.isoformat() if txn.date else None,
                'description': txn.description,
                'emoji': self._get_category_emoji(txn.enriched_category)
            })

        return transactions

    def get_spending_trend(self, budget: Optional[float] = None) -> Dict:
        """
        Get daily cumulative spending for trend visualization

        Returns:
        - Daily spending data points with cumulative totals
        - Budget pace line (linear projection)
        - Last month comparison line
        """
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1)
        days_in_month = (datetime(now.year, now.month + 1, 1) if now.month < 12
                        else datetime(now.year + 1, 1, 1)) - month_start
        days_in_month = days_in_month.days

        # Get last month info
        last_month = month_start - timedelta(days=1)
        last_month_start = datetime(last_month.year, last_month.month, 1)

        # Get daily spending for this month
        this_month_daily = self.db.query(
            func.date(Transaction.date).label('day'),
            func.sum(func.abs(Transaction.amount)).label('total')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                Transaction.date >= month_start,
                Transaction.date < now + timedelta(days=1),
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(func.date(Transaction.date)).order_by(func.date(Transaction.date)).all()

        # Get daily spending for last month (full month)
        last_month_daily = self.db.query(
            func.date(Transaction.date).label('day'),
            func.sum(func.abs(Transaction.amount)).label('total')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                Transaction.date >= last_month_start,
                Transaction.date < month_start,
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(func.date(Transaction.date)).order_by(func.date(Transaction.date)).all()

        # Calculate last month total for budget reference
        last_month_total = sum(row.total for row in last_month_daily)

        # Use provided budget or last month's total as reference
        budget_amount = budget if budget else last_month_total
        daily_budget_pace = budget_amount / days_in_month if days_in_month > 0 else 0

        # Build cumulative data for this month
        cumulative = 0
        this_month_data = []
        this_month_by_day = {row.day.strftime('%Y-%m-%d') if hasattr(row.day, 'strftime') else str(row.day): row.total for row in this_month_daily}

        for day_num in range(1, now.day + 1):
            day_date = datetime(now.year, now.month, day_num)
            day_str = day_date.strftime('%Y-%m-%d')
            daily_amount = this_month_by_day.get(day_str, 0)
            cumulative += daily_amount

            this_month_data.append({
                'day': day_num,
                'date': day_str,
                'daily': daily_amount,
                'cumulative': cumulative,
                'budget_pace': daily_budget_pace * day_num
            })

        # Build cumulative data for last month (for comparison)
        last_cumulative = 0
        last_month_data = []
        last_month_by_day = {}
        for row in last_month_daily:
            day_str = row.day.strftime('%Y-%m-%d') if hasattr(row.day, 'strftime') else str(row.day)
            last_month_by_day[day_str] = row.total

        # Get days in last month
        days_in_last_month = (month_start - last_month_start).days
        for day_num in range(1, days_in_last_month + 1):
            day_date = datetime(last_month.year, last_month.month, day_num)
            day_str = day_date.strftime('%Y-%m-%d')
            daily_amount = last_month_by_day.get(day_str, 0)
            last_cumulative += daily_amount

            last_month_data.append({
                'day': day_num,
                'cumulative': last_cumulative
            })

        # Current totals
        current_total = cumulative
        projected_total = (current_total / now.day) * days_in_month if now.day > 0 else 0

        return {
            'this_month': this_month_data,
            'last_month': last_month_data,
            'budget': budget_amount,
            'current_total': current_total,
            'projected_total': projected_total,
            'days_elapsed': now.day,
            'days_in_month': days_in_month,
            'on_track': current_total <= (daily_budget_pace * now.day * 1.1),  # Within 10%
            'month_name': now.strftime('%B'),
            'last_month_name': last_month.strftime('%B'),
            'last_month_total': last_month_total
        }

    def get_spending_trend_by_view(self, view: str = 'daily', budget: Optional[float] = None) -> Dict:
        """
        Get spending trend data based on view type.

        Args:
            view: 'daily' (days in current month), 'monthly' (past 12 months), 'yearly' (past 5 years)
            budget: Optional budget amount for reference

        Returns:
            Spending trend data formatted for the requested view
        """
        if view == 'daily':
            return self.get_spending_trend(budget)
        elif view == 'monthly':
            return self._get_monthly_trend(budget)
        elif view == 'yearly':
            return self._get_yearly_trend(budget)
        else:
            return self.get_spending_trend(budget)

    def _get_monthly_trend(self, budget: Optional[float] = None) -> Dict:
        """
        Get monthly spending totals for the past 12 months.
        Uses a single aggregated query for performance.
        """
        now = datetime.now()

        # Calculate date range for past 12 months
        # Go back 11 months from current month
        start_month = now.month - 11
        start_year = now.year
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        start_date = datetime(start_year, start_month, 1)

        # Single query to get all monthly totals
        results = self.db.query(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month'),
            func.sum(func.abs(Transaction.amount)).label('total')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                Transaction.date >= start_date,
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(
            extract('year', Transaction.date),
            extract('month', Transaction.date)
        ).all()

        # Convert results to dict for easy lookup
        results_dict = {(int(r.year), int(r.month)): float(r.total) for r in results}

        # Build monthly data array for past 12 months
        monthly_data = []
        total_spending = 0

        for i in range(11, -1, -1):
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            month_total = results_dict.get((target_year, target_month), 0)
            total_spending += month_total

            month_date = datetime(target_year, target_month, 1)
            monthly_data.append({
                'period': month_date.strftime('%b %Y'),
                'short_label': month_date.strftime('%b'),
                'month': target_month,
                'year': target_year,
                'amount': month_total,
                'is_current': target_year == now.year and target_month == now.month
            })

        # Calculate average and trends
        avg_spending = total_spending / 12 if monthly_data else 0
        current_month = monthly_data[-1]['amount'] if monthly_data else 0
        last_month = monthly_data[-2]['amount'] if len(monthly_data) >= 2 else 0

        # Calculate budget pace (monthly average or user budget)
        budget_amount = budget if budget else avg_spending

        return {
            'view': 'monthly',
            'data': monthly_data,
            'total': total_spending,
            'average': avg_spending,
            'current': current_month,
            'previous': last_month,
            'budget': budget_amount,
            'change': current_month - last_month,
            'change_pct': ((current_month - last_month) / last_month * 100) if last_month > 0 else 0,
            'period_label': 'Last 12 Months'
        }

    def _get_yearly_trend(self, budget: Optional[float] = None) -> Dict:
        """
        Get yearly spending totals for the past 5 years.
        Uses a single aggregated query for performance.
        """
        now = datetime.now()
        current_year = now.year
        start_year = current_year - 4
        start_date = datetime(start_year, 1, 1)

        # Single query to get all yearly totals
        results = self.db.query(
            extract('year', Transaction.date).label('year'),
            func.sum(func.abs(Transaction.amount)).label('total')
        ).join(Account, Transaction.account_id == Account.id).join(
            Institution, Account.institution_id == Institution.id
        ).filter(
            and_(
                Transaction.date >= start_date,
                Transaction.enriched_merchant.isnot(None),
                self._is_expense(),
                self._user_filter()
            )
        ).group_by(
            extract('year', Transaction.date)
        ).all()

        # Convert results to dict for easy lookup
        results_dict = {int(r.year): float(r.total) for r in results}

        # Build yearly data array
        yearly_data = []
        total_spending = 0

        for year in range(start_year, current_year + 1):
            year_total = results_dict.get(year, 0)
            total_spending += year_total

            # For current year, project full year
            if year == current_year:
                year_start = datetime(year, 1, 1)
                days_elapsed = (now - year_start).days + 1
                days_in_year = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
                projected = (year_total / days_elapsed) * days_in_year if days_elapsed > 0 else 0
            else:
                projected = None

            yearly_data.append({
                'period': str(year),
                'short_label': str(year),
                'year': year,
                'amount': year_total,
                'projected': projected,
                'is_current': year == current_year
            })

        # Calculate trends
        current_year_amount = yearly_data[-1]['amount'] if yearly_data else 0
        last_year_amount = yearly_data[-2]['amount'] if len(yearly_data) >= 2 else 0
        avg_spending = total_spending / len(yearly_data) if yearly_data else 0

        # Calculate budget (yearly average or user budget * 12)
        budget_amount = (budget * 12) if budget else avg_spending

        return {
            'view': 'yearly',
            'data': yearly_data,
            'total': total_spending,
            'average': avg_spending,
            'current': current_year_amount,
            'previous': last_year_amount,
            'budget': budget_amount,
            'change': current_year_amount - last_year_amount,
            'change_pct': ((current_year_amount - last_year_amount) / last_year_amount * 100) if last_year_amount > 0 else 0,
            'period_label': 'Last 5 Years',
            'current_year_projected': yearly_data[-1]['projected'] if yearly_data else None
        }
