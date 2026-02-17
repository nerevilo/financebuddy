"""
Institutions Router

API endpoints for managing connected financial institutions.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models import Institution, User

router = APIRouter(prefix="/institutions", tags=["institutions"])


# Response schemas
class AccountSummary(BaseModel):
    id: str
    name: str
    type: str
    subtype: Optional[str]
    last_four: Optional[str]
    current_balance: float
    available_balance: Optional[float]

    class Config:
        from_attributes = True


class InstitutionWithAccounts(BaseModel):
    id: str
    name: str
    status: str
    last_synced_at: Optional[datetime]
    accounts: List[AccountSummary]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[InstitutionWithAccounts])
async def get_institutions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all connected institutions with their accounts."""
    institutions = db.query(Institution).options(
        selectinload(Institution.accounts)
    ).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id
        )
    ).limit(50).all()

    result = []
    for inst in institutions:
        accounts = [
            AccountSummary(
                id=acc.id,
                name=acc.name,
                type=acc.type,
                subtype=acc.subtype,
                last_four=acc.last_four,
                current_balance=acc.current_balance or 0,
                available_balance=acc.available_balance
            )
            for acc in inst.accounts
        ]

        result.append(InstitutionWithAccounts(
            id=inst.id,
            name=inst.name,
            status=inst.status,
            last_synced_at=inst.last_synced_at,
            accounts=accounts
        ))

    return result


@router.get("/{institution_id}", response_model=InstitutionWithAccounts)
async def get_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific institution with its accounts."""
    institution = db.query(Institution).options(
        selectinload(Institution.accounts)
    ).filter(
        and_(
            Institution.id == institution_id,
            Institution.user_id == current_user.id
        )
    ).first()

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    accounts = [
        AccountSummary(
            id=acc.id,
            name=acc.name,
            type=acc.type,
            subtype=acc.subtype,
            last_four=acc.last_four,
            current_balance=acc.current_balance or 0,
            available_balance=acc.available_balance
        )
        for acc in institution.accounts
    ]

    return InstitutionWithAccounts(
        id=institution.id,
        name=institution.name,
        status=institution.status,
        last_synced_at=institution.last_synced_at,
        accounts=accounts
    )
