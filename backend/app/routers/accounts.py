"""
Accounts Router

API endpoints for managing connected accounts.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..models import Account, Institution
from ..schemas import AccountResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=List[AccountResponse])
async def get_accounts(db: Session = Depends(get_db)):
    """Get all connected accounts."""
    accounts = db.query(Account).join(Institution).filter(
        Institution.status == "active"
    ).all()

    result = []
    for acc in accounts:
        acc_dict = AccountResponse(
            id=acc.id,
            teller_account_id=acc.teller_account_id,
            name=acc.name,
            type=acc.type,
            subtype=acc.subtype,
            current_balance=acc.current_balance or 0,
            available_balance=acc.available_balance,
            currency=acc.currency,
            last_four=acc.last_four,
            institution_name=acc.institution.name if acc.institution else None
        )
        result.append(acc_dict)

    return result


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: str, db: Session = Depends(get_db)):
    """Get a specific account by ID."""
    account = db.query(Account).filter(Account.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return AccountResponse(
        id=account.id,
        teller_account_id=account.teller_account_id,
        name=account.name,
        type=account.type,
        subtype=account.subtype,
        current_balance=account.current_balance or 0,
        available_balance=account.available_balance,
        currency=account.currency,
        last_four=account.last_four,
        institution_name=account.institution.name if account.institution else None
    )


@router.get("/summary/balances")
async def get_balance_summary(db: Session = Depends(get_db)):
    """Get summary of all account balances."""
    accounts = db.query(Account).join(Institution).filter(
        Institution.status == "active"
    ).all()

    total_balance = 0
    total_available = 0
    total_credit_used = 0
    total_credit_limit = 0

    depository_balance = 0
    credit_balance = 0

    for acc in accounts:
        balance = acc.current_balance or 0

        if acc.type == "depository":
            depository_balance += balance
            total_balance += balance
            if acc.available_balance:
                total_available += acc.available_balance
        elif acc.type == "credit":
            # For credit cards, balance is usually negative (what you owe)
            credit_balance += abs(balance)
            total_credit_used += abs(balance)

    return {
        "total_balance": depository_balance - credit_balance,
        "depository_balance": depository_balance,
        "credit_balance": credit_balance,
        "total_available": total_available,
        "account_count": len(accounts)
    }
