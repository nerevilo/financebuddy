"""
Teller Connect Router

Handles enrollment callbacks from Teller Connect frontend widget.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..core.database import get_db
from ..models import Institution, Account, Transaction, User
from ..services.teller import TellerService
from ..schemas import TellerConnectPayload

router = APIRouter(prefix="/teller", tags=["teller"])


@router.post("/connect")
async def handle_teller_connect(
    payload: TellerConnectPayload,
    db: Session = Depends(get_db)
):
    """
    Handle the callback from Teller Connect.

    This endpoint receives the access token and enrollment info
    after a user successfully connects their bank account.
    """
    access_token = payload.accessToken
    enrollment = payload.enrollment

    # For MVP, create a default user if none exists
    user = db.query(User).first()
    if not user:
        user = User(email="demo@example.com", name="Demo User")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Check if enrollment already exists
    existing = db.query(Institution).filter(
        Institution.teller_enrollment_id == enrollment.get("id")
    ).first()

    if existing:
        # Update access token
        existing.teller_access_token = access_token
        existing.status = "active"
        existing.last_synced_at = datetime.utcnow()
        db.commit()
        institution = existing
    else:
        # Create new institution
        institution = Institution(
            user_id=user.id,
            teller_enrollment_id=enrollment.get("id"),
            teller_access_token=access_token,
            name=enrollment.get("institution", {}).get("name", "Unknown Bank"),
            status="active",
            last_synced_at=datetime.utcnow()
        )
        db.add(institution)
        db.commit()
        db.refresh(institution)

    # Sync accounts from Teller
    try:
        teller = TellerService(access_token=access_token)
        accounts_data = teller.get_accounts()

        for acc_data in accounts_data:
            existing_account = db.query(Account).filter(
                Account.teller_account_id == acc_data["id"]
            ).first()

            if existing_account:
                # Update existing account
                existing_account.name = acc_data.get("name", "Account")
                existing_account.type = acc_data.get("type", "depository")
                existing_account.subtype = acc_data.get("subtype")
                existing_account.last_synced_at = datetime.utcnow()
            else:
                # Create new account
                account = Account(
                    institution_id=institution.id,
                    teller_account_id=acc_data["id"],
                    name=acc_data.get("name", "Account"),
                    type=acc_data.get("type", "depository"),
                    subtype=acc_data.get("subtype"),
                    currency=acc_data.get("currency", "USD"),
                    last_four=acc_data.get("last_four"),
                    last_synced_at=datetime.utcnow()
                )
                db.add(account)

        db.commit()

    except Exception as e:
        # Log error but don't fail - accounts can be synced later
        print(f"Error syncing accounts: {e}")

    return {
        "success": True,
        "institution_id": institution.id,
        "message": f"Connected to {institution.name}"
    }


@router.post("/sync/{institution_id}")
async def sync_institution(
    institution_id: str,
    db: Session = Depends(get_db)
):
    """Sync accounts and transactions for an institution."""
    institution = db.query(Institution).filter(
        Institution.id == institution_id
    ).first()

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    teller = TellerService(access_token=institution.teller_access_token)

    # Sync accounts
    accounts_data = teller.get_accounts()
    synced_accounts = 0
    synced_transactions = 0

    for acc_data in accounts_data:
        # Find or create account
        account = db.query(Account).filter(
            Account.teller_account_id == acc_data["id"]
        ).first()

        if not account:
            account = Account(
                institution_id=institution.id,
                teller_account_id=acc_data["id"],
                name=acc_data.get("name", "Account"),
                type=acc_data.get("type", "depository"),
                subtype=acc_data.get("subtype"),
                currency=acc_data.get("currency", "USD"),
                last_four=acc_data.get("last_four")
            )
            db.add(account)
            db.commit()
            db.refresh(account)

        # Get balances
        try:
            balances = teller.get_account_balances(acc_data["id"])
            account.current_balance = float(balances.get("ledger", 0))
            account.available_balance = float(balances.get("available", 0)) if balances.get("available") else None
        except Exception as e:
            print(f"Error getting balances for {acc_data['id']}: {e}")

        # Get transactions
        try:
            transactions_data = teller.get_transactions(acc_data["id"])

            for tx_data in transactions_data:
                existing_tx = db.query(Transaction).filter(
                    Transaction.teller_transaction_id == tx_data["id"]
                ).first()

                if not existing_tx:
                    # Parse amount (Teller returns as string)
                    amount = float(tx_data.get("amount", 0))

                    # Safely get details and counterparty
                    details = tx_data.get("details") or {}
                    counterparty = details.get("counterparty") or {}

                    # Parse date string to date object
                    date_str = tx_data.get("date")
                    from datetime import date as date_type
                    tx_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date_type.today()

                    tx = Transaction(
                        account_id=account.id,
                        teller_transaction_id=tx_data["id"],
                        date=tx_date,
                        amount=amount,
                        description=tx_data.get("description", ""),
                        merchant_name=counterparty.get("name") if counterparty else None,
                        teller_category=details.get("category") if details else None,
                        type=tx_data.get("type"),
                        status=tx_data.get("status", "posted")
                    )
                    db.add(tx)
                    synced_transactions += 1

        except Exception as e:
            print(f"Error syncing transactions for {acc_data['id']}: {e}")

        account.last_synced_at = datetime.now(timezone.utc)
        synced_accounts += 1

    institution.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": True,
        "synced_accounts": synced_accounts,
        "synced_transactions": synced_transactions
    }


@router.delete("/disconnect/{institution_id}")
async def disconnect_institution(
    institution_id: str,
    db: Session = Depends(get_db)
):
    """Disconnect an institution."""
    institution = db.query(Institution).filter(
        Institution.id == institution_id
    ).first()

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Try to delete enrollment from Teller
    try:
        teller = TellerService(access_token=institution.teller_access_token)
        teller.delete_enrollment()
    except Exception as e:
        print(f"Error deleting Teller enrollment: {e}")

    # Mark as disconnected (keep data for historical reference)
    institution.status = "disconnected"
    db.commit()

    return {"success": True, "message": "Institution disconnected"}
