"""
Tags Router

API endpoints for managing transaction tags.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models import TransactionTag, User
from ..schemas import TagCreate, TagResponse, TagsListResponse

router = APIRouter(prefix="/tags", tags=["tags"])

# Predefined tags to seed for new users
PREDEFINED_TAGS = [
    {"name": "rent", "color": "#3B82F6"},  # Blue
    {"name": "subscription", "color": "#8B5CF6"},  # Purple
    {"name": "one-time", "color": "#F59E0B"},  # Amber
    {"name": "ignore", "color": "#6B7280"},  # Gray
    {"name": "recurring", "color": "#10B981"},  # Green
    {"name": "refund", "color": "#22C55E"},  # Light green
]


def ensure_predefined_tags(db: Session, user_id: str) -> None:
    """Create predefined tags for user if they don't exist."""
    for tag_data in PREDEFINED_TAGS:
        existing = db.query(TransactionTag).filter(
            and_(
                TransactionTag.user_id == user_id,
                TransactionTag.name == tag_data["name"]
            )
        ).first()

        if not existing:
            tag = TransactionTag(
                user_id=user_id,
                name=tag_data["name"],
                color=tag_data["color"],
                tag_type="predefined"
            )
            db.add(tag)

    db.commit()


@router.get("/", response_model=TagsListResponse)
async def get_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all tags (predefined + custom) for the current user.

    Automatically creates predefined tags if they don't exist.
    """
    # Ensure predefined tags exist
    ensure_predefined_tags(db, current_user.id)

    # Get all tags for user
    tags = db.query(TransactionTag).filter(
        TransactionTag.user_id == current_user.id
    ).order_by(TransactionTag.tag_type, TransactionTag.name).all()

    predefined = [
        TagResponse(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            tag_type=tag.tag_type
        )
        for tag in tags if tag.tag_type == "predefined"
    ]

    custom = [
        TagResponse(
            id=tag.id,
            name=tag.name,
            color=tag.color,
            tag_type=tag.tag_type
        )
        for tag in tags if tag.tag_type == "custom"
    ]

    return TagsListResponse(predefined=predefined, custom=custom)


@router.post("/", response_model=TagResponse)
async def create_tag(
    tag: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new custom tag.

    - name: Tag name (must be unique for user)
    - color: Optional hex color (e.g., "#FF5733")
    """
    # Check for duplicate name
    existing = db.query(TransactionTag).filter(
        and_(
            TransactionTag.user_id == current_user.id,
            TransactionTag.name == tag.name.lower().strip()
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Tag '{tag.name}' already exists"
        )

    new_tag = TransactionTag(
        user_id=current_user.id,
        name=tag.name.lower().strip(),
        color=tag.color,
        tag_type="custom"
    )

    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)

    return TagResponse(
        id=new_tag.id,
        name=new_tag.name,
        color=new_tag.color,
        tag_type=new_tag.tag_type
    )


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a custom tag.

    Predefined tags cannot be deleted.
    """
    tag = db.query(TransactionTag).filter(
        and_(
            TransactionTag.id == tag_id,
            TransactionTag.user_id == current_user.id
        )
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    if tag.tag_type == "predefined":
        raise HTTPException(
            status_code=400,
            detail="Predefined tags cannot be deleted"
        )

    db.delete(tag)
    db.commit()

    return {"message": "Tag deleted successfully"}
