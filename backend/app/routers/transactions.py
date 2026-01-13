"""
Transactions Router

API endpoints for managing and querying transactions.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc, asc
from typing import List, Optional, Literal
from datetime import date, datetime, timedelta

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.cache import get_cache, CacheService
from ..models import Transaction, Account, Institution, User
from ..schemas import TransactionResponse, TransactionCategoryUpdate, TransactionListResponse, CategoryResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=List[TransactionResponse])
async def get_transactions(
    account_id: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id
        )
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
            merchant_name=tx.enriched_merchant or tx.merchant_name,
            category=tx.enriched_category or tx.teller_category,
            type=tx.type,
            status=tx.status
        )
        for tx in transactions
    ]


@router.get("/recent")
async def get_recent_transactions(
    days: int = Query(default=30, le=365),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent transactions from the last N days."""
    start_date = date.today() - timedelta(days=days)

    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            Transaction.date >= start_date
        )
    ).order_by(Transaction.date.desc()).limit(limit).all()

    return [
        {
            "id": tx.id,
            "date": tx.date.isoformat(),
            "amount": tx.amount,
            "description": tx.description,
            "merchant_name": tx.enriched_merchant or tx.merchant_name,
            "category": tx.enriched_category or tx.teller_category,
            "account_name": tx.account.name if tx.account else None
        }
        for tx in transactions
    ]


@router.get("/search")
async def search_transactions(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search transactions by description or merchant name."""
    search_term = f"%{q}%"

    transactions = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id,
            (Transaction.description.ilike(search_term) | Transaction.merchant_name.ilike(search_term))
        )
    ).order_by(Transaction.date.desc()).limit(limit).all()

    return [
        {
            "id": tx.id,
            "date": tx.date.isoformat(),
            "amount": tx.amount,
            "description": tx.description,
            "merchant_name": tx.enriched_merchant or tx.merchant_name,
            "category": tx.enriched_category or tx.teller_category
        }
        for tx in transactions
    ]


@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all unique categories used in transactions.

    Returns categories sorted by usage count (most used first).
    """
    # Get unique categories with their counts
    categories = db.query(
        Transaction.enriched_category,
        func.count(Transaction.id).label('count')
    ).join(Account).join(Institution).filter(
        and_(
            Transaction.enriched_category.isnot(None),
            Institution.user_id == current_user.id
        )
    ).group_by(
        Transaction.enriched_category
    ).order_by(
        desc('count')
    ).all()

    return [
        CategoryResponse(
            name=cat.enriched_category,
            transaction_count=cat.count
        )
        for cat in categories
    ]


@router.get("/list", response_model=TransactionListResponse)
async def get_transactions_paginated(
    account_id: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Literal["date", "amount", "merchant", "category"] = "date",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get transactions with pagination, sorting, and total count.

    - sort_by: Field to sort by (date, amount, merchant, category)
    - sort_order: Sort direction (asc, desc)
    - Returns total count for pagination UI
    """
    base_query = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Institution.status == "active",
            Institution.user_id == current_user.id
        )
    )

    # Apply filters
    if account_id:
        base_query = base_query.filter(Transaction.account_id == account_id)
    if category:
        base_query = base_query.filter(Transaction.enriched_category == category)
    if start_date:
        base_query = base_query.filter(Transaction.date >= start_date)
    if end_date:
        base_query = base_query.filter(Transaction.date <= end_date)

    # Get total count before pagination
    total = base_query.count()

    # Apply sorting
    sort_column = {
        "date": Transaction.date,
        "amount": Transaction.amount,
        "merchant": Transaction.enriched_merchant,
        "category": Transaction.enriched_category
    }.get(sort_by, Transaction.date)

    order_func = desc if sort_order == "desc" else asc
    base_query = base_query.order_by(order_func(sort_column))

    # Apply pagination
    transactions = base_query.offset(offset).limit(limit).all()

    return TransactionListResponse(
        transactions=[
            TransactionResponse(
                id=tx.id,
                account_id=tx.account_id,
                date=tx.date,
                amount=tx.amount,
                description=tx.description,
                merchant_name=tx.enriched_merchant or tx.merchant_name,
                category=tx.enriched_category or tx.teller_category,
                type=tx.type,
                status=tx.status
            )
            for tx in transactions
        ],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific transaction by ID."""
    tx = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Transaction.id == transaction_id,
            Institution.user_id == current_user.id
        )
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionResponse(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date,
        amount=tx.amount,
        description=tx.description,
        merchant_name=tx.enriched_merchant or tx.merchant_name,
        category=tx.enriched_category or tx.teller_category,
        type=tx.type,
        status=tx.status
    )


@router.patch("/{transaction_id}/category", response_model=TransactionResponse)
async def update_transaction_category(
    transaction_id: str,
    update: TransactionCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
):
    """
    Update the category for a specific transaction.

    This is a user override - sets categorization_source to 'user'.
    """
    tx = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Transaction.id == transaction_id,
            Institution.user_id == current_user.id
        )
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update category with user override
    tx.enriched_category = update.category
    tx.categorization_source = "user"
    tx.categorization_confidence = 1.0
    tx.enriched_at = datetime.utcnow()

    db.commit()
    db.refresh(tx)

    # Invalidate dashboard cache for this user
    await cache.invalidate_user_dashboard(current_user.id)

    return TransactionResponse(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date,
        amount=tx.amount,
        description=tx.description,
        merchant_name=tx.enriched_merchant or tx.merchant_name,
        category=tx.enriched_category or tx.teller_category,
        type=tx.type,
        status=tx.status
    )
