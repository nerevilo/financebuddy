"""
LLM-Based Transaction Enrichment

Using smaller, cheaper LLMs for merchant recognition and categorization.

Cost Comparison:
- Ntropy: $0.020 per transaction
- GPT-4: $0.030 per transaction (expensive!)
- GPT-3.5-turbo: $0.0015 per transaction (cheap!)
- Claude Haiku: $0.00025 per transaction (cheapest!)
"""
import httpx
import json
from typing import Optional, Dict
from ..core.config import get_settings
from ..core.logging_config import get_logger
from ..models.models import Transaction

logger = get_logger(__name__)


class LLMEnrichmentService:
    """Enrich transactions using LLMs instead of Ntropy"""

    def __init__(self):
        settings = get_settings()
        self.openai_key = getattr(settings, 'openai_api_key', None)
        self.anthropic_key = getattr(settings, 'anthropic_api_key', None)

    async def enrich_with_gpt35(self, transaction: Transaction) -> Optional[Dict]:
        """
        Enrich using GPT-3.5-turbo (cheap and fast)

        Cost: ~$0.0015 per transaction
        Speed: ~1-2 seconds
        Accuracy: 85-90%
        """
        if not self.openai_key:
            return None

        prompt = f"""Analyze this bank transaction and extract information:

Transaction Description: "{transaction.description}"
Amount: ${abs(transaction.amount)}

Please identify:
1. The merchant/business name (clean, official name)
2. The business category (e.g., "fast food", "groceries", "gas stations")
3. Any location hints (city, state)
4. Your confidence level (0.0-1.0)

Respond ONLY with valid JSON (no markdown, no explanation):
{{
    "merchant": "Official Business Name",
    "category": "category name",
    "city": "city or null",
    "state": "state or null",
    "confidence": 0.0-1.0
}}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a financial transaction analyzer. Respond only with valid JSON."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 150
                    }
                )

                if response.status_code != 200:
                    logger.error("OpenAI API error", extra={"status_code": response.status_code, "response": response.text})
                    return None

                data = response.json()
                content = data["choices"][0]["message"]["content"]

                # Parse JSON response
                result = json.loads(content)

                return {
                    "merchant": result.get("merchant"),
                    "category": result.get("category"),
                    "city": result.get("city"),
                    "state": result.get("state"),
                    "confidence": result.get("confidence", 0.8),
                    "source": "gpt35",
                    "cost": 0.0015  # Approximate
                }

        except Exception as e:
            logger.error("GPT-3.5 enrichment failed", extra={"error": str(e)})
            return None

    async def enrich_with_claude_haiku(self, transaction: Transaction) -> Optional[Dict]:
        """
        Enrich using Claude Haiku (fastest and cheapest)

        Cost: ~$0.00025 per transaction (10x cheaper than GPT-3.5!)
        Speed: ~500ms
        Accuracy: 80-85%
        """
        if not self.anthropic_key:
            return None

        prompt = f"""Analyze this bank transaction and extract information:

Transaction Description: "{transaction.description}"
Amount: ${abs(transaction.amount)}

Identify:
1. Merchant/business name (clean, official name)
2. Business category (e.g., "fast food", "groceries", "gas stations")
3. Location hints (city, state if visible)
4. Confidence level (0.0-1.0)

Respond ONLY with JSON:
{{
    "merchant": "Official Name",
    "category": "category",
    "city": "city or null",
    "state": "state or null",
    "confidence": 0.0-1.0
}}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.anthropic_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 150,
                        "temperature": 0.1,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ]
                    }
                )

                if response.status_code != 200:
                    logger.error("Claude API error", extra={"status_code": response.status_code, "response": response.text})
                    return None

                data = response.json()
                content = data["content"][0]["text"]

                # Parse JSON response
                result = json.loads(content)

                return {
                    "merchant": result.get("merchant"),
                    "category": result.get("category"),
                    "city": result.get("city"),
                    "state": result.get("state"),
                    "confidence": result.get("confidence", 0.8),
                    "source": "claude_haiku",
                    "cost": 0.00025  # Actual Claude Haiku pricing
                }

        except Exception as e:
            logger.error("Claude Haiku enrichment failed", extra={"error": str(e)})
            return None


# Cost Comparison for 791 transactions:
"""
Ntropy:          791 × $0.020   = $15.82
GPT-4:           791 × $0.030   = $23.73 (worse!)
GPT-3.5:         791 × $0.0015  = $1.19  (93% cheaper!)
Claude Haiku:    791 × $0.00025 = $0.20  (99% cheaper!)

BUT: LLMs don't provide store locations like Ntropy does.

Best Hybrid:
- Pattern matching: 60% (free)
- Claude Haiku: 30% ($0.06)
- Ntropy: 10% ($1.58)
Total: $1.64 per 791 transactions (90% savings!)
"""
