"""
User Profile API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models import UserProfile, User
from ..models.models import generate_uuid
from ..schemas import UserProfileCreate, UserProfileUpdate, UserProfileResponse

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/", response_model=UserProfileResponse)
async def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user profile."""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        # Create default profile
        profile = UserProfile(
            id=generate_uuid(),
            user_id=current_user.id,
            household_size=1,
            insight_frequency="daily"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    # Parse preferred_categories from JSON
    preferred_categories = None
    if profile.preferred_categories:
        try:
            preferred_categories = json.loads(profile.preferred_categories)
        except:
            pass

    return UserProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        monthly_income_estimate=profile.monthly_income_estimate,
        income_last_calculated=profile.income_last_calculated,
        household_size=profile.household_size or 1,
        location_city=profile.location_city,
        location_state=profile.location_state,
        context_notes=profile.context_notes,
        insight_frequency=profile.insight_frequency or "daily",
        preferred_categories=preferred_categories,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


@router.patch("/", response_model=UserProfileResponse)
async def update_profile(
    update: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user profile."""
    profile = db.query(UserProfile).filter(
        UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = UserProfile(
            id=generate_uuid(),
            user_id=current_user.id,
            household_size=1,
            insight_frequency="daily"
        )
        db.add(profile)

    update_data = update.model_dump(exclude_unset=True)

    # Handle preferred_categories as JSON
    if 'preferred_categories' in update_data and update_data['preferred_categories'] is not None:
        update_data['preferred_categories'] = json.dumps(update_data['preferred_categories'])

    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)

    # Parse preferred_categories from JSON for response
    preferred_categories = None
    if profile.preferred_categories:
        try:
            preferred_categories = json.loads(profile.preferred_categories)
        except:
            pass

    return UserProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        monthly_income_estimate=profile.monthly_income_estimate,
        income_last_calculated=profile.income_last_calculated,
        household_size=profile.household_size or 1,
        location_city=profile.location_city,
        location_state=profile.location_state,
        context_notes=profile.context_notes,
        insight_frequency=profile.insight_frequency or "daily",
        preferred_categories=preferred_categories,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )
