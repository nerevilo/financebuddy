"""
Budget-Aware Enrichment Service

Enriches transactions while respecting per-user spending limits.
- New users: auto-enrich up to budget limit
- Existing users with new transactions: enrich new data up to remaining budget
- Default budget: $1.00 per user
"""
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import User, Transaction, Account, Institution
from ..core.logging_config import get_logger
from .categorization import TransferDetector
from .cascade_enrichment import CascadeEnrichment

logger = get_logger(__name__)


# Estimated costs per method (conservative estimates)
COST_ESTIMATES = {
    "pattern": 0.0,
    "gemini": 0.0001,      # Gemini Flash is very cheap
    "llm_basic": 0.00025,  # Claude Haiku
    "llm_search": 0.00525, # Claude Haiku + search
    "ntropy": 0.02,        # Ntropy API
}

# Default: use pattern matching + Gemini (cheapest effective option)
DEFAULT_METHOD = "gemini"


class BudgetEnrichmentService:
    """
    Enriches user transactions within their budget limit.
    """

    def __init__(self, db: Session):
        self.db = db
        self.transfer_detector = TransferDetector(db=db)

    def get_remaining_budget(self, user: User) -> float:
        """Get user's remaining enrichment budget."""
        return max(0, user.enrichment_budget - (user.enrichment_spent or 0))

    def get_unenriched_transactions(self, user_id: str, limit: Optional[int] = None) -> List[Transaction]:
        """Get transactions that haven't been enriched yet for a user."""
        query = self.db.query(Transaction).join(Account).join(Institution).filter(
            and_(
                Institution.user_id == user_id,
                Transaction.enriched_merchant.is_(None),
                Transaction.is_transfer == False
            )
        ).order_by(Transaction.date.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def estimate_cost(self, num_transactions: int, method: str = DEFAULT_METHOD) -> float:
        """Estimate cost for enriching N transactions."""
        cost_per_tx = COST_ESTIMATES.get(method, 0.001)
        return num_transactions * cost_per_tx

    def max_transactions_for_budget(self, budget: float, method: str = DEFAULT_METHOD) -> int:
        """Calculate max transactions that can be enriched within budget."""
        cost_per_tx = COST_ESTIMATES.get(method, 0.001)
        if cost_per_tx == 0:
            return 10000  # Unlimited for free methods
        return int(budget / cost_per_tx)

    async def enrich_user_transactions(
        self,
        user_id: str,
        max_transactions: Optional[int] = None,
        method: str = DEFAULT_METHOD
    ) -> Dict:
        """
        Enrich transactions for a user within their budget.

        Args:
            user_id: User ID
            max_transactions: Optional limit on transactions to process
            method: Enrichment method to use

        Returns:
            Dict with enrichment stats
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found", "enriched": 0}

        remaining_budget = self.get_remaining_budget(user)
        if remaining_budget <= 0:
            return {
                "error": "Budget exhausted",
                "enriched": 0,
                "budget_remaining": 0,
                "budget_spent": user.enrichment_spent
            }

        # Calculate how many we can afford
        max_affordable = self.max_transactions_for_budget(remaining_budget, method)

        # Apply user limit if provided
        if max_transactions:
            max_to_process = min(max_transactions, max_affordable)
        else:
            max_to_process = max_affordable

        # Get unenriched transactions
        transactions = self.get_unenriched_transactions(user_id, limit=max_to_process)

        if not transactions:
            return {
                "message": "No transactions to enrich",
                "enriched": 0,
                "budget_remaining": remaining_budget
            }

        # First pass: detect transfers (free)
        transfer_count = 0
        non_transfers = []

        for tx in transactions:
            if self.transfer_detector.is_transfer(tx):
                tx.is_transfer = True
                tx.categorization_source = "rule"
                tx.categorization_confidence = 0.95
                tx.enriched_at = datetime.utcnow()
                transfer_count += 1
            else:
                non_transfers.append(tx)

        self.db.commit()

        # Second pass: enrich non-transfers
        enriched_count = 0
        total_cost = 0.0
        cascade = CascadeEnrichment()

        for tx in non_transfers:
            # Check budget before each enrichment
            if total_cost >= remaining_budget:
                break

            try:
                result = await cascade.enrich_transaction(tx, force_method=method)

                if result.get("merchant"):
                    tx.enriched_merchant = result["merchant"]
                    tx.enriched_category = result["category"]
                    tx.categorization_source = result.get("source", method)
                    tx.categorization_confidence = result.get("confidence", 0.8)
                    tx.enriched_at = datetime.utcnow()
                    enriched_count += 1
                    total_cost += result.get("cost", COST_ESTIMATES.get(method, 0.001))

            except Exception as e:
                logger.error("Failed to enrich transaction", extra={"transaction_id": tx.id, "error": str(e)})
                continue

            # Commit in batches
            if enriched_count % 20 == 0:
                self.db.commit()

        # Update user's spent budget
        user.enrichment_spent = (user.enrichment_spent or 0) + total_cost
        self.db.commit()

        return {
            "enriched": enriched_count,
            "transfers_detected": transfer_count,
            "cost": round(total_cost, 4),
            "budget_remaining": round(self.get_remaining_budget(user), 4),
            "budget_spent": round(user.enrichment_spent, 4)
        }

    async def enrich_new_transactions(self, user_id: str, transaction_ids: List[str]) -> Dict:
        """
        Enrich specific new transactions (called after sync).

        Args:
            user_id: User ID
            transaction_ids: List of new transaction IDs to enrich

        Returns:
            Dict with enrichment stats
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        remaining_budget = self.get_remaining_budget(user)
        if remaining_budget <= 0:
            return {"error": "Budget exhausted", "enriched": 0}

        # Get the specific transactions
        transactions = self.db.query(Transaction).filter(
            Transaction.id.in_(transaction_ids)
        ).all()

        enriched_count = 0
        transfer_count = 0
        total_cost = 0.0
        cascade = CascadeEnrichment()

        for tx in transactions:
            if total_cost >= remaining_budget:
                break

            # Check transfer first (free)
            if self.transfer_detector.is_transfer(tx):
                tx.is_transfer = True
                tx.categorization_source = "rule"
                tx.categorization_confidence = 0.95
                tx.enriched_at = datetime.utcnow()
                transfer_count += 1
                continue

            try:
                result = await cascade.enrich_transaction(tx)

                if result.get("merchant"):
                    tx.enriched_merchant = result["merchant"]
                    tx.enriched_category = result["category"]
                    tx.categorization_source = result.get("source", "cascade")
                    tx.categorization_confidence = result.get("confidence", 0.8)
                    tx.enriched_at = datetime.utcnow()
                    enriched_count += 1
                    total_cost += result.get("cost", 0.0001)

            except Exception as e:
                logger.error("Failed to enrich transaction", extra={"transaction_id": tx.id, "error": str(e)})

        # Update spending
        user.enrichment_spent = (user.enrichment_spent or 0) + total_cost
        self.db.commit()

        return {
            "enriched": enriched_count,
            "transfers_detected": transfer_count,
            "cost": round(total_cost, 4),
            "budget_remaining": round(self.get_remaining_budget(user), 4)
        }

    def get_user_enrichment_stats(self, user_id: str) -> Dict:
        """Get enrichment statistics for a user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}

        total_tx = self.db.query(Transaction).join(Account).join(Institution).filter(
            Institution.user_id == user_id
        ).count()

        enriched_tx = self.db.query(Transaction).join(Account).join(Institution).filter(
            and_(
                Institution.user_id == user_id,
                Transaction.enriched_merchant.isnot(None)
            )
        ).count()

        unenriched_tx = self.db.query(Transaction).join(Account).join(Institution).filter(
            and_(
                Institution.user_id == user_id,
                Transaction.enriched_merchant.is_(None),
                Transaction.is_transfer == False
            )
        ).count()

        return {
            "total_transactions": total_tx,
            "enriched": enriched_tx,
            "unenriched": unenriched_tx,
            "budget_total": user.enrichment_budget,
            "budget_spent": user.enrichment_spent or 0,
            "budget_remaining": self.get_remaining_budget(user)
        }
