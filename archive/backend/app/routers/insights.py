"""
Insights API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime

from ..core.database import get_db
from ..core.auth import get_current_user
from ..services.insight_generation_service import InsightGenerationService
from ..models import Insight, User
from ..schemas import (
    InsightFeedbackUpdate, DailyInsightsResponse, InsightHistory
)

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/daily", response_model=DailyInsightsResponse)
async def get_daily_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get today's 3 insights (alert, opportunity, optimization).

    Generates new insights if none exist for today.
    """
    service = InsightGenerationService(db, user_id=current_user.id)
    insights = await service.generate_daily_insights(current_user.id)

    total_cost = sum(i.generation_cost or 0 for i in insights)
    source = insights[0].llm_source if insights else "unknown"

    return DailyInsightsResponse(
        date=date.today(),
        insights=insights,
        generation_source=source,
        total_cost=total_cost
    )


@router.get("/history", response_model=InsightHistory)
async def get_insight_history(
    limit: int = 30,
    offset: int = 0,
    insight_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get historical insights with feedback statistics."""
    service = InsightGenerationService(db, user_id=current_user.id)
    return service.get_insight_history(
        current_user.id,
        limit=limit,
        offset=offset,
        insight_type=insight_type
    )


@router.post("/{insight_id}/feedback")
async def update_insight_feedback(
    insight_id: str,
    feedback: InsightFeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update feedback on an insight (helpful, acted_on, dismissed)."""
    service = InsightGenerationService(db, user_id=current_user.id)

    # Check ownership
    insight = db.query(Insight).filter(Insight.id == insight_id).first()
    if not insight or insight.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Insight not found")

    insight = service.update_feedback(insight_id, feedback.feedback)
    return {"status": "updated", "feedback": insight.feedback}


@router.post("/{insight_id}/read")
async def mark_insight_read(
    insight_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark an insight as read."""
    service = InsightGenerationService(db, user_id=current_user.id)

    # Check ownership
    insight = db.query(Insight).filter(Insight.id == insight_id).first()
    if not insight or insight.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Insight not found")

    insight = service.mark_as_read(insight_id)
    return {"status": "read"}


@router.post("/regenerate", response_model=DailyInsightsResponse)
async def regenerate_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Force regeneration of daily insights (for testing/debugging)."""
    service = InsightGenerationService(db, user_id=current_user.id)

    # Delete today's insights first
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    db.query(Insight).filter(
        Insight.user_id == current_user.id,
        Insight.generated_at >= today_start
    ).delete()
    db.commit()

    # Generate fresh
    insights = await service.generate_daily_insights(current_user.id)

    return DailyInsightsResponse(
        date=date.today(),
        insights=insights,
        generation_source=insights[0].llm_source if insights else "unknown",
        total_cost=sum(i.generation_cost or 0 for i in insights)
    )
