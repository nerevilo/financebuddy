"""
Categorization Router

Endpoints for transaction enrichment, categorization, and ML-based merchant recognition.
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List, Optional

from ..core.database import get_db
from ..services.categorization import TransferDetector
from ..services.ntropy_client import NtropyClient
from ..services.cascade_enrichment import CascadeEnrichment
from ..models.models import Transaction, Account, Institution
from pydantic import BaseModel


router = APIRouter(prefix="/categorization", tags=["categorization"])


# Response models
class EnrichmentStatus(BaseModel):
    message: str
    total_transactions: int
    enriched: int
    pending: int


class CategoryStats(BaseModel):
    total_transactions: int
    enriched: int
    transfers: int
    coverage_percent: float
    by_source: dict


class NtropyStatus(BaseModel):
    enabled: bool
    connected: bool
    message: str


# Background task for enrichment
async def enrich_transactions_task(db: Session):
    """Background task to enrich transactions using Ntropy"""
    transfer_detector = TransferDetector(db=db)
    ntropy_client = NtropyClient()

    if not ntropy_client.is_enabled():
        print("Ntropy is not enabled. Skipping enrichment.")
        return

    # Get all transactions without enrichment
    transactions = db.query(Transaction).filter(
        Transaction.enriched_merchant == None
    ).all()

    print(f"Starting enrichment for {len(transactions)} transactions...")

    enriched_count = 0
    transfer_count = 0

    for tx in transactions:
        # Step 1: Check if transfer using existing detector
        tx.is_transfer = transfer_detector.is_transfer(tx)

        if tx.is_transfer:
            # Mark as transfer, no need to enrich
            tx.categorization_source = "rule"
            tx.categorization_confidence = 0.95
            tx.enriched_at = datetime.utcnow()
            transfer_count += 1
        else:
            # Step 2: Enrich with Ntropy
            try:
                enriched = await ntropy_client.enrich_transaction(tx)

                if enriched:
                    tx.enriched_merchant = enriched["merchant"]
                    tx.enriched_category = enriched["category"]
                    tx.categorization_source = "ntropy"
                    tx.categorization_confidence = enriched["confidence"]
                    tx.enriched_at = datetime.utcnow()
                    enriched_count += 1

            except Exception as e:
                print(f"Failed to enrich transaction {tx.id}: {e}")
                continue

        # Commit in batches of 50 for efficiency
        if (enriched_count + transfer_count) % 50 == 0:
            db.commit()
            print(f"Progress: {enriched_count} enriched, {transfer_count} transfers")

    # Final commit
    db.commit()
    print(f"Enrichment complete: {enriched_count} enriched, {transfer_count} transfers")


@router.post("/enrich/all", response_model=EnrichmentStatus)
async def enrich_all_transactions(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Enrich all uncategorized transactions using Ntropy.
    Runs in background to avoid timeout.

    This will:
    1. Detect and flag internal transfers
    2. Enrich non-transfers with Ntropy merchant/category data
    """
    total = db.query(Transaction).count()
    enriched = db.query(Transaction).filter(
        Transaction.enriched_merchant != None
    ).count()

    # Start background task
    background_tasks.add_task(enrich_transactions_task, db)

    return EnrichmentStatus(
        message="Enrichment started in background",
        total_transactions=total,
        enriched=enriched,
        pending=total - enriched
    )


@router.post("/enrich/{transaction_id}")
async def enrich_single_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Enrich a single transaction by ID.

    Useful for re-enriching specific transactions or testing.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transfer_detector = TransferDetector(db=db)
    ntropy_client = NtropyClient()

    # Check if transfer
    transaction.is_transfer = transfer_detector.is_transfer(transaction)

    if transaction.is_transfer:
        transaction.categorization_source = "rule"
        transaction.categorization_confidence = 0.95
        transaction.enriched_at = datetime.utcnow()
        db.commit()

        return {
            "message": "Transaction identified as transfer",
            "is_transfer": True,
            "source": "rule"
        }

    # Enrich with Ntropy
    if ntropy_client.is_enabled():
        enriched = await ntropy_client.enrich_transaction(transaction)

        if enriched:
            transaction.enriched_merchant = enriched["merchant"]
            transaction.enriched_category = enriched["category"]
            transaction.categorization_source = "ntropy"
            transaction.categorization_confidence = enriched["confidence"]
            transaction.enriched_at = datetime.utcnow()
            db.commit()

            return {
                "message": "Transaction enriched successfully",
                "merchant": enriched["merchant"],
                "category": enriched["category"],
                "confidence": enriched["confidence"]
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Ntropy enrichment failed"
            )
    else:
        raise HTTPException(
            status_code=503,
            detail="Ntropy is not enabled. Check NTROPY_API_KEY and USE_NTROPY settings."
        )


@router.get("/stats", response_model=CategoryStats)
def get_categorization_stats(db: Session = Depends(get_db)):
    """Get statistics on categorization coverage"""
    total = db.query(Transaction).count()
    enriched = db.query(Transaction).filter(
        Transaction.enriched_merchant != None
    ).count()
    transfers = db.query(Transaction).filter(
        Transaction.is_transfer == True
    ).count()

    # Count by source
    by_source = {}
    source_counts = db.query(
        Transaction.categorization_source,
        func.count(Transaction.id)
    ).filter(
        Transaction.categorization_source != None
    ).group_by(
        Transaction.categorization_source
    ).all()

    for source, count in source_counts:
        by_source[source] = count

    return CategoryStats(
        total_transactions=total,
        enriched=enriched,
        transfers=transfers,
        coverage_percent=round((enriched / total * 100), 2) if total > 0 else 0.0,
        by_source=by_source
    )


@router.get("/ntropy/status", response_model=NtropyStatus)
async def get_ntropy_status():
    """
    Check Ntropy API status and connectivity.

    Returns enabled state and connection test result.
    """
    ntropy_client = NtropyClient()

    if not ntropy_client.is_enabled():
        return NtropyStatus(
            enabled=False,
            connected=False,
            message="Ntropy is not enabled. Set NTROPY_API_KEY and USE_NTROPY=true in .env"
        )

    # Test connection
    connected = await ntropy_client.test_connection()

    if connected:
        return NtropyStatus(
            enabled=True,
            connected=True,
            message="Ntropy API is connected and working"
        )
    else:
        return NtropyStatus(
            enabled=True,
            connected=False,
            message="Ntropy API key is set but connection failed. Check your API key."
        )


@router.delete("/clear-enrichment")
def clear_all_enrichment(db: Session = Depends(get_db)):
    """
    Clear all enrichment data from transactions.

    WARNING: This will delete all Ntropy enrichment results.
    Useful for testing or re-enriching with different settings.
    """
    count = db.query(Transaction).filter(
        Transaction.enriched_merchant != None
    ).count()

    # Clear enrichment fields
    db.query(Transaction).update({
        Transaction.enriched_merchant: None,
        Transaction.enriched_category: None,
        Transaction.is_transfer: False,
        Transaction.categorization_source: None,
        Transaction.categorization_confidence: None,
        Transaction.enriched_at: None
    })

    db.commit()

    return {
        "message": "Enrichment data cleared",
        "cleared_count": count
    }


# ========================================
# CASCADE ENRICHMENT ENDPOINTS (NEW!)
# ========================================
# These use the smart multi-tier approach:
# Pattern → LLM → LLM+Search → Ntropy
# Target: 88-95% cost savings vs Ntropy-only
# ========================================


class CascadeStats(BaseModel):
    total_cost: float
    total_transactions: int
    cost_per_transaction: float
    methods_used: dict
    cost_by_method: dict
    ntropy_cost_would_be: float
    savings_amount: float
    savings_percent: float


async def cascade_enrich_transactions_task(db: Session):
    """Background task to enrich transactions using cascade strategy"""
    transfer_detector = TransferDetector(db=db)
    cascade = CascadeEnrichment()

    # Get all transactions without enrichment
    transactions = db.query(Transaction).filter(
        Transaction.enriched_merchant == None
    ).all()

    print(f"Starting cascade enrichment for {len(transactions)} transactions...")

    enriched_count = 0
    transfer_count = 0

    for tx in transactions:
        # Step 1: Check if transfer using existing detector
        tx.is_transfer = transfer_detector.is_transfer(tx)

        if tx.is_transfer:
            # Mark as transfer, no need to enrich
            tx.categorization_source = "rule"
            tx.categorization_confidence = 0.95
            tx.enriched_at = datetime.utcnow()
            transfer_count += 1
        else:
            # Step 2: Cascade enrichment
            try:
                result = await cascade.enrich_transaction(tx)

                if result["merchant"]:
                    tx.enriched_merchant = result["merchant"]
                    tx.enriched_category = result["category"]
                    tx.categorization_source = result["source"]
                    tx.categorization_confidence = result["confidence"]
                    tx.enriched_at = datetime.utcnow()
                    enriched_count += 1

            except Exception as e:
                print(f"Failed to enrich transaction {tx.id}: {e}")
                continue

        # Commit in batches of 50 for efficiency
        if (enriched_count + transfer_count) % 50 == 0:
            db.commit()
            print(f"Progress: {enriched_count} enriched, {transfer_count} transfers")

    # Final commit
    db.commit()

    # Print final stats
    stats = cascade.get_stats()
    print(f"Cascade enrichment complete!")
    print(f"  Enriched: {enriched_count}")
    print(f"  Transfers: {transfer_count}")
    print(f"  Total cost: ${stats['total_cost']}")
    print(f"  Saved: ${stats['savings_amount']} ({stats['savings_percent']}%)")
    print(f"  Methods: {stats['methods_used']}")


@router.post("/cascade/enrich/all", response_model=EnrichmentStatus)
async def cascade_enrich_all(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Enrich all transactions using CASCADE strategy (Pattern → LLM → Search → Ntropy).

    This is the SMART, COST-OPTIMIZED approach:
    - 70% handled by pattern matching (FREE)
    - 20% handled by Claude Haiku ($0.00025)
    - 8% handled by Claude + Search ($0.00525)
    - 2% handled by Ntropy ($0.02)

    Expected: 88-95% cost savings vs Ntropy-only!
    """
    total = db.query(Transaction).count()
    enriched = db.query(Transaction).filter(
        Transaction.enriched_merchant != None
    ).count()

    # Start background task
    background_tasks.add_task(cascade_enrich_transactions_task, db)

    return EnrichmentStatus(
        message="Cascade enrichment started in background (Pattern → LLM → Search → Ntropy)",
        total_transactions=total,
        enriched=enriched,
        pending=total - enriched
    )


@router.post("/cascade/enrich/{transaction_id}")
async def cascade_enrich_single(
    transaction_id: str,
    force_method: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Enrich a single transaction using CASCADE strategy.

    Args:
        transaction_id: Transaction ID
        force_method: Optional - force a specific method for testing
            Options: "pattern", "llm_basic", "llm_search", "ntropy"

    Returns enrichment result with method used and cost.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Check if transfer
    transfer_detector = TransferDetector(db=db)
    transaction.is_transfer = transfer_detector.is_transfer(transaction)

    if transaction.is_transfer:
        transaction.categorization_source = "rule"
        transaction.categorization_confidence = 0.95
        transaction.enriched_at = datetime.utcnow()
        db.commit()

        return {
            "message": "Transaction identified as transfer",
            "is_transfer": True,
            "source": "rule",
            "cost": 0.0
        }

    # Cascade enrichment
    cascade = CascadeEnrichment()
    result = await cascade.enrich_transaction(transaction, force_method=force_method)

    if result["merchant"]:
        transaction.enriched_merchant = result["merchant"]
        transaction.enriched_category = result["category"]
        transaction.categorization_source = result["source"]
        transaction.categorization_confidence = result["confidence"]
        transaction.enriched_at = datetime.utcnow()
        db.commit()

        return {
            "message": "Transaction enriched successfully",
            "merchant": result["merchant"],
            "category": result["category"],
            "address": result.get("address"),
            "city": result.get("city"),
            "state": result.get("state"),
            "confidence": result["confidence"],
            "method_used": result["method_used"],
            "cost": result["cost"],
            "searched": result.get("searched", False),
            "search_query": result.get("search_query")
        }
    else:
        raise HTTPException(
            status_code=503,
            detail="All enrichment methods failed"
        )


@router.get("/cascade/stats", response_model=CascadeStats)
def get_cascade_stats():
    """
    Get cost statistics for cascade enrichment.

    Shows:
    - Total cost vs Ntropy-only cost
    - Cost breakdown by method
    - Savings percentage
    - Method usage distribution

    NOTE: This creates a new CascadeEnrichment instance,
    so stats are only available during a session.
    For persistent stats, check database categorization_source field.
    """
    cascade = CascadeEnrichment()

    # This will show 0s if no enrichment done in this session
    # In production, you'd track this in database or cache
    stats = cascade.get_stats()

    return CascadeStats(**stats)


@router.post("/cascade/test/{transaction_id}")
async def test_enrichment_methods(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Test ALL enrichment methods on a single transaction.

    Useful for:
    - Comparing results across methods
    - Debugging enrichment quality
    - Cost analysis

    Returns results from:
    1. Pattern matching
    2. Claude Haiku basic
    3. Claude Haiku + Search
    4. Ntropy (if enabled)
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    cascade = CascadeEnrichment()
    results = {}

    # Test pattern matching
    try:
        result = await cascade.enrich_transaction(transaction, force_method="pattern")
        results["pattern_matching"] = result
    except Exception as e:
        results["pattern_matching"] = {"error": str(e)}

    # Test Claude Haiku basic
    try:
        result = await cascade.enrich_transaction(transaction, force_method="llm_basic")
        results["claude_haiku"] = result
    except Exception as e:
        results["claude_haiku"] = {"error": str(e)}

    # Test Claude Haiku + Search
    try:
        result = await cascade.enrich_transaction(transaction, force_method="llm_search")
        results["claude_haiku_search"] = result
    except Exception as e:
        results["claude_haiku_search"] = {"error": str(e)}

    # Test Ntropy
    try:
        result = await cascade.enrich_transaction(transaction, force_method="ntropy")
        results["ntropy"] = result
    except Exception as e:
        results["ntropy"] = {"error": str(e)}

    return {
        "transaction": {
            "id": transaction.id,
            "description": transaction.description,
            "amount": transaction.amount
        },
        "results": results,
        "comparison": {
            "cheapest": "pattern_matching ($0.00)",
            "fastest": "pattern_matching (instant)",
            "most_detailed": "claude_haiku_search or ntropy",
            "recommended": "Use cascade endpoint - auto-selects best method"
        }
    }
