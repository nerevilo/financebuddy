"""
Anomaly Detection API Router

Endpoints for detecting unusual transactions and managing one-time expenses.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models import User, Transaction
from ..services.anomaly_detection_service import AnomalyDetectionService
from ..schemas.schemas import (
    AnomalyResponse,
    UnusualTransactionsResponse,
    MarkOneTimeRequest,
    OneTimeExpenseResponse,
    OneTimeExpensesListResponse,
    AnomalySummary
)

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


def _format_anomaly(anomaly_dict: dict) -> AnomalyResponse:
    """Format anomaly detection result for API response."""
    return AnomalyResponse(
        id=anomaly_dict['transaction_id'],
        amount=anomaly_dict['amount'],
        merchant=anomaly_dict['merchant'],
        category=anomaly_dict['category'],
        date=anomaly_dict['date'],
        anomaly_score=anomaly_dict['anomaly_score'],
        anomaly_reason=anomaly_dict['anomaly_reason'],
        description=anomaly_dict['description'],
        is_one_time=anomaly_dict['transaction'].is_one_time or False,
        user_reviewed=anomaly_dict['transaction'].user_reviewed or False
    )


def _format_transaction_anomaly(txn: Transaction) -> AnomalyResponse:
    """Format a Transaction object as AnomalyResponse."""
    merchant = txn.enriched_merchant or txn.merchant_name
    category = txn.enriched_category or txn.teller_category

    return AnomalyResponse(
        id=txn.id,
        amount=abs(txn.amount),
        merchant=merchant,
        category=category,
        date=txn.date,
        anomaly_score=txn.anomaly_score or 0.0,
        anomaly_reason=txn.anomaly_reason or 'unknown',
        description=f"${abs(txn.amount):,.2f} at {merchant or 'Unknown'}",
        is_one_time=txn.is_one_time or False,
        user_reviewed=txn.user_reviewed or False
    )


@router.get("/unusual", response_model=UnusualTransactionsResponse)
async def get_unusual_transactions(
    limit: int = 10,
    include_reviewed: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get unusual transactions for review.

    Returns detected anomalies that may be one-time expenses.
    By default, only returns unreviewed transactions.
    """
    service = AnomalyDetectionService(db, current_user.id)

    if include_reviewed:
        # Run fresh detection
        anomalies = service.detect_anomalies_for_user()[:limit]
        transactions = [_format_anomaly(a) for a in anomalies]
    else:
        # Get unreviewed from DB
        unreviewed = service.get_unreviewed_anomalies(limit)
        if unreviewed:
            transactions = [_format_transaction_anomaly(t) for t in unreviewed]
        else:
            # No saved anomalies, run detection
            anomalies = service.detect_anomalies_for_user()[:limit]
            transactions = [_format_anomaly(a) for a in anomalies]

    total_unreviewed = len(service.get_unreviewed_anomalies(100))

    return UnusualTransactionsResponse(
        transactions=transactions,
        total_unreviewed=total_unreviewed,
        last_scan=datetime.utcnow().isoformat()
    )


@router.post("/detect")
async def run_anomaly_detection(
    use_llm: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger anomaly detection scan.

    Two-stage process:
    1. Statistical detection (fast, free)
    2. LLM verification (Gemini) - filters false positives

    Set use_llm=false to skip LLM verification.
    """
    service = AnomalyDetectionService(db, current_user.id)

    # Stage 1: Statistical detection
    anomalies = service.detect_anomalies_for_user()

    # Stage 2: LLM verification (if enabled)
    if use_llm and anomalies:
        anomalies = await service.verify_with_llm(anomalies)

    # Save verified anomalies
    count = 0
    for anomaly in anomalies:
        txn = anomaly['transaction']
        if not txn.is_anomaly and not txn.user_reviewed:
            txn.is_anomaly = True
            txn.anomaly_score = anomaly['anomaly_score']
            txn.anomaly_reason = anomaly.get('llm_reason') or anomaly['anomaly_reason']
            count += 1

    db.commit()

    return {
        "message": "Detection complete",
        "new_anomalies_found": count,
        "llm_verified": use_llm
    }


@router.post("/{transaction_id}/mark-one-time")
async def mark_as_one_time(
    transaction_id: str,
    request: MarkOneTimeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a transaction as a one-time expense.

    One-time expenses are excluded from budget baseline calculations.
    """
    service = AnomalyDetectionService(db, current_user.id)

    txn = service.mark_as_one_time(
        transaction_id,
        reason=request.reason,
        exclude_from_budget=request.exclude_from_budget
    )

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "message": "Marked as one-time expense",
        "transaction_id": transaction_id,
        "exclude_from_budget": request.exclude_from_budget
    }


@router.post("/{transaction_id}/mark-normal")
async def mark_as_normal(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a transaction as normal (not anomalous).

    User feedback to improve future detection.
    """
    service = AnomalyDetectionService(db, current_user.id)

    txn = service.mark_as_normal(transaction_id)

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "message": "Marked as normal",
        "transaction_id": transaction_id
    }


@router.get("/one-time-expenses", response_model=OneTimeExpensesListResponse)
async def get_one_time_expenses(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all transactions marked as one-time expenses."""
    service = AnomalyDetectionService(db, current_user.id)

    expenses = service.get_one_time_expenses(
        start_date=datetime.fromisoformat(start_date) if start_date else None,
        end_date=datetime.fromisoformat(end_date) if end_date else None
    )

    expense_responses = [
        OneTimeExpenseResponse(
            id=t.id,
            amount=abs(t.amount),
            merchant=t.enriched_merchant or t.merchant_name,
            category=t.enriched_category or t.teller_category,
            date=t.date,
            one_time_reason=t.one_time_reason,
            exclude_from_budget=t.exclude_from_budget or False
        )
        for t in expenses
    ]

    return OneTimeExpensesListResponse(
        expenses=expense_responses,
        total=len(expenses),
        total_amount=sum(abs(t.amount) for t in expenses)
    )


@router.get("/summary", response_model=AnomalySummary)
async def get_anomaly_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary statistics about anomalies and one-time expenses.

    Useful for dashboard widgets.
    """
    service = AnomalyDetectionService(db, current_user.id)
    summary = service.get_anomaly_summary()

    top_unreviewed = [
        _format_transaction_anomaly(t)
        for t in summary['top_unreviewed']
    ]

    return AnomalySummary(
        unreviewed_count=summary['unreviewed_count'],
        one_time_count=summary['one_time_count'],
        one_time_total=summary['one_time_total'],
        top_unreviewed=top_unreviewed
    )
