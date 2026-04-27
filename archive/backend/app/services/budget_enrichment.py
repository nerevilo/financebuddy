"""
Budget-Aware Enrichment Service

Enriches transactions while respecting per-user spending limits.
- New users: auto-enrich up to budget limit
- Existing users with new transactions: enrich new data up to remaining budget
- Default budget: $1.00 per user
"""
from datetime import datetime, timezone
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models import User, Transaction, Account, Institution, MerchantCategoryRule
from ..core.logging_config import get_logger
from .categorization import TransferDetector
from .cascade_enrichment import CascadeEnrichment

logger = get_logger(__name__)


# Estimated costs per method (conservative estimates)
COST_ESTIMATES = {
    "semantic_rule": 0.0,      # Rule-based matching (FREE)
    "semantic_similarity": 0.0, # BERT embedding similarity (FREE)
    "pattern": 0.0,            # Legacy pattern matching (FREE)
    "gemini": 0.0001,          # Gemini Flash is very cheap
    "llm_basic": 0.00025,      # Claude Haiku
    "llm_search": 0.00525,     # Claude Haiku + search
    "ntropy": 0.02,            # Ntropy API
}

# Default: use semantic matching + Gemini cascade (cheapest effective option)
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
                tx.enriched_at = datetime.now(timezone.utc)
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
                    tx.enriched_at = datetime.now(timezone.utc)
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

        OPTIMIZED: Uses batch LLM processing for 5-10x fewer API calls.

        Priority order:
        1. User merchant category rules (free, highest priority)
        2. Transfer detection (free)
        3. Batch ML enrichment (paid, batched for efficiency)

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

        # Get the specific transactions — scoped to this user only
        transactions = self.db.query(Transaction).join(Account).join(Institution).filter(
            Transaction.id.in_(transaction_ids),
            Institution.user_id == user_id
        ).all()

        if not transactions:
            return {"enriched": 0, "message": "No transactions to enrich"}

        # Load user's merchant category rules into a dict for fast lookup
        rules = self.db.query(MerchantCategoryRule).filter(
            and_(
                MerchantCategoryRule.user_id == user_id,
                MerchantCategoryRule.is_active == True
            )
        ).all()
        merchant_rules = {rule.merchant_name: rule for rule in rules}

        transfer_count = 0
        rule_applied_count = 0
        needs_ml_enrichment: List[Transaction] = []

        # FIRST PASS: Apply free methods (rules + transfer detection)
        for tx in transactions:
            # Check user merchant category rules (free, takes precedence)
            if tx.merchant_name and tx.merchant_name in merchant_rules:
                rule = merchant_rules[tx.merchant_name]
                tx.enriched_category = rule.category
                tx.categorization_source = "user_rule"
                tx.categorization_confidence = 1.0
                tx.enriched_at = datetime.now(timezone.utc)
                rule.times_applied = (rule.times_applied or 0) + 1
                rule_applied_count += 1
                continue

            # Check transfer (free)
            if self.transfer_detector.is_transfer(tx):
                tx.is_transfer = True
                tx.categorization_source = "rule"
                tx.categorization_confidence = 0.95
                tx.enriched_at = datetime.now(timezone.utc)
                transfer_count += 1
                continue

            # Needs ML enrichment
            needs_ml_enrichment.append(tx)

        # Commit free enrichments
        self.db.commit()

        # SECOND PASS: Batch ML enrichment (paid)
        enriched_count = 0
        total_cost = 0.0

        if needs_ml_enrichment:
            # Limit to budget
            max_affordable = self.max_transactions_for_budget(remaining_budget, DEFAULT_METHOD)
            txns_to_enrich = needs_ml_enrichment[:max_affordable]

            logger.info("Batch enriching transactions", extra={
                "total_new": len(transactions),
                "needs_ml": len(needs_ml_enrichment),
                "processing": len(txns_to_enrich),
                "user_rules_applied": rule_applied_count,
                "transfers_detected": transfer_count
            })

            # Use batch enrichment (5-10x fewer API calls!)
            cascade = CascadeEnrichment()
            try:
                results = await cascade.enrich_batch(txns_to_enrich)

                # Apply results to transactions
                for tx, result in zip(txns_to_enrich, results):
                    if result and result.get("merchant"):
                        tx.enriched_merchant = result["merchant"]
                        tx.enriched_category = result["category"]
                        tx.categorization_source = result.get("source", "cascade_batch")
                        tx.categorization_confidence = result.get("confidence", 0.8)
                        tx.enriched_at = datetime.now(timezone.utc)
                        enriched_count += 1
                        total_cost += result.get("cost", 0.0001)
                    elif result and result.get("method_used") == "failed":
                        # Track failed enrichments for retry
                        logger.warning("Enrichment failed", extra={
                            "transaction_id": tx.id,
                            "description": tx.description[:50]
                        })

                # Commit ML enrichments
                self.db.commit()

            except Exception as e:
                logger.error("Batch enrichment failed", extra={"error": str(e)})

        # Update user's spent budget
        user.enrichment_spent = (user.enrichment_spent or 0) + total_cost
        self.db.commit()

        return {
            "enriched": enriched_count,
            "transfers_detected": transfer_count,
            "user_rules_applied": rule_applied_count,
            "cost": round(total_cost, 4),
            "budget_remaining": round(self.get_remaining_budget(user), 4),
            "batch_processed": len(needs_ml_enrichment) if needs_ml_enrichment else 0
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
