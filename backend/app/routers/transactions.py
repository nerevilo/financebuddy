"""
Transactions Router

API endpoints for managing and querying transactions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import date, timedelta

from ..core.database import get_db
from ..models import Transaction, Account, Institution
from ..schemas import TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=List[TransactionResponse])
async def get_transactions(
    account_id: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get transactions with optional filters.

    - account_id: Filter by specific account
    - category: Filter by category
    - start_date: Filter transactions from this date (inclusive)
    - end_date: Filter transactions until this date (inclusive)
    - limit: Maximum number of transactions to return
    - offset: Number of transactions to skip
    """
    query = db.query(Transaction).join(Account).join(Institution).filter(
        Institution.status == "active"
    )

    if account_id:
        query = query.filter(Transaction.account_id == account_id)

    if category:
        query = query.filter(Transaction.teller_category == category)

    if start_date:
        query = query.filter(Transaction.date >= start_date)

    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()

    return [
        TransactionResponse(
            id=tx.id,
            account_id=tx.account_id,
            date=tx.date,
            amount=tx.amount,
            description=tx.description,
            merchant_name=tx.merchant_name,
            category=tx.teller_category,
            type=tx.type,
            status=tx.status
        )
        for tx in transactions
    ]


@router.get("/recent")
async def get_recent_transactions(
    days: int = Query(default=30, le=365),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db)
):
    """Get recent transactions from the last N days."""
    start_date = date.today() - timedelta(days=days)

    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Transaction.date >= start_date
        )
    ).order_by(Transaction.date.desc()).limit(limit).all()

    return [
        {
            "id": tx.id,
            "date": tx.date.isoformat(),
            "amount": tx.amount,
            "description": tx.description,
            "merchant_name": tx.merchant_name,
            "category": tx.teller_category,
            "account_name": tx.account.name if tx.account else None
        }
        for tx in transactions
    ]


@router.get("/search")
async def search_transactions(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db)
):
    """Search transactions by description or merchant name."""
    search_term = f"%{q}%"

    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            (Transaction.description.ilike(search_term) | Transaction.merchant_name.ilike(search_term))
        )
    ).order_by(Transaction.date.desc()).limit(limit).all()

    return [
        {
            "id": tx.id,
            "date": tx.date.isoformat(),
            "amount": tx.amount,
            "description": tx.description,
            "merchant_name": tx.merchant_name,
            "category": tx.teller_category
        }
        for tx in transactions
    ]


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Get a specific transaction by ID."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionResponse(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date,
        amount=tx.amount,
        description=tx.description,
        merchant_name=tx.merchant_name,
        category=tx.teller_category,
        type=tx.type,
        status=tx.status
    )
