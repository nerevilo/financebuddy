"""
Gemini-Based Transaction Enrichment with Search Tools

Uses Google Gemini Flash (FREE tier - 1,500 requests/day!)

Cost:
- Gemini Flash alone: $0.000075 per transaction (FREE tier!)
- Gemini Flash + Search: $0.000075 + $0.005 = $0.005075 per transaction

Benefits:
- FREE for up to 1,500 requests/day
- 3x cheaper than Claude Haiku after free tier
- Excellent structured output
- Function calling for search tools
- Fast (~300-500ms)
- LLM response caching (7 days) for repeated merchant patterns
"""
import asyncio
import json
from typing import Optional, Dict, List
from ..core.config import get_settings
from ..core.logging_config import get_logger
from ..core.cache import get_cache, EnrichmentCacheKeys, CacheTTL
from ..models.models import Transaction
from .search_service import SearchService
from .categories import normalize_category_id

logger = get_logger(__name__)

# Standard categories for LLM prompt
STANDARD_CATEGORIES_PROMPT = """
VALID CATEGORIES (you MUST use one of these exact values):
- groceries: Grocery stores, supermarkets, Costco/Walmart for food
- fast_food: Quick service restaurants, burger joints, pizza delivery
- restaurants: Sit-down dining, casual/fine dining, bars
- coffee_shops: Coffee shops, cafes, Starbucks, Dunkin
- gas_stations: Gas stations, fuel, Costco Gas, EV charging
- parking: Parking lots, garages, meters
- public_transit: Subway, bus, metro, train
- rideshare: Uber, Lyft, taxi
- auto: Car maintenance, repairs, oil change, car wash
- shopping: General retail, Amazon, department stores
- electronics: Electronics stores, Best Buy, Apple Store
- clothing: Clothing stores, fashion, shoes
- home_improvement: Hardware stores, Home Depot, Lowe's
- utilities: Electric, water, gas utilities
- phone_internet: Mobile phone, internet, cable (Verizon, AT&T)
- insurance: Car/health/home insurance
- software_subscriptions: Software, SaaS, Claude, OpenAI, GitHub, Cursor, Notion
- streaming: Netflix, Spotify, Disney+, Hulu, YouTube Premium
- gaming: Video games, Steam, PlayStation, Xbox
- healthcare: Doctor, hospital, medical services
- pharmacy: CVS, Walgreens, prescriptions
- fitness: Gym membership, fitness classes
- personal_care: Haircut, salon, spa
- entertainment: Movies, concerts, events
- travel: Flights, hotels, Airbnb
- education: Tuition, courses, books
- fees_charges: Bank fees, ATM fees, service charges
- internal_transfer: Transfers between own accounts
- external_transfer: Zelle, Venmo, PayPal transfers
- credit_card_payment: Credit card bill payment
- income: Salary, paycheck, refunds
- other: Uncategorized
"""

# Optional import - only needed if using Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class GeminiEnrichment:
    """
    Gemini enrichment with search tool capabilities

    Uses Gemini 1.5 Flash for speed and cost efficiency
    FREE tier: 1,500 requests/day!
    """

    def __init__(self):
        settings = get_settings()
        self.gemini_key = settings.gemini_api_key
        self.search_service = SearchService()
        self.model = None

        if self.gemini_key and GEMINI_AVAILABLE:
            genai.configure(api_key=self.gemini_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')  # Latest Flash model (FREE!)
        elif self.gemini_key and not GEMINI_AVAILABLE:
            logger.warning("Gemini API key provided but google-generativeai package not installed. Run: pip install google-generativeai")

    async def enrich_basic(
        self,
        transaction: Transaction,
        hint: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Basic enrichment without search (FAST & FREE)

        Args:
            transaction: Transaction to enrich
            hint: Optional hint from semantic matching with suggested merchant/category

        Returns:
            {
                "merchant": "Hardee's",
                "category": "fast_food",
                "city": null,
                "state": null,
                "confidence": 0.88,
                "source": "gemini_flash",
                "cost": 0.000075
            }
        """
        if not self.model:
            return None

        # Check cache first (skip if we have a hint - means we want fresh LLM opinion)
        cache = get_cache()
        cache_key = EnrichmentCacheKeys.gemini_result(transaction.description)

        if not hint:  # Only use cache if no hint (fresh query)
            cached_result = await cache.get(cache_key)
            if cached_result:
                cached_result["source"] = "gemini_flash_cached"
                cached_result["cost"] = 0.0  # Free from cache
                cached_result["cached"] = True
                logger.debug("Cache hit for enrichment", extra={
                    "description": transaction.description[:50],
                    "merchant": cached_result.get("merchant")
                })
                return cached_result

        # Build hint text if provided
        hint_text = ""
        if hint:
            hint_text = f"""
HINT FROM PATTERN MATCHING (verify or correct this):
- Suggested merchant: {hint.get('suggested_merchant', 'unknown')}
- Suggested category: {hint.get('suggested_category', 'unknown')}
- Confidence: {hint.get('confidence', 0):.0%}
Use this as a starting point but make your own determination based on the transaction description.
"""

        # Sanitize description for LLM prompt
        safe_desc = transaction.description[:200].replace('"', '').replace("'", "")

        prompt = f"""Analyze this bank transaction and extract merchant information.

<transaction_description>{safe_desc}</transaction_description>
Amount: ${abs(transaction.amount)}
{hint_text}
{STANDARD_CATEGORIES_PROMPT}

CRITICAL RULES:
1. If this is an INTERNAL BANK TRANSACTION (withdrawals, deposits, transfers, interest, fees), return null merchant:
   - Keywords: "Withdrawal to", "Deposit from", "Transfer", "Check Deposit", "Interest Paid", "Savings", "Checking"
   - Return: {{"merchant": null, "category": "internal_transfer", "city": null, "state": null, "confidence": 1.0}}

2. If this is a PERSON-TO-PERSON payment (Zelle, Venmo, PayPal, names), return null merchant:
   - Keywords: "Zelle", "Venmo", "PayPal", "money from [Name]", "Cashapp"
   - Return: {{"merchant": null, "category": "external_transfer", "city": null, "state": null, "confidence": 1.0}}

3. If this is ROBINHOOD, CREDITS/DEBITS, ACH transfers, return null merchant:
   - Return: {{"merchant": null, "category": "internal_transfer", "city": null, "state": null, "confidence": 1.0}}

4. IMPORTANT GAS STATION DETECTION:
   - "COSTCO GAS", "COSTCO GASOLINE", "COSTCO FUEL" → category: "gas_stations" (NOT groceries!)
   - "SAMS CLUB GAS", "WALMART GAS", "KROGER FUEL" → category: "gas_stations"
   - Any transaction with "GAS", "FUEL", "GASOLINE" at a retail store → "gas_stations"

5. SOFTWARE/TECH SUBSCRIPTIONS:
   - Claude, Anthropic, OpenAI, ChatGPT, Cursor, GitHub, Notion, Figma → "software_subscriptions"
   - NOT "television" or "streaming" - these are developer/productivity tools

6. ONLY if this is a REAL BUSINESS PURCHASE (Debit/Credit Card Purchase), extract:
   - Merchant: Clean business name (remove store numbers, keep it simple)
   - Category: Use ONLY from the valid categories list above
   - City/State: Extract from description if visible
   - Confidence: 0.85-0.95 for clear merchants

Examples:
✅ "Debit Card Purchase - HARDEE'S 594" → {{"merchant": "Hardee's", "category": "fast_food", ...}}
✅ "Debit Card Purchase - COSTCO GAS" → {{"merchant": "Costco Gas", "category": "gas_stations", ...}}
✅ "Debit Card Purchase - COSTCO WHSE" → {{"merchant": "Costco", "category": "groceries", ...}}
✅ "CLAUDE.AI SUBSCRIPTION" → {{"merchant": "Claude", "category": "software_subscriptions", ...}}
✅ "ANTHROPIC" → {{"merchant": "Anthropic", "category": "software_subscriptions", ...}}
✅ "OPENAI" → {{"merchant": "OpenAI", "category": "software_subscriptions", ...}}
✅ "NETFLIX.COM" → {{"merchant": "Netflix", "category": "streaming", ...}}
❌ "Withdrawal to 360 Checking" → {{"merchant": null, "category": "internal_transfer", ...}}
❌ "Check Deposit (Mobile)" → {{"merchant": null, "category": "internal_transfer", ...}}
❌ "Zelle money received from John" → {{"merchant": null, "category": "external_transfer", ...}}

Respond ONLY with valid JSON:
{{
    "merchant": "Business Name or null",
    "category": "category_id from list above",
    "city": "city or null",
    "state": "state or null",
    "confidence": 0.0-1.0
}}"""

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 150,
                    }
                ),
                timeout=30
            )

            # Parse response
            result = self._extract_json(response.text)

            if result:
                # Normalize category to standard taxonomy
                if result.get("category"):
                    result["category"] = normalize_category_id(result["category"])
                result["source"] = "gemini_flash"
                result["cost"] = 0.000075  # Free tier, but tracking theoretical cost
                result["cached"] = False

                # Cache the result for future use (7 days)
                await cache.set(cache_key, result, ttl=CacheTTL.LLM_ENRICHMENT)
                logger.debug("Cached enrichment result", extra={
                    "description": transaction.description[:50],
                    "merchant": result.get("merchant")
                })

                return result

        except Exception as e:
            logger.error("Gemini basic enrichment error", extra={"error": str(e)})
            return None

        return None

    async def enrich_with_search(self, transaction: Transaction) -> Optional[Dict]:
        """
        Enrichment with search tools (when store numbers or locations needed)

        Process:
        1. Gemini analyzes transaction
        2. If uncertain → searches web
        3. Extracts data from search results
        4. Returns structured answer

        Returns:
            {
                "merchant": "Hardee's",
                "category": "fast food",
                "address": "1315 Murfreesboro Rd, Franklin, TN",
                "city": "Franklin",
                "state": "TN",
                "confidence": 0.92,
                "searched": true,
                "search_query": "Hardees store 594 location",
                "source": "gemini_flash_search",
                "cost": 0.005075
            }
        """
        if not self.model:
            return None

        # Check cache first
        cache = get_cache()
        cache_key = EnrichmentCacheKeys.gemini_result(transaction.description) + ":search"

        cached_result = await cache.get(cache_key)
        if cached_result:
            cached_result["source"] = "gemini_flash_search_cached"
            cached_result["cost"] = 0.0  # Free from cache
            cached_result["cached"] = True
            logger.debug("Cache hit for search enrichment", extra={
                "description": transaction.description[:50],
                "merchant": cached_result.get("merchant")
            })
            return cached_result

        # Two-step approach: Always search for store numbers
        # Step 1: Detect if there's a store number
        # Step 2: Search and extract

        # Check if description has a store number pattern
        import re
        has_store_number = bool(re.search(r'\d{3,5}', transaction.description))

        search_query = None
        search_results_text = ""

        if has_store_number:
            # Extract business name and store number
            words = transaction.description.upper().split()
            merchant_name = words[0] if words else ""

            # Create search query
            search_query = f"{merchant_name} store location address"
            logger.debug("Searching for business location", extra={"search_query": search_query})

            # Execute search
            search_results = await self.search_service.search(search_query, max_results=3)

            if search_results:
                search_results_text = "\n\n".join([
                    f"Result {i+1}:\n{r['title']}\n{r['snippet']}"
                    for i, r in enumerate(search_results[:3])
                ])

        # Sanitize description for LLM prompt
        safe_desc = transaction.description[:200].replace('"', '').replace("'", "")

        # Now ask Gemini to extract info (with or without search results)
        prompt = f"""Analyze this bank transaction:

<transaction_description>{safe_desc}</transaction_description>
Amount: ${abs(transaction.amount)}"""

        if search_results_text:
            prompt += f"""

Search results for this merchant:
{search_results_text}

Use the search results to find the exact address, city, and state."""

        prompt += f"""

{STANDARD_CATEGORIES_PROMPT}

IMPORTANT: Use the exact category_id from the list above. Examples:
- "COSTCO GAS" → "gas_stations" (NOT groceries)
- "CLAUDE.AI" → "software_subscriptions" (NOT television)
- "NETFLIX" → "streaming"

Extract and return ONLY valid JSON:
{{
    "merchant": "Official Business Name",
    "category": "category_id from list above",
    "address": "full address from search or null",
    "city": "city from search or null",
    "state": "state from search or null",
    "confidence": 0.0-1.0
}}"""

        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 200,
                    }
                ),
                timeout=30
            )

            result = self._extract_json(response.text)

            if result:
                # Normalize category to standard taxonomy
                if result.get("category"):
                    result["category"] = normalize_category_id(result["category"])
                result["searched"] = has_store_number and bool(search_results_text)
                result["search_query"] = search_query if search_query else None
                result["source"] = "gemini_flash_search" if result["searched"] else "gemini_flash"
                result["cost"] = 0.005075 if result["searched"] else 0.000075
                result["cached"] = False

                # Cache the result for future use (7 days)
                await cache.set(cache_key, result, ttl=CacheTTL.LLM_ENRICHMENT)
                logger.debug("Cached search enrichment result", extra={
                    "description": transaction.description[:50],
                    "merchant": result.get("merchant")
                })

                return result

        except Exception as e:
            logger.error("Gemini with search error", extra={"error": str(e)})
            return None

        return None

    async def enrich_batch(
        self,
        transactions: List[Transaction],
        batch_size: int = 8
    ) -> List[Optional[Dict]]:
        """
        Batch enrichment - process multiple transactions in a single LLM call.

        This reduces API calls by 5-10x while staying within rate limits.

        Args:
            transactions: List of transactions to enrich
            batch_size: Number of transactions per API call (default: 8)

        Returns:
            List of enrichment results (same order as input transactions)
            Each result is either a dict or None if enrichment failed
        """
        if not self.model or not transactions:
            return [None] * len(transactions)

        cache = get_cache()
        results: List[Optional[Dict]] = [None] * len(transactions)
        uncached_indices: List[int] = []
        uncached_transactions: List[Transaction] = []

        # Step 1: Check cache for each transaction
        for i, tx in enumerate(transactions):
            cache_key = EnrichmentCacheKeys.gemini_result(tx.description)
            cached_result = await cache.get(cache_key)
            if cached_result:
                cached_result["source"] = "gemini_flash_cached"
                cached_result["cost"] = 0.0
                cached_result["cached"] = True
                results[i] = cached_result
                logger.debug("Batch cache hit", extra={"description": tx.description[:30]})
            else:
                uncached_indices.append(i)
                uncached_transactions.append(tx)

        if not uncached_transactions:
            logger.info("Batch enrichment: all from cache", extra={"count": len(transactions)})
            return results

        # Step 2: Process uncached transactions in batches
        for batch_start in range(0, len(uncached_transactions), batch_size):
            batch_end = min(batch_start + batch_size, len(uncached_transactions))
            batch_txns = uncached_transactions[batch_start:batch_end]
            batch_indices = uncached_indices[batch_start:batch_end]

            # Build batch prompt (sanitize descriptions)
            tx_list = "\n".join([
                f'{i+1}. <transaction_description>{tx.description[:200].replace(chr(34), "").replace(chr(39), "")}</transaction_description> - ${abs(tx.amount):.2f}'
                for i, tx in enumerate(batch_txns)
            ])

            prompt = f"""Analyze these bank transactions and extract merchant information for EACH one.

TRANSACTIONS:
{tx_list}

{STANDARD_CATEGORIES_PROMPT}

RULES:
1. Internal bank transactions (transfers, deposits, withdrawals) → merchant: null, category: "internal_transfer"
2. P2P payments (Zelle, Venmo, PayPal) → merchant: null, category: "external_transfer"
3. Gas at retail stores (COSTCO GAS, WALMART FUEL) → category: "gas_stations" (NOT groceries)
4. Software/AI tools (Claude, OpenAI, GitHub, Cursor) → category: "software_subscriptions"
5. For real purchases, extract clean merchant name and appropriate category

Return a JSON ARRAY with exactly {len(batch_txns)} objects, one for each transaction in order:
[
  {{"merchant": "Name or null", "category": "category_id", "confidence": 0.0-1.0}},
  {{"merchant": "Name or null", "category": "category_id", "confidence": 0.0-1.0}},
  ...
]

IMPORTANT: Return ONLY the JSON array, no other text."""

            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.model.generate_content,
                        prompt,
                        generation_config={
                            "temperature": 0.1,
                            "max_output_tokens": 100 * len(batch_txns),
                        }
                    ),
                    timeout=30
                )

                batch_results = self._extract_json_array(response.text)

                if batch_results and len(batch_results) == len(batch_txns):
                    # Successfully parsed batch response
                    for j, (idx, tx, result) in enumerate(zip(batch_indices, batch_txns, batch_results)):
                        if result and isinstance(result, dict):
                            if result.get("category"):
                                result["category"] = normalize_category_id(result["category"])
                            result["source"] = "gemini_flash_batch"
                            result["cost"] = 0.000075 / len(batch_txns)  # Split cost across batch
                            result["cached"] = False
                            results[idx] = result

                            # Cache individual result
                            cache_key = EnrichmentCacheKeys.gemini_result(tx.description)
                            await cache.set(cache_key, result, ttl=CacheTTL.LLM_ENRICHMENT)

                    logger.info("Batch enrichment success", extra={
                        "batch_size": len(batch_txns),
                        "successful": sum(1 for r in batch_results if r)
                    })
                else:
                    # Batch parsing failed, fall back to individual calls
                    logger.warning("Batch parse failed, falling back to individual", extra={
                        "expected": len(batch_txns),
                        "got": len(batch_results) if batch_results else 0
                    })
                    for idx, tx in zip(batch_indices, batch_txns):
                        individual_result = await self.enrich_basic(tx)
                        results[idx] = individual_result

            except Exception as e:
                logger.error("Batch enrichment error", extra={"error": str(e)})
                # Fall back to individual calls for this batch
                for idx, tx in zip(batch_indices, batch_txns):
                    try:
                        individual_result = await self.enrich_basic(tx)
                        results[idx] = individual_result
                    except Exception as inner_e:
                        logger.error("Individual fallback failed", extra={"error": str(inner_e)})
                        results[idx] = None

        return results

    def _extract_json_array(self, text: str) -> Optional[List[Dict]]:
        """
        Extract JSON array from Gemini's response.

        Handles:
        - Pure JSON array
        - JSON array in markdown code blocks
        - JSON array with surrounding text
        """
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except:
            pass

        # Try extracting from code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    parsed = json.loads(text[start:end].strip())
                    if isinstance(parsed, list):
                        return parsed
                except:
                    pass

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                try:
                    parsed = json.loads(text[start:end].strip())
                    if isinstance(parsed, list):
                        return parsed
                except:
                    pass

        # Try extracting from [ to ]
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start:end])
                if isinstance(parsed, list):
                    return parsed
            except:
                pass

        return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """
        Extract JSON from Gemini's response

        Handles:
        - Pure JSON
        - JSON in markdown code blocks
        - JSON with explanation text
        """
        try:
            # Try parsing as-is
            return json.loads(text)
        except:
            pass

        # Try extracting from code block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except:
                    pass

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                try:
                    return json.loads(text[start:end].strip())
                except:
                    pass

        # Try extracting from { to }
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass

        return None


# Example usage:
"""
enricher = GeminiEnrichment()

# Basic enrichment (FREE!)
result = await enricher.enrich_basic(transaction)

# With search (when needed)
result = await enricher.enrich_with_search(transaction)

# For "HARDEE'S 594":
# 1. Gemini sees description
# 2. Gemini recognizes store number 594
# 3. Gemini calls search_business("Hardees store 594 location")
# 4. Gets Tavily search results with address
# 5. Extracts information
# 6. Returns complete data

Result:
{
    "merchant": "Hardee's",
    "category": "fast food",
    "address": "1315 Murfreesboro Rd, Franklin, TN 37064",
    "city": "Franklin",
    "state": "TN",
    "confidence": 0.92,
    "searched": true,
    "search_query": "Hardees store 594 location",
    "source": "gemini_flash_search",
    "cost": 0.005075
}

Cost: FREE for first 1,500/day!
Then: $0.005075 per transaction (with search)
vs Ntropy: $0.02 per transaction
Savings: 75%!
"""
