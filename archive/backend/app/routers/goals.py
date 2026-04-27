"""
Goals API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models import User
from ..services.goal_service import GoalService
from ..services.income_service import IncomeService
from ..schemas import (
    GoalCreate, GoalUpdate, GoalResponse, GoalSuggestion
)

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.post("/", response_model=GoalResponse)
async def create_goal(
    goal: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new financial goal."""
    service = GoalService(db)
    created = service.create_goal(current_user.id, goal.model_dump())
    return service.get_goal_with_progress(created)


@router.get("/", response_model=List[GoalResponse])
async def get_goals(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all goals, optionally filtered by status."""
    service = GoalService(db)
    goals = service.get_user_goals(current_user.id, status)
    return [service.get_goal_with_progress(g) for g in goals]


@router.get("/suggestions", response_model=List[GoalSuggestion])
async def get_goal_suggestions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get auto-suggested goals based on spending patterns."""
    goal_service = GoalService(db)
    income_service = IncomeService(db)

    monthly_income = income_service.calculate_monthly_income(current_user.id)
    return goal_service.suggest_goals(current_user.id, monthly_income)


@router.get("/{goal_id}", response_model=GoalResponse)
async def get_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific goal."""
    service = GoalService(db)
    goal = service.get_goal(goal_id)

    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Goal not found")

    return service.get_goal_with_progress(goal)


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(
    goal_id: str,
    update: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a goal."""
    service = GoalService(db)
    goal = service.get_goal(goal_id)

    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal = service.update_goal(goal_id, update.model_dump(exclude_unset=True))
    return service.get_goal_with_progress(goal)


@router.post("/{goal_id}/progress", response_model=GoalResponse)
async def add_goal_progress(
    goal_id: str,
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add progress to a goal."""
    service = GoalService(db)
    goal = service.get_goal(goal_id)

    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal = service.add_progress(goal_id, amount)
    return service.get_goal_with_progress(goal)


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a goal."""
    service = GoalService(db)
    goal = service.get_goal(goal_id)

    if not goal or goal.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Goal not found")

    service.delete_goal(goal_id)
    return {"status": "deleted"}
