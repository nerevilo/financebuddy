"""
Ntropy API Client for Transaction Enrichment

Provides merchant recognition and category detection using Ntropy's ML API.
"""
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from ..core.config import get_settings
from ..core.logging_config import get_logger
from ..models.models import Transaction

logger = get_logger(__name__)


class NtropyClient:
    """Client for Ntropy transaction enrichment API"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.ntropy_api_key
        self.base_url = settings.ntropy_api_url
        self.enabled = settings.use_ntropy and bool(self.api_key)

        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Default account holder ID (we'll use a consistent ID for all transactions)
        self.default_account_holder_id = "ledgi-default-user"

        # Shared HTTP client for connection reuse
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the shared HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0, headers=self.headers)
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def create_account_holder(self, account_holder_id: str = None) -> bool:
        """
        Create an account holder in Ntropy.

        Args:
            account_holder_id: ID for the account holder (uses default if None)

        Returns:
            bool: True if successful or already exists
        """
        if not self.enabled:
            return False

        account_id = account_holder_id or self.default_account_holder_id

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/account_holders",
                json={
                    "id": account_id,
                    "type": "consumer"
                }
            )

            if response.status_code in [200, 201]:
                return True
            elif response.status_code == 400:
                if "already exists" in response.text.lower():
                    return True
                else:
                    logger.error("Failed to create account holder", extra={"status_code": response.status_code, "response": response.text})
                    return False
            elif response.status_code == 409:
                return True
            else:
                logger.error("Failed to create account holder", extra={"status_code": response.status_code, "response": response.text})
                return False

        except Exception as e:
            logger.error("Error creating account holder", extra={"error": str(e)})
            return False

    async def enrich_transaction(self, transaction: Transaction) -> Optional[Dict]:
        """
        Enrich a single transaction with Ntropy.

        Returns:
            Dict with enrichment data or None if failed.
        """
        if not self.enabled:
            return None

        try:
            entry_type = "outgoing" if transaction.amount < 0 else "incoming"

            await self.create_account_holder()

            payload = {
                "id": transaction.id,
                "description": transaction.description,
                "amount": abs(float(transaction.amount)),
                "date": transaction.date.isoformat(),
                "entry_type": entry_type,
                "currency": "USD",
                "account_holder_id": self.default_account_holder_id
            }

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/transactions",
                json=payload
            )

            if response.status_code != 200:
                logger.error("Ntropy API error", extra={"status_code": response.status_code, "response": response.text})
                return None

            data = response.json()

            merchant = None
            if data.get("entities") and data["entities"].get("counterparty"):
                merchant = data["entities"]["counterparty"].get("name")

            category = None
            if data.get("categories"):
                category = data["categories"].get("general")

            return {
                "merchant": merchant,
                "category": category,
                "location": data.get("location"),
                "logo": data.get("entities", {}).get("counterparty", {}).get("logo"),
                "website": data.get("entities", {}).get("counterparty", {}).get("website"),
                "confidence": 0.9
            }

        except Exception as e:
            logger.error("Failed to enrich transaction", extra={"transaction_id": transaction.id, "error": str(e)})
            return None

    async def enrich_batch(self, transactions: List[Transaction]) -> List[Optional[Dict]]:
        """
        Enrich multiple transactions one at a time.

        Note: Ntropy API v3 doesn't support batch operations,
        so we process transactions sequentially.
        """
        if not self.enabled:
            return [None] * len(transactions)

        all_results = []

        for tx in transactions:
            result = await self.enrich_transaction(tx)
            all_results.append(result)

        return all_results

    def is_enabled(self) -> bool:
        """Check if Ntropy integration is enabled and configured."""
        return self.enabled

    async def test_connection(self) -> bool:
        """Test the Ntropy API connection and credentials."""
        if not self.enabled:
            return False

        try:
            await self.create_account_holder()

            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/transactions",
                json={
                    "id": "test-transaction-001",
                    "description": "STARBUCKS STORE 12345",
                    "amount": 10.00,
                    "date": datetime.now().isoformat(),
                    "entry_type": "outgoing",
                    "currency": "USD",
                    "account_holder_id": self.default_account_holder_id
                }
            )

            return response.status_code == 200

        except Exception as e:
            logger.error("Ntropy connection test failed", extra={"error": str(e)})
            return False
