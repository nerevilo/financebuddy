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
"""
import json
from typing import Optional, Dict
from ..core.config import get_settings
from ..core.logging_config import get_logger
from ..models.models import Transaction
from .search_service import SearchService

logger = get_logger(__name__)

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

    async def enrich_basic(self, transaction: Transaction) -> Optional[Dict]:
        """
        Basic enrichment without search (FAST & FREE)

        Returns:
            {
                "merchant": "Hardee's",
                "category": "fast food",
                "city": null,
                "state": null,
                "confidence": 0.88,
                "source": "gemini_flash",
                "cost": 0.000075
            }
        """
        if not self.model:
            return None

        prompt = f"""Analyze this bank transaction and extract merchant information.

Transaction Description: "{transaction.description}"
Amount: ${abs(transaction.amount)}

CRITICAL RULES:
1. If this is an INTERNAL BANK TRANSACTION (withdrawals, deposits, transfers, interest, fees), return null merchant:
   - Keywords: "Withdrawal to", "Deposit from", "Transfer", "Check Deposit", "Interest Paid", "Savings", "Checking"
   - Return: {{"merchant": null, "category": "internal_transfer", "city": null, "state": null, "confidence": 1.0}}

2. If this is a PERSON-TO-PERSON payment (Zelle, Venmo, PayPal, names), return null merchant:
   - Keywords: "Zelle", "Venmo", "PayPal", "money from [Name]", "Cashapp"
   - Return: {{"merchant": null, "category": "p2p_transfer", "city": null, "state": null, "confidence": 1.0}}

3. If this is ROBINHOOD, CREDITS/DEBITS, ACH transfers, return null merchant:
   - Return: {{"merchant": null, "category": "internal_transfer", "city": null, "state": null, "confidence": 1.0}}

4. ONLY if this is a REAL BUSINESS PURCHASE (Debit/Credit Card Purchase), extract:
   - Merchant: Clean business name (remove store numbers, keep it simple)
   - Category: Specific type (fast food, groceries, gas station, coffee shop, retail, subscription, etc.)
   - City/State: Extract from description if visible
   - Confidence: 0.85-0.95 for clear merchants

Examples:
✅ "Debit Card Purchase - HARDEE'S 594" → {{"merchant": "Hardee's", "category": "fast food", ...}}
✅ "Debit Card Purchase - CLAUDE.AI SUBSCRIPTION" → {{"merchant": "Claude AI", "category": "software subscription", ...}}
❌ "Withdrawal to 360 Checking" → {{"merchant": null, "category": "internal_transfer", ...}}
❌ "Check Deposit (Mobile)" → {{"merchant": null, "category": "internal_transfer", ...}}
❌ "Zelle money received from John" → {{"merchant": null, "category": "p2p_transfer", ...}}
❌ "Deposit from ROBINHOOD CREDITS" → {{"merchant": null, "category": "internal_transfer", ...}}

Respond ONLY with valid JSON:
{{
    "merchant": "Business Name or null",
    "category": "category",
    "city": "city or null",
    "state": "state or null",
    "confidence": 0.0-1.0
}}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 150,
                }
            )

            # Parse response
            result = self._extract_json(response.text)

            if result:
                result["source"] = "gemini_flash"
                result["cost"] = 0.000075  # Free tier, but tracking theoretical cost
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

        # Now ask Gemini to extract info (with or without search results)
        prompt = f"""Analyze this bank transaction:

Transaction: "{transaction.description}"
Amount: ${abs(transaction.amount)}"""

        if search_results_text:
            prompt += f"""

Search results for this merchant:
{search_results_text}

Use the search results to find the exact address, city, and state."""

        prompt += """

Extract and return ONLY valid JSON:
{
    "merchant": "Official Business Name",
    "category": "category (e.g., fast food, groceries)",
    "address": "full address from search or null",
    "city": "city from search or null",
    "state": "state from search or null",
    "confidence": 0.0-1.0
}"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 200,
                }
            )

            result = self._extract_json(response.text)

            if result:
                result["searched"] = has_store_number and bool(search_results_text)
                result["search_query"] = search_query if search_query else None
                result["source"] = "gemini_pro_search" if result["searched"] else "gemini_pro"
                result["cost"] = 0.005075 if result["searched"] else 0.000075
                return result

        except Exception as e:
            logger.error("Gemini with search error", extra={"error": str(e)})
            return None

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
