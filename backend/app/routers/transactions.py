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
from ..models import Transaction, Account, Institution, User, TransactionTag, TransactionTagAssociation
from ..schemas import (
    TransactionResponse, TransactionCategoryUpdate, TransactionListResponse, CategoryResponse,
    TransactionDetailResponse, TransactionUpdateRequest, TransactionListWithAnomaliesResponse, TagResponse
)

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


@router.get("/list", response_model=TransactionListWithAnomaliesResponse)
async def get_transactions_paginated(
    account_id: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Literal["date", "amount", "merchant", "category"] = "date",
    sort_order: Literal["asc", "desc"] = "desc",
    show_unusual_only: bool = False,
    tag_ids: Optional[str] = Query(None, description="Comma-separated tag IDs"),
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get transactions with pagination, sorting, anomaly info, and total count.

    - sort_by: Field to sort by (date, amount, merchant, category)
    - sort_order: Sort direction (asc, desc)
    - show_unusual_only: Filter to show only unusual transactions
    - tag_ids: Comma-separated list of tag IDs to filter by
    - Returns total count and anomaly count for UI
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

    # Filter by unusual only
    if show_unusual_only:
        base_query = base_query.filter(
            and_(Transaction.is_anomaly == True, Transaction.user_reviewed == False)
        )

    # Filter by tags (transactions that have any of the specified tags)
    if tag_ids:
        tag_id_list = [tid.strip() for tid in tag_ids.split(",") if tid.strip()]
        if tag_id_list:
            base_query = base_query.join(TransactionTagAssociation).filter(
                TransactionTagAssociation.tag_id.in_(tag_id_list)
            ).distinct()

    # Get total count and anomaly count before pagination
    total = base_query.count()
    anomaly_count = base_query.filter(
        and_(Transaction.is_anomaly == True, Transaction.user_reviewed == False)
    ).count() if not show_unusual_only else total

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

    return TransactionListWithAnomaliesResponse(
        transactions=[
            TransactionDetailResponse(
                id=tx.id,
                account_id=tx.account_id,
                date=tx.date,
                amount=tx.amount,
                description=tx.description,
                merchant_name=tx.enriched_merchant or tx.merchant_name,
                category=tx.enriched_category or tx.teller_category,
                type=tx.type,
                status=tx.status,
                is_anomaly=tx.is_anomaly or False,
                anomaly_score=tx.anomaly_score,
                anomaly_reason=tx.anomaly_reason,
                is_one_time=tx.is_one_time or False,
                user_reviewed=tx.user_reviewed or False,
                tags=[
                    TagResponse(
                        id=tag.id,
                        name=tag.name,
                        color=tag.color,
                        tag_type=tag.tag_type
                    ) for tag in tx.tags
                ]
            )
            for tx in transactions
        ],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
        anomaly_count=anomaly_count
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


@router.get("/{transaction_id}/detail", response_model=TransactionDetailResponse)
async def get_transaction_detail(
    transaction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full transaction details including tags and anomaly info.
    """
    tx = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Transaction.id == transaction_id,
            Institution.user_id == current_user.id
        )
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return TransactionDetailResponse(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date,
        amount=tx.amount,
        description=tx.description,
        merchant_name=tx.enriched_merchant or tx.merchant_name,
        category=tx.enriched_category or tx.teller_category,
        type=tx.type,
        status=tx.status,
        is_anomaly=tx.is_anomaly or False,
        anomaly_score=tx.anomaly_score,
        anomaly_reason=tx.anomaly_reason,
        is_one_time=tx.is_one_time or False,
        user_reviewed=tx.user_reviewed or False,
        tags=[
            TagResponse(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                tag_type=tag.tag_type
            ) for tag in tx.tags
        ]
    )


@router.patch("/{transaction_id}", response_model=TransactionDetailResponse)
async def update_transaction(
    transaction_id: str,
    update: TransactionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: CacheService = Depends(get_cache)
):
    """
    Update a transaction's merchant name, category, and/or tags.
    """
    tx = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Transaction.id == transaction_id,
            Institution.user_id == current_user.id
        )
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update merchant name if provided
    if update.merchant_name is not None:
        tx.enriched_merchant = update.merchant_name
        tx.enriched_at = datetime.utcnow()

    # Update category if provided
    if update.category is not None:
        tx.enriched_category = update.category
        tx.categorization_source = "user"
        tx.categorization_confidence = 1.0
        tx.enriched_at = datetime.utcnow()

    # Update tags if provided
    if update.tag_ids is not None:
        # Verify all tags belong to the user
        tags = db.query(TransactionTag).filter(
            and_(
                TransactionTag.id.in_(update.tag_ids),
                TransactionTag.user_id == current_user.id
            )
        ).all()

        if len(tags) != len(update.tag_ids):
            raise HTTPException(status_code=400, detail="One or more invalid tag IDs")

        # Replace all tags
        tx.tags = tags

    db.commit()
    db.refresh(tx)

    # Invalidate dashboard cache
    await cache.invalidate_user_dashboard(current_user.id)

    return TransactionDetailResponse(
        id=tx.id,
        account_id=tx.account_id,
        date=tx.date,
        amount=tx.amount,
        description=tx.description,
        merchant_name=tx.enriched_merchant or tx.merchant_name,
        category=tx.enriched_category or tx.teller_category,
        type=tx.type,
        status=tx.status,
        is_anomaly=tx.is_anomaly or False,
        anomaly_score=tx.anomaly_score,
        anomaly_reason=tx.anomaly_reason,
        is_one_time=tx.is_one_time or False,
        user_reviewed=tx.user_reviewed or False,
        tags=[
            TagResponse(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                tag_type=tag.tag_type
            ) for tag in tx.tags
        ]
    )


@router.post("/{transaction_id}/tags/{tag_id}")
async def add_tag_to_transaction(
    transaction_id: str,
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a tag to a transaction.
    """
    # Verify transaction belongs to user
    tx = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Transaction.id == transaction_id,
            Institution.user_id == current_user.id
        )
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify tag belongs to user
    tag = db.query(TransactionTag).filter(
        and_(
            TransactionTag.id == tag_id,
            TransactionTag.user_id == current_user.id
        )
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Check if already associated
    if tag in tx.tags:
        return {"message": "Tag already added to transaction"}

    tx.tags.append(tag)
    db.commit()

    return {"message": "Tag added successfully"}


@router.delete("/{transaction_id}/tags/{tag_id}")
async def remove_tag_from_transaction(
    transaction_id: str,
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a tag from a transaction.
    """
    # Verify transaction belongs to user
    tx = db.query(Transaction).join(Account).join(Institution).filter(
        and_(
            Transaction.id == transaction_id,
            Institution.user_id == current_user.id
        )
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify tag belongs to user
    tag = db.query(TransactionTag).filter(
        and_(
            TransactionTag.id == tag_id,
            TransactionTag.user_id == current_user.id
        )
    ).first()

    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Remove if present
    if tag in tx.tags:
        tx.tags.remove(tag)
        db.commit()
        return {"message": "Tag removed successfully"}

    return {"message": "Tag was not on transaction"}
