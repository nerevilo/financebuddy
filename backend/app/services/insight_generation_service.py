"""
LLM-Powered Insight Generation Service

Generates 3 daily insights using Gemini Flash (FREE tier).
"""
import json
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, List, Optional

from ..models import Insight, Goal, IncomeSource, UserProfile
from ..models.models import generate_uuid
from ..core.config import get_settings
from ..core.logging_config import get_logger
from .dashboard_service import DashboardService
from .income_service import IncomeService
from .goal_service import GoalService

logger = get_logger(__name__)

# Optional import for Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class InsightGenerationService:
    """
    Generate personalized daily insights using LLM.

    Uses Gemini Flash (FREE tier - 1,500 requests/day)
    Generates exactly 3 insights: Alert, Opportunity, Optimization
    """

    PROMPT_VERSION = "v1.0"

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.dashboard_service = DashboardService(db)
        self.income_service = IncomeService(db)
        self.goal_service = GoalService(db)

        # Initialize Gemini
        self.model = None
        if GEMINI_AVAILABLE and self.settings.gemini_api_key:
            genai.configure(api_key=self.settings.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')

    async def generate_daily_insights(self, user_id: str) -> List[Insight]:
        """
        Generate 3 daily insights for a user.

        Returns:
            List of 3 Insight objects: [alert, opportunity, optimization]
        """
        # Check if already generated today
        existing = self._get_todays_insights(user_id)
        if existing:
            return existing

        # Gather context data
        context = self._gather_context(user_id)

        # Generate insights with LLM
        if self.model:
            insights_data = self._generate_with_gemini(context)
        else:
            # Fallback to rule-based insights
            insights_data = self._generate_fallback_insights(context)

        # Save insights to database
        saved_insights = []
        for insight_data in insights_data:
            insight = self._save_insight(user_id, insight_data)
            saved_insights.append(insight)

        return saved_insights

    def _gather_context(self, user_id: str) -> Dict:
        """Gather all context data for insight generation."""

        # Spending velocity
        velocity = self.dashboard_service.get_spending_velocity()

        # Category comparison
        comparison = self.dashboard_service.get_monthly_comparison()

        # Goals progress
        goals = self.goal_service.get_user_goals(user_id, status='active')
        goals_data = [self.goal_service.get_goal_with_progress(g) for g in goals]

        # Income summary
        income_sources = self.income_service.get_income_sources(user_id)
        monthly_income = self.income_service.calculate_monthly_income(user_id)

        # Recent anomalies (categories with >30% change)
        anomalies = []
        for category, data in comparison.get('categories', {}).items():
            if data.get('change_pct') and abs(data['change_pct']) > 30:
                anomalies.append({
                    'category': category,
                    'change_pct': data['change_pct'],
                    'this_month': data['this_month'],
                    'last_month': data['last_month']
                })

        # User profile context
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        return {
            'velocity': velocity,
            'comparison': comparison,
            'goals': goals_data,
            'monthly_income': monthly_income,
            'income_expense_ratio': (velocity.get('projected_total', 0) / monthly_income) if monthly_income > 0 else None,
            'anomalies': anomalies,
            'profile': {
                'household_size': profile.household_size if profile else 1,
                'context_notes': profile.context_notes if profile else None,
            },
            'date': datetime.now().strftime('%B %d, %Y')
        }

    def _generate_with_gemini(self, context: Dict) -> List[Dict]:
        """Generate insights using Gemini Flash."""

        prompt = self._build_prompt(context)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,  # Some creativity for insights
                    "max_output_tokens": 1000,
                }
            )

            # Parse JSON response
            insights = self._parse_insights_response(response.text)

            # Add metadata
            for insight in insights:
                insight['llm_source'] = 'gemini_flash'
                insight['generation_cost'] = 0.0  # Free tier
                insight['prompt_version'] = self.PROMPT_VERSION

            return insights

        except Exception as e:
            logger.error("Gemini insight generation error", extra={"error": str(e)})
            return self._generate_fallback_insights(context)

    def _build_prompt(self, context: Dict) -> str:
        """Build the LLM prompt with user context."""

        # Format goals for prompt
        goals_text = "None set"
        if context.get('goals'):
            goals_text = "\n".join([
                f"- {g.get('name')}: ${g.get('current_amount', 0):.0f} / ${g.get('target_amount', 0):.0f} ({g.get('progress_percentage', 0):.0f}%)"
                for g in context['goals'][:3]
            ])

        # Format anomalies
        anomalies_text = "No significant changes"
        if context.get('anomalies'):
            anomalies_text = "\n".join([
                f"- {a['category']}: {a['change_pct']:+.0f}% (${a['this_month']:.0f} vs ${a['last_month']:.0f})"
                for a in context['anomalies'][:5]
            ])

        velocity = context.get('velocity', {})

        prompt = f"""You are a helpful personal finance assistant. Generate exactly 3 daily insights for a user based on their financial data.

## User's Financial Context ({context['date']})

### Spending Velocity
- Spent this month: ${velocity.get('spent_so_far', 0):.2f}
- Daily average: ${velocity.get('daily_average', 0):.2f}
- Projected month total: ${velocity.get('projected_total', 0):.2f}
- Last month total: ${velocity.get('last_month_total', 0):.2f}
- On track: {'Yes' if velocity.get('on_track') else 'No - spending faster than last month'}

### Income & Expenses
- Monthly income: ${context.get('monthly_income', 0):.2f}
- Income/Expense ratio: {context.get('income_expense_ratio') or 'Unknown'}

### Active Goals
{goals_text}

### Spending Changes (vs Last Month)
{anomalies_text}

### User Context
- Household size: {context['profile'].get('household_size', 1)}
- Notes: {context['profile'].get('context_notes') or 'None provided'}

## Your Task

Generate exactly 3 insights in this JSON format:

```json
[
  {{
    "type": "alert",
    "title": "Short attention-grabbing title (max 60 chars)",
    "description": "2-3 sentences explaining the insight with specific numbers",
    "action": "One specific actionable step",
    "emoji": "relevant emoji",
    "category": "related spending category or null",
    "priority_score": 0.8,
    "amount_referenced": 123.45
  }},
  {{
    "type": "opportunity",
    "title": "...",
    "description": "...",
    "action": "...",
    "emoji": "...",
    "category": "...",
    "priority_score": 0.6,
    "amount_referenced": null
  }},
  {{
    "type": "optimization",
    "title": "...",
    "description": "...",
    "action": "...",
    "emoji": "...",
    "category": "...",
    "priority_score": 0.4,
    "amount_referenced": null
  }}
]
```

## Insight Types

1. **ALERT**: Urgent or important issue (overspending, unusual activity, goal at risk)
   - Focus on problems that need immediate attention
   - Use specific dollar amounts
   - Priority: 0.7-1.0

2. **OPPORTUNITY**: Savings potential, positive trends, rewards
   - Highlight ways to save money
   - Celebrate progress and wins
   - Priority: 0.4-0.7

3. **OPTIMIZATION**: Budget adjustments, habit improvements, goal strategies
   - Suggest tweaks to improve financial health
   - Long-term thinking
   - Priority: 0.3-0.6

## Requirements
- Be specific with numbers (use actual $ amounts from context)
- Make actions concrete and achievable TODAY
- Personalize based on user context
- Keep titles punchy and engaging
- Each insight should be unique and valuable

Respond ONLY with the JSON array, no other text."""

        return prompt

    def _parse_insights_response(self, response_text: str) -> List[Dict]:
        """Parse Gemini's JSON response."""
        try:
            # Try parsing as-is
            return json.loads(response_text)
        except:
            pass

        # Try extracting from code block
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end > start:
                try:
                    return json.loads(response_text[start:end].strip())
                except:
                    pass

        if "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end > start:
                try:
                    return json.loads(response_text[start:end].strip())
                except:
                    pass

        # Try extracting from [ to ]
        start = response_text.find("[")
        end = response_text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response_text[start:end])
            except:
                pass

        return []

    def _generate_fallback_insights(self, context: Dict) -> List[Dict]:
        """Generate rule-based insights when LLM is unavailable."""
        insights = []

        velocity = context.get('velocity', {})

        # Alert: Based on spending velocity
        if not velocity.get('on_track', True):
            change_pct = velocity.get('vs_last_month_pct', 0)
            insights.append({
                'type': 'alert',
                'title': f"Spending {abs(change_pct):.0f}% higher than last month",
                'description': f"You've spent ${velocity.get('spent_so_far', 0):.2f} so far this month. At this pace, you'll spend ${velocity.get('projected_total', 0):.2f} by month end, which is ${abs(velocity.get('vs_last_month', 0)):.2f} more than last month.",
                'action': "Review your recent purchases and identify any non-essential spending to cut back on.",
                'emoji': '\u26a0\ufe0f',
                'category': None,
                'priority_score': 0.8,
                'amount_referenced': velocity.get('projected_total'),
                'llm_source': 'fallback',
                'generation_cost': 0.0,
                'prompt_version': 'fallback'
            })
        else:
            insights.append({
                'type': 'alert',
                'title': "You're on track this month!",
                'description': f"Your spending is at ${velocity.get('spent_so_far', 0):.2f} with {velocity.get('days_in_month', 30) - velocity.get('days_elapsed', 0)} days left. You're pacing well compared to last month.",
                'action': "Keep monitoring your spending to maintain this great pace.",
                'emoji': '\u2705',
                'category': None,
                'priority_score': 0.5,
                'amount_referenced': velocity.get('spent_so_far'),
                'llm_source': 'fallback',
                'generation_cost': 0.0,
                'prompt_version': 'fallback'
            })

        # Opportunity: Based on anomalies (decreased spending)
        anomalies = context.get('anomalies', [])
        decreased = [a for a in anomalies if a.get('change_pct', 0) < -20]
        if decreased:
            best = min(decreased, key=lambda x: x['change_pct'])
            savings = best['last_month'] - best['this_month']
            insights.append({
                'type': 'opportunity',
                'title': f"Great savings on {best['category']}!",
                'description': f"You've reduced {best['category']} spending by {abs(best['change_pct']):.0f}% - from ${best['last_month']:.2f} to ${best['this_month']:.2f}. That's ${savings:.2f} saved!",
                'action': "Consider putting these savings toward your goals.",
                'emoji': '\U0001f389',
                'category': best['category'],
                'priority_score': 0.6,
                'amount_referenced': savings,
                'llm_source': 'fallback',
                'generation_cost': 0.0,
                'prompt_version': 'fallback'
            })
        else:
            insights.append({
                'type': 'opportunity',
                'title': "Look for subscription savings",
                'description': "Have you reviewed your recurring subscriptions lately? Many people have forgotten subscriptions they no longer use.",
                'action': "List all your subscriptions and cancel any you haven't used in 30 days.",
                'emoji': '\U0001f4a1',
                'category': 'subscription',
                'priority_score': 0.5,
                'amount_referenced': None,
                'llm_source': 'fallback',
                'generation_cost': 0.0,
                'prompt_version': 'fallback'
            })

        # Optimization: Based on goals or income ratio
        goals = context.get('goals', [])
        if goals:
            goal = goals[0]  # First goal
            progress = goal.get('progress_percentage', 0)
            insights.append({
                'type': 'optimization',
                'title': f"Goal progress: {goal.get('name', 'Your Goal')}",
                'description': f"You're {progress:.0f}% of the way to your ${goal.get('target_amount', 0):.0f} goal. {goal.get('months_to_goal', 'Unknown')} months to go at your current pace.",
                'action': f"Try to save ${goal.get('monthly_allocation', 0):.2f} this month to stay on track.",
                'emoji': '\U0001f3af',
                'category': None,
                'priority_score': 0.4,
                'amount_referenced': goal.get('monthly_allocation'),
                'llm_source': 'fallback',
                'generation_cost': 0.0,
                'prompt_version': 'fallback'
            })
        else:
            insights.append({
                'type': 'optimization',
                'title': "Set a financial goal",
                'description': "People with clear financial goals save 2x more than those without. Consider setting up an emergency fund or savings target.",
                'action': "Create your first financial goal in the Goals section.",
                'emoji': '\U0001f3af',
                'category': None,
                'priority_score': 0.4,
                'amount_referenced': None,
                'llm_source': 'fallback',
                'generation_cost': 0.0,
                'prompt_version': 'fallback'
            })

        return insights

    def _save_insight(self, user_id: str, data: Dict) -> Insight:
        """Save an insight to the database."""
        insight = Insight(
            id=generate_uuid(),
            user_id=user_id,
            type=data['type'],
            title=data['title'],
            description=data['description'],
            action=data.get('action'),
            emoji=data.get('emoji'),
            category=data.get('category'),
            amount_referenced=data.get('amount_referenced'),
            priority_score=data.get('priority_score', 0.5),
            llm_source=data.get('llm_source'),
            generation_cost=data.get('generation_cost', 0.0),
            prompt_version=data.get('prompt_version'),
            expires_at=datetime.utcnow() + timedelta(days=1),  # Valid for 24 hours
            generated_at=datetime.utcnow()
        )

        self.db.add(insight)
        self.db.commit()
        return insight

    def _get_todays_insights(self, user_id: str) -> Optional[List[Insight]]:
        """Get insights generated today."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        insights = self.db.query(Insight).filter(
            and_(
                Insight.user_id == user_id,
                Insight.generated_at >= today_start
            )
        ).order_by(Insight.priority_score.desc()).all()

        return insights if len(insights) >= 3 else None

    # ================== Feedback & History ==================

    def update_feedback(self, insight_id: str, feedback: str) -> Optional[Insight]:
        """Update user feedback on an insight."""
        insight = self.db.query(Insight).filter(Insight.id == insight_id).first()

        if insight:
            insight.feedback = feedback
            insight.feedback_at = datetime.utcnow()
            self.db.commit()

        return insight

    def mark_as_read(self, insight_id: str) -> Optional[Insight]:
        """Mark an insight as read."""
        insight = self.db.query(Insight).filter(Insight.id == insight_id).first()

        if insight:
            insight.is_read = True
            insight.read_at = datetime.utcnow()
            self.db.commit()

        return insight

    def get_insight_history(
        self,
        user_id: str,
        limit: int = 30,
        offset: int = 0,
        insight_type: Optional[str] = None
    ) -> Dict:
        """Get historical insights with feedback stats."""
        query = self.db.query(Insight).filter(Insight.user_id == user_id)

        if insight_type:
            query = query.filter(Insight.type == insight_type)

        total = query.count()

        insights = query.order_by(
            Insight.generated_at.desc()
        ).offset(offset).limit(limit).all()

        # Get feedback stats
        helpful = self.db.query(func.count(Insight.id)).filter(
            and_(Insight.user_id == user_id, Insight.feedback == 'helpful')
        ).scalar()

        acted_on = self.db.query(func.count(Insight.id)).filter(
            and_(Insight.user_id == user_id, Insight.feedback == 'acted_on')
        ).scalar()

        dismissed = self.db.query(func.count(Insight.id)).filter(
            and_(Insight.user_id == user_id, Insight.feedback == 'dismissed')
        ).scalar()

        return {
            'insights': insights,
            'total': total,
            'helpful_count': helpful,
            'acted_on_count': acted_on,
            'dismissed_count': dismissed
        }
