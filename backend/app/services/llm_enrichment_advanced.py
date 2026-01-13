"""
Advanced LLM Enrichment with Search Tools

This service uses Claude Haiku (cheapest, fastest) with the ability to
search the web when uncertain about merchant information.

Cost:
- Claude Haiku alone: $0.00025 per transaction
- Claude Haiku + Search: $0.00025 + $0.005 = $0.00525 per transaction
  (Still cheaper than Ntropy at $0.02!)

Architecture:
1. LLM analyzes transaction
2. If uncertain → calls search tool
3. Search returns results
4. LLM synthesizes final answer
"""
import json
from typing import Optional, Dict
from anthropic import AsyncAnthropic
from ..core.config import get_settings
from ..core.logging_config import get_logger
from ..models.models import Transaction
from .search_service import SearchService

logger = get_logger(__name__)


class AdvancedLLMEnrichment:
    """
    LLM enrichment with search tool capabilities

    Uses Claude Haiku for speed and cost efficiency
    """

    def __init__(self):
        settings = get_settings()
        self.anthropic_key = settings.anthropic_api_key
        self.client = None
        self.search_service = SearchService()

        if self.anthropic_key:
            self.client = AsyncAnthropic(api_key=self.anthropic_key)

    async def enrich_with_search(self, transaction: Transaction) -> Optional[Dict]:
        """
        Enrich transaction using Claude Haiku with search tools

        Process:
        1. Claude analyzes transaction description
        2. If Claude is uncertain → calls search_business tool
        3. Search returns web results
        4. Claude uses results to provide accurate answer

        Returns:
            {
                "merchant": "Hardee's",
                "category": "fast food",
                "address": "1315 Murfreesboro Rd, Franklin, TN",
                "city": "Franklin",
                "state": "TN",
                "confidence": 0.92,
                "searched": true/false,
                "search_query": "..." (if searched),
                "source": "claude_haiku_search",
                "cost": 0.00525
            }
        """
        if not self.client:
            return None

        # Define tools Claude can use
        tools = [
            {
                "name": "search_business",
                "description": "Search the web for business information, store locations, or merchant details. Use this when you need to verify a store location, find an address, or get details about a specific merchant or store number.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query (e.g., 'Hardees store 594 location', 'Dominos 4290 Blacksburg VA address')"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]

        # Initial prompt
        system_prompt = """You are a financial transaction analyzer. Extract merchant information from transaction descriptions.

You have access to a web search tool. Use it when:
- You see a store number and need to find the location
- You're unsure about a business name or details
- You need to verify merchant information

Extract:
1. Merchant name (official, clean name)
2. Business category (e.g., "fast food", "groceries", "gas stations")
3. Store location (if determinable - use search tool for store numbers)
4. Confidence level (0.0-1.0)

Respond in JSON format."""

        user_prompt = f"""Analyze this transaction:

Description: "{transaction.description}"
Amount: ${abs(transaction.amount)}

If you see a store number or location hint, use the search_business tool to find the exact address.

Return JSON:
{{
    "merchant": "Official Business Name",
    "category": "category",
    "address": "full address or null",
    "city": "city or null",
    "state": "state or null",
    "confidence": 0.0-1.0
}}"""

        try:
            # Initial API call
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                tools=tools,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system=system_prompt,
                temperature=0.1
            )

            # Check if Claude wants to use search tool
            if response.stop_reason == "tool_use":
                # Claude decided to search!
                tool_use_block = None
                for block in response.content:
                    if block.type == "tool_use":
                        tool_use_block = block
                        break

                if tool_use_block and tool_use_block.name == "search_business":
                    search_query = tool_use_block.input["query"]
                    logger.debug("Claude Haiku searching", extra={"search_query": search_query})

                    # Execute search
                    search_results = await self.search_service.search(search_query, max_results=3)

                    # Format results for Claude
                    search_summary = "\n\n".join([
                        f"Result {i+1}:\nTitle: {r['title']}\n{r['snippet']}\nSource: {r['url']}"
                        for i, r in enumerate(search_results)
                    ])

                    if not search_summary:
                        search_summary = "No search results found."

                    # Continue conversation with search results
                    response2 = await self.client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=1024,
                        messages=[
                            {"role": "user", "content": user_prompt},
                            {"role": "assistant", "content": response.content},
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": tool_use_block.id,
                                        "content": f"Search results:\n\n{search_summary}"
                                    }
                                ]
                            }
                        ],
                        system=system_prompt,
                        temperature=0.1
                    )

                    # Extract JSON from final response
                    final_text = ""
                    for block in response2.content:
                        if block.type == "text":
                            final_text = block.text
                            break

                    result = self._extract_json(final_text)
                    if result:
                        result["searched"] = True
                        result["search_query"] = search_query
                        result["source"] = "claude_haiku_search"
                        result["cost"] = 0.00525  # Haiku + search cost
                        return result

            else:
                # Claude answered directly without searching
                final_text = ""
                for block in response.content:
                    if block.type == "text":
                        final_text = block.text
                        break

                result = self._extract_json(final_text)
                if result:
                    result["searched"] = False
                    result["source"] = "claude_haiku_direct"
                    result["cost"] = 0.00025  # Haiku only
                    return result

        except Exception as e:
            logger.error("Claude Haiku with search error", extra={"error": str(e)})
            return None

        return None

    def _extract_json(self, text: str) -> Optional[Dict]:
        """
        Extract JSON from Claude's response

        Handles both pure JSON and JSON in markdown code blocks
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
enricher = AdvancedLLMEnrichment()

result = await enricher.enrich_with_search(transaction)

# For "HARDEE'S 594":
# 1. Claude sees description
# 2. Claude recognizes store number 594
# 3. Claude calls search_business("Hardees store 594 location")
# 4. Gets search results with address
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
    "source": "claude_haiku_search",
    "cost": 0.00525
}

Cost: $0.00525 per transaction (with search)
vs Ntropy: $0.02 per transaction
Savings: 74%!
"""
