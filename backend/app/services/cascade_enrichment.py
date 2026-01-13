"""
Cascade Enrichment Strategy

Smart multi-tier approach that minimizes costs while maximizing accuracy.

Flow:
1. Cache check (already enriched?) → FREE, instant
2. Pattern matching (common merchants) → FREE, instant
3. Gemini Flash (simple cases) → $0.000075, 300ms (FREE tier: 1,500/day!)
4. Gemini Flash + Search (complex cases) → $0.005075, 3-5s
5. Ntropy (fallback for failures) → $0.02, 2-3s

Cost Optimization:
- 70% handled by pattern matching → FREE
- 20% handled by Gemini Flash → $0.000075 (FREE tier!)
- 8% handled by Gemini + Search → $0.005075
- 2% handled by Ntropy → $0.02

Expected cost for 791 transactions:
- Pattern: 553 × $0.00 = $0.00
- Gemini: 158 × $0.000075 = $0.01 (FREE tier!)
- Gemini+Search: 63 × $0.005075 = $0.32
- Ntropy: 17 × $0.02 = $0.34
TOTAL: $0.67 (vs $15.82 with Ntropy only = 96% savings!)
"""
from typing import Optional, Dict
from datetime import datetime
from ..models.models import Transaction
from ..core.config import get_settings
from ..core.logging_config import get_logger
from .merchant_patterns import MerchantPatternMatcher
from .gemini_enrichment import GeminiEnrichment
from .ntropy_client import NtropyClient

logger = get_logger(__name__)


class CascadeEnrichment:
    """
    Intelligent multi-tier enrichment strategy

    Tries methods from cheapest to most expensive,
    stopping as soon as we get a confident result.
    """

    def __init__(self):
        self.pattern_matcher = MerchantPatternMatcher()
        self.gemini = GeminiEnrichment()
        self.ntropy = NtropyClient()
        self.settings = get_settings()

        # Confidence thresholds
        self.PATTERN_THRESHOLD = 0.85
        self.LLM_BASIC_THRESHOLD = 0.75
        self.LLM_SEARCH_THRESHOLD = 0.70

        # Track costs
        self.total_cost = 0.0
        self.method_counts = {
            "cache": 0,
            "pattern": 0,
            "llm_basic": 0,
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

        # Step 2: Try pattern matching (FREE)
        if not force_method or force_method == "pattern":
            pattern_result = self.pattern_matcher.recognize_merchant(
                transaction.description
            )

            if pattern_result and pattern_result["confidence"] >= self.PATTERN_THRESHOLD:
                self.method_counts["pattern"] += 1
                self.total_cost += 0.0
                result.update({
                    "merchant": pattern_result["merchant"],
                    "category": pattern_result["category"],
                    "confidence": pattern_result["confidence"],
                    "source": "pattern_matching",
                    "cost": 0.0,
                    "method_used": "pattern_matching"
                })
                logger.debug("Pattern match", extra={"merchant": pattern_result['merchant']})
                return result

        # Step 3: Try Gemini Flash basic (CHEAP & FREE!)
        if not force_method or force_method == "llm_basic":
            llm_result = await self.gemini.enrich_basic(transaction)

            if llm_result and llm_result["confidence"] >= self.LLM_BASIC_THRESHOLD:
                self.method_counts["llm_basic"] += 1
                self.total_cost += 0.000075  # FREE tier!
                result.update({
                    "merchant": llm_result["merchant"],
                    "category": llm_result["category"],
                    "city": llm_result.get("city"),
                    "state": llm_result.get("state"),
                    "confidence": llm_result["confidence"],
                    "source": "gemini_flash",
                    "cost": 0.000075,
                    "method_used": "llm_basic"
                })
                logger.debug("Gemini Flash enrichment", extra={"merchant": llm_result['merchant']})
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

    def get_stats(self) -> Dict:
        """
        Get enrichment statistics

        Returns:
            {
                "total_cost": 0.71,
                "total_transactions": 791,
                "cost_per_transaction": 0.0009,
                "methods_used": {
                    "cache": 100,
                    "pattern": 553,
                    "llm_basic": 158,
                    "llm_search": 63,
                    "ntropy": 17
                },
                "cost_by_method": {
                    "pattern": 0.00,
                    "llm_basic": 0.04,
                    "llm_search": 0.33,
                    "ntropy": 0.34
                },
                "savings_vs_ntropy": "95%"
            }
        """
        total_transactions = sum(self.method_counts.values())
        ntropy_cost = total_transactions * 0.02
        savings_percent = 0

        if ntropy_cost > 0:
            savings_percent = ((ntropy_cost - self.total_cost) / ntropy_cost) * 100

        return {
            "total_cost": round(self.total_cost, 2),
            "total_transactions": total_transactions,
            "cost_per_transaction": round(self.total_cost / max(total_transactions, 1), 6),
            "methods_used": self.method_counts,
            "cost_by_method": {
                "pattern": 0.00,
                "llm_basic": round(self.method_counts["llm_basic"] * 0.000075, 2),
                "llm_search": round(self.method_counts["llm_search"] * 0.005075, 2),
                "ntropy": round(self.method_counts["ntropy"] * 0.02, 2)
            },
            "ntropy_cost_would_be": round(ntropy_cost, 2),
            "savings_amount": round(ntropy_cost - self.total_cost, 2),
            "savings_percent": round(savings_percent, 1)
        }

    def reset_stats(self):
        """Reset cost tracking"""
        self.total_cost = 0.0
        self.method_counts = {
            "cache": 0,
            "pattern": 0,
            "llm_basic": 0,
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
