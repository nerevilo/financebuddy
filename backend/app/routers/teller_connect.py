"""
Teller Connect Router

Handles enrollment callbacks from Teller Connect frontend widget.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..core.database import get_db, SessionLocal
from ..core.auth import get_current_user
from ..core.encryption import encrypt_value, decrypt_value
from ..core.logging_config import get_logger
from ..models import Institution, Account, Transaction, User
from ..services.teller import TellerService
from ..services.budget_enrichment import BudgetEnrichmentService
from ..schemas import TellerConnectPayload

logger = get_logger(__name__)

router = APIRouter(prefix="/teller", tags=["teller"])


async def enrich_new_transactions_task(user_id: str, transaction_ids: list):
    """Background task to enrich new transactions."""
    if not transaction_ids:
        return

    db = SessionLocal()
    try:
        service = BudgetEnrichmentService(db)
        result = await service.enrich_new_transactions(user_id, transaction_ids)
        logger.info("Auto-enrichment complete", extra={"result": result, "user_id": user_id})
    except Exception as e:
        logger.error("Auto-enrichment error", extra={"error": str(e), "user_id": user_id})
    finally:
        db.close()


@router.post("/connect")
async def handle_teller_connect(
    payload: TellerConnectPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Handle the callback from Teller Connect.

    This endpoint receives the access token and enrollment info
    after a user successfully connects their bank account.
    Requires authentication - connects bank to the logged-in user.
    """
    access_token = payload.accessToken
    enrollment = payload.enrollment

    # Use the authenticated user
    user = current_user

    # Check if enrollment already exists
    existing = db.query(Institution).filter(
        Institution.teller_enrollment_id == enrollment.get("id")
    ).first()

    if existing:
        # Update access token (encrypted at rest)
        existing.teller_access_token = encrypt_value(access_token)
        existing.status = "active"
        existing.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        institution = existing
    else:
        # Create new institution
        institution = Institution(
            user_id=user.id,
            teller_enrollment_id=enrollment.get("id"),
            teller_access_token=encrypt_value(access_token),
            name=enrollment.get("institution", {}).get("name", "Unknown Bank"),
            status="active",
            last_synced_at=datetime.now(timezone.utc)
        )
        db.add(institution)
        db.commit()
        db.refresh(institution)

    # Sync accounts from Teller
    try:
        teller = TellerService(access_token=access_token)
        accounts_data = await teller.get_accounts()

        for acc_data in accounts_data:
            existing_account = db.query(Account).filter(
                Account.teller_account_id == acc_data["id"]
            ).first()

            if existing_account:
                # Update existing account
                existing_account.name = acc_data.get("name", "Account")
                existing_account.type = acc_data.get("type", "depository")
                existing_account.subtype = acc_data.get("subtype")
                existing_account.last_synced_at = datetime.now(timezone.utc)
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
                    last_synced_at=datetime.now(timezone.utc)
                )
                db.add(account)

        db.commit()

    except Exception as e:
        # Log error but don't fail - accounts can be synced later
        logger.error("Error syncing accounts", extra={"error": str(e), "institution_id": institution.id})

    return {
        "success": True,
        "institution_id": institution.id,
        "message": f"Connected to {institution.name}"
    }


@router.post("/sync/{institution_id}")
async def sync_institution(
    institution_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync accounts and transactions for an institution."""
    institution = db.query(Institution).filter(
        Institution.id == institution_id,
        Institution.user_id == current_user.id
    ).first()

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    teller = TellerService(access_token=decrypt_value(institution.teller_access_token))

    # Sync accounts
    accounts_data = await teller.get_accounts()
    synced_accounts = 0
    synced_transactions = 0
    new_transaction_ids = []  # Track new transactions for enrichment

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
            db.flush()
            db.refresh(account)

        # Get balances
        try:
            balances = await teller.get_account_balances(acc_data["id"])
            account.current_balance = float(balances.get("ledger", 0))
            account.available_balance = float(balances.get("available", 0)) if balances.get("available") else None
        except Exception as e:
            logger.error("Error getting balances", extra={"error": str(e), "account_id": acc_data['id']})

        # Get transactions
        try:
            transactions_data = await teller.get_transactions(acc_data["id"])

            # Get existing transaction IDs for this account (for deduplication)
            existing_teller_ids = set(
                tx_id for (tx_id,) in db.query(Transaction.teller_transaction_id).filter(
                    Transaction.teller_transaction_id.in_([tx["id"] for tx in transactions_data])
                ).all()
            )

            # BULK INSERT: Collect all new transactions first
            new_transactions = []
            from datetime import date as date_type

            for tx_data in transactions_data:
                if tx_data["id"] not in existing_teller_ids:
                    # Parse amount (Teller returns as string)
                    amount = float(tx_data.get("amount", 0))

                    # Safely get details and counterparty
                    details = tx_data.get("details") or {}
                    counterparty = details.get("counterparty") or {}

                    # Parse date string to date object
                    date_str = tx_data.get("date")
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
                    new_transactions.append(tx)

            # Bulk insert all new transactions at once (much faster!)
            if new_transactions:
                db.bulk_save_objects(new_transactions, return_defaults=True)
                db.flush()  # Single flush for all transactions
                new_transaction_ids.extend([tx.id for tx in new_transactions])
                synced_transactions += len(new_transactions)

                logger.info("Bulk inserted transactions", extra={
                    "count": len(new_transactions),
                    "account_id": acc_data['id']
                })

        except Exception as e:
            logger.error("Error syncing transactions", extra={"error": str(e), "account_id": acc_data['id']})

        account.last_synced_at = datetime.now(timezone.utc)
        synced_accounts += 1

    institution.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    # Trigger auto-enrichment for new transactions in background
    if new_transaction_ids:
        background_tasks.add_task(
            enrich_new_transactions_task,
            current_user.id,
            new_transaction_ids
        )

    return {
        "success": True,
        "synced_accounts": synced_accounts,
        "synced_transactions": synced_transactions,
        "enrichment_queued": len(new_transaction_ids)
    }


@router.delete("/disconnect/{institution_id}")
async def disconnect_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Disconnect an institution."""
    institution = db.query(Institution).filter(
        Institution.id == institution_id,
        Institution.user_id == current_user.id
    ).first()

    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")

    # Try to delete enrollment from Teller
    try:
        teller = TellerService(access_token=decrypt_value(institution.teller_access_token))
        await teller.delete_enrollment()
    except Exception as e:
        logger.error("Error deleting Teller enrollment", extra={"error": str(e), "institution_id": institution_id})

    # Mark as disconnected (keep data for historical reference)
    institution.status = "disconnected"
    db.commit()

    return {"success": True, "message": "Institution disconnected"}
