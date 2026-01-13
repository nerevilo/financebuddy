"""
Income API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models import User
from ..services.income_service import IncomeService
from ..schemas import (
    IncomeSourceCreate, IncomeSourceUpdate, IncomeSourceResponse,
    IncomeSummary, DetectedIncome
)

router = APIRouter(prefix="/api/income", tags=["income"])


@router.get("/", response_model=IncomeSummary)
async def get_income_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get income summary with all sources."""
    service = IncomeService(db)
    sources = service.get_income_sources(current_user.id)
    monthly_total = service.calculate_monthly_income(current_user.id)

    return IncomeSummary(
        total_monthly_income=monthly_total,
        income_sources=sources,
        auto_detected_count=len([s for s in sources if s.auto_detected]),
        manual_count=len([s for s in sources if not s.auto_detected])
    )


@router.post("/detect", response_model=List[DetectedIncome])
async def detect_income_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-detect income sources from transaction patterns."""
    service = IncomeService(db)
    detected = service.detect_income_sources(current_user.id)

    return [
        DetectedIncome(
            name=d['name'],
            amount=d['amount'],
            frequency=d['frequency'],
            occurrences=d['occurrences'],
            pattern=d['pattern'],
            last_date=d['last_date'],
            confidence=d['confidence'],
            last_transaction_id=d.get('last_transaction_id')
        )
        for d in detected
    ]


@router.post("/detect/{index}/save", response_model=IncomeSourceResponse)
async def save_detected_income(
    index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save a detected income source."""
    service = IncomeService(db)
    detected = service.detect_income_sources(current_user.id)

    if index >= len(detected):
        raise HTTPException(status_code=404, detail="Detection index out of range")

    return service.save_detected_income(current_user.id, detected[index])


@router.post("/", response_model=IncomeSourceResponse)
async def create_income_source(
    source: IncomeSourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a manual income source."""
    service = IncomeService(db)
    return service.create_income_source(current_user.id, source.model_dump())


@router.patch("/{source_id}", response_model=IncomeSourceResponse)
async def update_income_source(
    source_id: str,
    update: IncomeSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an income source."""
    service = IncomeService(db)
    source = service.get_income_source(source_id)

    if not source or source.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Income source not found")

    source = service.update_income_source(source_id, update.model_dump(exclude_unset=True))
    return source


@router.delete("/{source_id}")
async def delete_income_source(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an income source."""
    service = IncomeService(db)
    source = service.get_income_source(source_id)

    if not source or source.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Income source not found")

    service.delete_income_source(source_id)
    return {"status": "deleted"}
