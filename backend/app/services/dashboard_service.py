"""
Dashboard Service - Analytics and Insights Generation
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import Dict, List, Optional
from ..models.models import Transaction
import statistics


class DashboardService:
    """Generate insights and analytics for the dashboard"""

    def __init__(self, db: Session):
        self.db = db

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
        this_month_total = self.db.query(func.sum(Transaction.amount)).filter(
            and_(
                extract('year', Transaction.date) == now.year,
                extract('month', Transaction.date) == now.month,
                Transaction.enriched_merchant.isnot(None),  # Only real merchants
                Transaction.amount < 0  # Only debits
            )
        ).scalar() or 0

        this_month_total = abs(this_month_total)

        # Last month total
        last_month = month_start - timedelta(days=1)
        last_month_total = self.db.query(func.sum(Transaction.amount)).filter(
            and_(
                extract('year', Transaction.date) == last_month.year,
                extract('month', Transaction.date) == last_month.month,
                Transaction.enriched_merchant.isnot(None),
                Transaction.amount < 0
            )
        ).scalar() or 0

        last_month_total = abs(last_month_total)

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

        # This month by category
        this_month_query = self.db.query(
            Transaction.enriched_category,
            func.sum(Transaction.amount).label('total')
        ).filter(
            and_(
                extract('year', Transaction.date) == now.year,
                extract('month', Transaction.date) == now.month,
                Transaction.enriched_merchant.isnot(None),
                Transaction.amount < 0
            )
        ).group_by(Transaction.enriched_category).all()

        # Last month by category
        last_month_query = self.db.query(
            Transaction.enriched_category,
            func.sum(Transaction.amount).label('total')
        ).filter(
            and_(
                extract('year', Transaction.date) == last_month.year,
                extract('month', Transaction.date) == last_month.month,
                Transaction.enriched_merchant.isnot(None),
                Transaction.amount < 0
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

    def get_category_breakdown(self, month: Optional[int] = None, year: Optional[int] = None) -> Dict:
        """
        Get spending breakdown by category for a specific month

        Returns categories sorted by amount with percentages
        """
        now = datetime.now()
        target_month = month or now.month
        target_year = year or now.year

        # Get total and by category
        results = self.db.query(
            Transaction.enriched_category,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).filter(
            and_(
                extract('year', Transaction.date) == target_year,
                extract('month', Transaction.date) == target_month,
                Transaction.enriched_merchant.isnot(None),
                Transaction.amount < 0
            )
        ).group_by(Transaction.enriched_category).all()

        # Calculate total
        total = sum(abs(row.total) for row in results)

        # Build category list
        categories = []
        for row in results:
            if not row.enriched_category:
                continue

            amount = abs(row.total)
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
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('visits'),
            func.avg(Transaction.amount).label('avg_amount')
        ).filter(
            and_(
                extract('year', Transaction.date) == now.year,
                extract('month', Transaction.date) == now.month,
                Transaction.enriched_merchant.isnot(None),
                Transaction.amount < 0
            )
        ).group_by(Transaction.enriched_merchant).all()

        merchants = []
        for row in results:
            total = abs(row.total)
            avg = abs(row.avg_amount)

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

    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        """Get recent transactions with enrichment data"""

        results = self.db.query(Transaction).filter(
            Transaction.enriched_merchant.isnot(None)
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
