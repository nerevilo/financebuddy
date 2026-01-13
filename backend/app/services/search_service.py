"""
Web Search Service for Transaction Enrichment

Provides search capabilities for LLMs to look up business information.

Supported search engines:
1. Tavily API (best for AI agents) - 1,000 free searches/month
2. DuckDuckGo (free, no API key needed) - fallback

Cost:
- Tavily: $0.005 per search (after free tier)
- DuckDuckGo: FREE (unlimited)
"""
import httpx
from typing import List, Dict, Optional
from ..core.config import get_settings
from ..core.logging_config import get_logger

logger = get_logger(__name__)


class SearchService:
    """
    Web search service for AI agents

    Automatically uses best available search engine:
    - Tavily (if API key configured) - best results
    - DuckDuckGo (always available) - fallback
    """

    def __init__(self):
        settings = get_settings()
        self.tavily_key = settings.tavily_api_key

    async def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Search the web for information

        Args:
            query: Search query (e.g., "Hardees store 594 location")
            max_results: Maximum number of results to return

        Returns:
            List of search results with title, snippet, url
        """
        # Try Tavily first (best for AI)
        if self.tavily_key:
            results = await self._search_tavily(query, max_results)
            if results:
                return results

        # Fallback to DuckDuckGo (free)
        return await self._search_duckduckgo(query, max_results)

    async def _search_tavily(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Search using Tavily API (AI-optimized search)

        Best results for AI agents - returns clean, structured data
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    headers={
                        "Content-Type": "application/json"
                    },
                    json={
                        "api_key": self.tavily_key,
                        "query": query,
                        "search_depth": "basic",  # or "advanced" for more thorough
                        "max_results": max_results,
                        "include_answer": True,  # Get AI-generated answer
                        "include_raw_content": False  # Don't need full page content
                    }
                )

                if response.status_code == 200:
                    data = response.json()

                    results = []

                    # Add AI-generated answer if available
                    if data.get("answer"):
                        results.append({
                            "title": "AI Summary",
                            "snippet": data["answer"],
                            "url": "",
                            "source": "tavily_ai"
                        })

                    # Add search results
                    for result in data.get("results", [])[:max_results]:
                        results.append({
                            "title": result.get("title", ""),
                            "snippet": result.get("content", ""),
                            "url": result.get("url", ""),
                            "source": "tavily"
                        })

                    return results
                else:
                    logger.error("Tavily API error", extra={"status_code": response.status_code})
                    return []

        except Exception as e:
            logger.error("Tavily search error", extra={"error": str(e)})
            return []

    async def _search_duckduckgo(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Search using DuckDuckGo Instant Answer API (FREE)

        Note: This is the instant answer API, not full web search.
        Returns structured data when available.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": 1,
                        "skip_disambig": 1
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    results = []

                    # Get instant answer if available
                    if data.get("AbstractText"):
                        results.append({
                            "title": data.get("Heading", ""),
                            "snippet": data.get("AbstractText", ""),
                            "url": data.get("AbstractURL", ""),
                            "source": "duckduckgo"
                        })

                    # Get related topics
                    for topic in data.get("RelatedTopics", [])[:max_results]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results.append({
                                "title": topic.get("FirstURL", "").split("/")[-1],
                                "snippet": topic.get("Text", ""),
                                "url": topic.get("FirstURL", ""),
                                "source": "duckduckgo"
                            })

                    return results[:max_results]

        except Exception as e:
            logger.error("DuckDuckGo search error", extra={"error": str(e)})
            return []

        return []

    async def search_business_location(self, merchant: str, store_number: str = None) -> Optional[Dict]:
        """
        Specialized search for business locations

        Args:
            merchant: Business name (e.g., "Hardees")
            store_number: Store number if available (e.g., "594")

        Returns:
            Search results focused on location information
        """
        if store_number:
            query = f"{merchant} store {store_number} location address"
        else:
            query = f"{merchant} location address"

        results = await self.search(query, max_results=5)

        if not results:
            return None

        # Combine all snippets
        combined_info = "\n\n".join([
            f"Source: {r['title']}\n{r['snippet']}"
            for r in results
        ])

        return {
            "query": query,
            "results": results,
            "combined_text": combined_info
        }


# Example usage:
"""
search_service = SearchService()

# Basic search
results = await search_service.search("Hardees store 594 location")
# Returns:
# [
#     {
#         "title": "Hardee's #594",
#         "snippet": "1315 Murfreesboro Rd, Franklin, TN 37064",
#         "url": "https://...",
#         "source": "tavily" or "duckduckgo"
#     }
# ]

# Specialized business location search
location_info = await search_service.search_business_location("Hardees", "594")
# Returns combined search results focused on location
"""
