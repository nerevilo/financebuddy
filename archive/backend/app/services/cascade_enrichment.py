"""
Cascade Enrichment Strategy

Smart multi-tier approach that minimizes costs while maximizing accuracy.

Flow:
1. Cache check (already enriched?) → FREE, instant
2. Semantic + Rule matching (intelligent patterns) → FREE, instant
3. Gemini Flash (simple cases) → $0.000075, 300ms (FREE tier: 1,500/day!)
4. Gemini Flash + Search (complex cases) → $0.005075, 3-5s
5. Ntropy (fallback for failures) → $0.02, 2-3s

Key Features:
- Priority-based pattern matching (COSTCO GAS before COSTCO)
- Semantic similarity using sentence-transformers
- Standardized category taxonomy
- Category normalization for consistent output

Cost Optimization:
- 75% handled by semantic/rule matching → FREE
- 17% handled by Gemini Flash → $0.000075 (FREE tier!)
- 6% handled by Gemini + Search → $0.005075
- 2% handled by Ntropy → $0.02

Expected cost for 791 transactions:
- Semantic/Rule: 593 × $0.00 = $0.00
- Gemini: 134 × $0.000075 = $0.01 (FREE tier!)
- Gemini+Search: 47 × $0.005075 = $0.24
- Ntropy: 17 × $0.02 = $0.34
TOTAL: $0.59 (vs $15.82 with Ntropy only = 96% savings!)
"""
from typing import Optional, Dict, List, Tuple
from ..models.models import Transaction
from ..core.config import get_settings
from ..core.logging_config import get_logger
from .semantic_matcher import get_semantic_matcher
from .gemini_enrichment import GeminiEnrichment
from .ntropy_client import NtropyClient
from .categories import normalize_category_id

logger = get_logger(__name__)


class CascadeEnrichment:
    """
    Intelligent multi-tier enrichment strategy

    Tries methods from cheapest to most expensive,
    stopping as soon as we get a confident result.

    Uses semantic matching with BERT embeddings for intelligent
    category detection (e.g., "COSTCO GAS" → gas_stations, not groceries).
    """

    def __init__(self):
        self.semantic_matcher = get_semantic_matcher()
        self.gemini = GeminiEnrichment()
        self.ntropy = NtropyClient()
        self.settings = get_settings()

        # Confidence thresholds
        # High confidence = trust rule match, skip LLM (fast & free)
        # Low confidence = pass to Gemini Flash for verification
        self.HIGH_CONFIDENCE_THRESHOLD = 0.85  # Trust rule match completely
        self.MEDIUM_CONFIDENCE_THRESHOLD = 0.70  # Use as hint for LLM
        self.LLM_BASIC_THRESHOLD = 0.70
        self.LLM_SEARCH_THRESHOLD = 0.65

        # Track costs
        self.total_cost = 0.0
        self.method_counts = {
            "cache": 0,
            "semantic_rule": 0,
            "semantic_similarity": 0,
            "llm_basic": 0,
            "llm_cached": 0,  # LLM cache hits
            "llm_search": 0,
            "ntropy": 0
        }

    async def enrich_transaction(
        self,
        transaction: Transaction,
        force_method: Optional[str] = None
    ) -> Dict:
        """
        Enrich a transaction using cascade strategy

        Args:
            transaction: Transaction to enrich
            force_method: Force a specific method (for testing)
                Options: "pattern", "llm_basic", "llm_search", "ntropy"

        Returns:
            {
                "merchant": "Hardee's",
                "category": "fast food",
                "address": "...",
                "city": "Franklin",
                "state": "TN",
                "confidence": 0.92,
                "source": "pattern|llm_basic|llm_search|ntropy",
                "cost": 0.00,
                "searched": false,
                "method_used": "pattern_matching"
            }
        """
        result = {
            "merchant": None,
            "category": None,
            "address": None,
            "city": None,
            "state": None,
            "confidence": 0.0,
            "source": None,
            "cost": 0.0,
            "searched": False,
            "method_used": None
        }

        # Step 1: Check cache (already enriched?)
        if not force_method and transaction.enriched_merchant:
            self.method_counts["cache"] += 1
            result.update({
                "merchant": transaction.enriched_merchant,
                "category": transaction.enriched_category,
                "confidence": transaction.categorization_confidence or 0.9,
                "source": transaction.categorization_source or "cache",
                "cost": 0.0,
                "method_used": "cache"
            })
            return result

        # Step 2: Try semantic + rule matching (FREE)
        # High confidence matches are returned immediately
        # Medium/low confidence matches are passed to LLM for verification
        semantic_result = None
        semantic_hint = None

        if not force_method or force_method == "semantic":
            semantic_result = self.semantic_matcher.match(transaction.description)

            if semantic_result:
                source_type = semantic_result.get("source", "semantic")
                confidence = semantic_result.get("confidence", 0.0)

                # HIGH CONFIDENCE: Trust rule match completely (fast & free)
                # Examples: "COSTCO GAS" → gas_stations, "CLAUDE" → software_subscriptions
                if source_type == "rule_match" and confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                    self.method_counts["semantic_rule"] += 1
                    self.total_cost += 0.0
                    result.update({
                        "merchant": semantic_result.get("merchant"),
                        "category": normalize_category_id(semantic_result.get("category", "other")),
                        "confidence": confidence,
                        "source": "semantic_rule",
                        "cost": 0.0,
                        "method_used": "semantic_rule",
                        "matched_pattern": semantic_result.get("matched_pattern")
                    })
                    logger.debug("High-confidence rule match", extra={
                        "merchant": semantic_result.get('merchant'),
                        "pattern": semantic_result.get('matched_pattern'),
                        "confidence": confidence
                    })
                    return result

                # MEDIUM CONFIDENCE: Save as hint for LLM verification
                # The LLM will use this as context but make its own decision
                elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                    semantic_hint = {
                        "suggested_merchant": semantic_result.get("merchant"),
                        "suggested_category": semantic_result.get("category"),
                        "confidence": confidence,
                        "source": source_type
                    }
                    logger.debug("Medium-confidence match, passing to LLM", extra={
                        "hint": semantic_hint
                    })

        # Step 3: Try Gemini Flash basic (CHEAP & FREE!)
        # Pass semantic hint if available for better accuracy
        if not force_method or force_method == "llm_basic":
            llm_result = await self.gemini.enrich_basic(transaction, hint=semantic_hint)

            if llm_result and llm_result.get("confidence", 0) >= self.LLM_BASIC_THRESHOLD:
                # Check if this was a cache hit
                was_cached = llm_result.get("cached", False)
                if was_cached:
                    self.method_counts["llm_cached"] += 1
                    cost = 0.0
                else:
                    self.method_counts["llm_basic"] += 1
                    cost = 0.000075
                    self.total_cost += cost

                # Category is already normalized in gemini_enrichment
                method_used = "llm_cached" if was_cached else ("llm_with_hint" if semantic_hint else "llm_basic")
                result.update({
                    "merchant": llm_result.get("merchant"),
                    "category": llm_result.get("category", "other"),
                    "city": llm_result.get("city"),
                    "state": llm_result.get("state"),
                    "confidence": llm_result.get("confidence"),
                    "source": llm_result.get("source", "gemini_flash"),
                    "cost": cost,
                    "method_used": method_used,
                    "had_hint": semantic_hint is not None,
                    "cached": was_cached
                })
                logger.debug("Gemini Flash enrichment", extra={
                    "merchant": llm_result.get('merchant'),
                    "had_hint": semantic_hint is not None,
                    "cached": was_cached
                })
                return result

        # Step 4: Try Gemini Flash + Search (MODERATE)
        if not force_method or force_method == "llm_search":
            search_result = await self.gemini.enrich_with_search(transaction)

            if search_result and search_result["confidence"] >= self.LLM_SEARCH_THRESHOLD:
                self.method_counts["llm_search"] += 1
                cost = search_result.get("cost", 0.005075)
                self.total_cost += cost
                result.update({
                    "merchant": search_result["merchant"],
                    "category": search_result["category"],
                    "address": search_result.get("address"),
                    "city": search_result.get("city"),
                    "state": search_result.get("state"),
                    "confidence": search_result["confidence"],
                    "source": "gemini_flash_search",
                    "cost": cost,
                    "searched": search_result.get("searched", False),
                    "search_query": search_result.get("search_query"),
                    "method_used": "llm_search"
                })
                logger.debug("Gemini + Search enrichment", extra={"merchant": search_result['merchant']})
                return result

        # Step 5: Fallback to Ntropy (EXPENSIVE but reliable)
        if (not force_method or force_method == "ntropy") and self.settings.use_ntropy:
            ntropy_result = await self.ntropy.enrich_transaction(transaction)

            if ntropy_result:
                self.method_counts["ntropy"] += 1
                self.total_cost += 0.02
                result.update({
                    "merchant": ntropy_result.get("merchant"),
                    "category": ntropy_result.get("category"),
                    "address": ntropy_result.get("location", {}).get("address"),
                    "city": ntropy_result.get("location", {}).get("city"),
                    "state": ntropy_result.get("location", {}).get("state"),
                    "confidence": 0.95,  # Ntropy is very accurate
                    "source": "ntropy",
                    "cost": 0.02,
                    "method_used": "ntropy"
                })
                logger.debug("Ntropy enrichment", extra={"merchant": ntropy_result.get('merchant')})
                return result

        # If all methods failed
        logger.warning("All enrichment methods failed", extra={"description": transaction.description})
        result["method_used"] = "failed"
        return result

    async def enrich_batch(self, transactions: List[Transaction]) -> List[Dict]:
        """
        Batch enrichment - optimized for processing multiple transactions.

        Strategy:
        1. Apply semantic/rule matching to ALL transactions first (FREE, instant)
        2. Separate into: already_done, high_confidence_rules, needs_llm
        3. Batch LLM calls for transactions that need it
        4. Return results in original order

        This is significantly faster than calling enrich_transaction() in a loop
        because it batches the LLM calls (5-10x fewer API calls).

        Args:
            transactions: List of transactions to enrich

        Returns:
            List of enrichment results (same order as input)
        """
        if not transactions:
            return []

        results: List[Dict] = []
        needs_llm: List[Tuple[int, Transaction, Optional[Dict]]] = []  # (index, tx, hint)

        # Step 1: Process all transactions through semantic/rule matching
        for i, tx in enumerate(transactions):
            result = {
                "merchant": None,
                "category": None,
                "address": None,
                "city": None,
                "state": None,
                "confidence": 0.0,
                "source": None,
                "cost": 0.0,
                "searched": False,
                "method_used": None
            }

            # Check if already enriched
            if tx.enriched_merchant:
                self.method_counts["cache"] += 1
                result.update({
                    "merchant": tx.enriched_merchant,
                    "category": tx.enriched_category,
                    "confidence": tx.categorization_confidence or 0.9,
                    "source": tx.categorization_source or "cache",
                    "cost": 0.0,
                    "method_used": "cache"
                })
                results.append(result)
                continue

            # Try semantic/rule matching
            semantic_result = self.semantic_matcher.match(tx.description)
            semantic_hint = None

            if semantic_result:
                source_type = semantic_result.get("source", "semantic")
                confidence = semantic_result.get("confidence", 0.0)

                # HIGH CONFIDENCE: Use rule match directly
                if source_type == "rule_match" and confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                    self.method_counts["semantic_rule"] += 1
                    result.update({
                        "merchant": semantic_result.get("merchant"),
                        "category": normalize_category_id(semantic_result.get("category", "other")),
                        "confidence": confidence,
                        "source": "semantic_rule",
                        "cost": 0.0,
                        "method_used": "semantic_rule",
                        "matched_pattern": semantic_result.get("matched_pattern")
                    })
                    results.append(result)
                    continue

                # MEDIUM CONFIDENCE: Save as hint for LLM
                elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                    semantic_hint = {
                        "suggested_merchant": semantic_result.get("merchant"),
                        "suggested_category": semantic_result.get("category"),
                        "confidence": confidence,
                        "source": source_type
                    }

            # Needs LLM processing
            results.append(result)  # Placeholder, will be updated
            needs_llm.append((i, tx, semantic_hint))

        # Step 2: Batch process transactions that need LLM
        if needs_llm:
            logger.info("Batch enrichment: sending to LLM", extra={
                "total": len(transactions),
                "needs_llm": len(needs_llm),
                "from_rules": len(transactions) - len(needs_llm)
            })

            # Extract just the transactions for batch processing
            llm_transactions = [tx for _, tx, _ in needs_llm]
            llm_results = await self.gemini.enrich_batch(llm_transactions)

            # Update results with LLM responses
            for (idx, tx, hint), llm_result in zip(needs_llm, llm_results):
                if llm_result and llm_result.get("confidence", 0) >= self.LLM_BASIC_THRESHOLD:
                    was_cached = llm_result.get("cached", False)
                    if was_cached:
                        self.method_counts["llm_cached"] += 1
                        cost = 0.0
                    else:
                        self.method_counts["llm_basic"] += 1
                        cost = llm_result.get("cost", 0.000075)
                        self.total_cost += cost

                    results[idx].update({
                        "merchant": llm_result.get("merchant"),
                        "category": llm_result.get("category", "other"),
                        "city": llm_result.get("city"),
                        "state": llm_result.get("state"),
                        "confidence": llm_result.get("confidence"),
                        "source": llm_result.get("source", "gemini_flash_batch"),
                        "cost": cost,
                        "method_used": "llm_batch",
                        "had_hint": hint is not None,
                        "cached": was_cached
                    })
                else:
                    # LLM failed for this transaction, mark as failed
                    results[idx]["method_used"] = "failed"
                    logger.warning("Batch LLM failed for transaction", extra={
                        "description": tx.description[:50]
                    })

        logger.info("Batch enrichment complete", extra={
            "total": len(transactions),
            "successful": sum(1 for r in results if r.get("method_used") != "failed"),
            "from_rules": sum(1 for r in results if r.get("method_used") == "semantic_rule"),
            "from_llm": sum(1 for r in results if r.get("method_used") == "llm_batch"),
            "from_cache": sum(1 for r in results if r.get("method_used") == "cache")
        })

        return results

    def get_stats(self) -> Dict:
        """
        Get enrichment statistics

        Returns:
            {
                "total_cost": 0.59,
                "total_transactions": 791,
                "cost_per_transaction": 0.0007,
                "methods_used": {
                    "cache": 100,
                    "semantic_rule": 450,
                    "semantic_similarity": 100,
                    "llm_basic": 100,
                    "llm_search": 30,
                    "ntropy": 11
                },
                "cost_by_method": {...},
                "savings_vs_ntropy": "96%"
            }
        """
        total_transactions = sum(self.method_counts.values())
        ntropy_cost = total_transactions * 0.02
        savings_percent = 0

        if ntropy_cost > 0:
            savings_percent = ((ntropy_cost - self.total_cost) / ntropy_cost) * 100

        # Count free methods (semantic matching + LLM cache hits)
        free_count = (
            self.method_counts.get("cache", 0) +
            self.method_counts.get("semantic_rule", 0) +
            self.method_counts.get("semantic_similarity", 0) +
            self.method_counts.get("llm_cached", 0)
        )

        return {
            "total_cost": round(self.total_cost, 2),
            "total_transactions": total_transactions,
            "cost_per_transaction": round(self.total_cost / max(total_transactions, 1), 6),
            "methods_used": self.method_counts,
            "cost_by_method": {
                "cache": 0.00,
                "semantic_rule": 0.00,
                "semantic_similarity": 0.00,
                "llm_cached": 0.00,  # Cache hits are free
                "llm_basic": round(self.method_counts.get("llm_basic", 0) * 0.000075, 4),
                "llm_search": round(self.method_counts.get("llm_search", 0) * 0.005075, 2),
                "ntropy": round(self.method_counts.get("ntropy", 0) * 0.02, 2)
            },
            "free_matches_count": free_count,
            "free_matches_percent": round((free_count / max(total_transactions, 1)) * 100, 1),
            "llm_cache_hits": self.method_counts.get("llm_cached", 0),
            "ntropy_cost_would_be": round(ntropy_cost, 2),
            "savings_amount": round(ntropy_cost - self.total_cost, 2),
            "savings_percent": round(savings_percent, 1)
        }

    def reset_stats(self):
        """Reset cost tracking"""
        self.total_cost = 0.0
        self.method_counts = {
            "cache": 0,
            "semantic_rule": 0,
            "semantic_similarity": 0,
            "llm_basic": 0,
            "llm_cached": 0,
            "llm_search": 0,
            "ntropy": 0
        }


# Example usage:
"""
cascade = CascadeEnrichment()

# Enrich single transaction
result = await cascade.enrich_transaction(transaction)

# Enrich all transactions
for txn in transactions:
    result = await cascade.enrich_transaction(txn)

# Get cost stats
stats = cascade.get_stats()
# Log stats: Total cost, savings, methods used

# Expected output:
# Total cost: $0.71
# Saved: $15.11 (95.5%)
# Methods: {'pattern': 553, 'llm_basic': 158, 'llm_search': 63, 'ntropy': 17}
"""
