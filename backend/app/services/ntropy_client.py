"""
Ntropy API Client for Transaction Enrichment

Provides merchant recognition and category detection using Ntropy's ML API.
"""
import httpx
from typing import Dict, List, Optional
from datetime import datetime
from ..core.config import get_settings
from ..models.models import Transaction


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
        self.default_account_holder_id = "fintrack-default-user"

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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/account_holders",
                    headers=self.headers,
                    json={
                        "id": account_id,
                        "type": "consumer"  # consumer or business
                    }
                )

                # 200/201 = created, 400 with "already exists" = ok, 409 = conflict
                if response.status_code in [200, 201]:
                    return True
                elif response.status_code == 400:
                    # Check if it's because account holder already exists
                    if "already exists" in response.text.lower():
                        return True
                    else:
                        print(f"Failed to create account holder: {response.status_code} - {response.text}")
                        return False
                elif response.status_code == 409:
                    return True  # Already exists
                else:
                    print(f"Failed to create account holder: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            print(f"Error creating account holder: {e}")
            return False

    async def enrich_transaction(self, transaction: Transaction) -> Optional[Dict]:
        """
        Enrich a single transaction with Ntropy.

        Args:
            transaction: Transaction object to enrich

        Returns:
            Dict with enrichment data:
            {
                "merchant": "Hardee's",
                "category": "dining",
                "location": {...},
                "confidence": 0.95
            }

            Returns None if Ntropy is disabled or API call fails.
        """
        if not self.enabled:
            return None

        try:
            # Determine entry_type (outgoing = expense/debit, incoming = income/credit)
            entry_type = "outgoing" if transaction.amount < 0 else "incoming"

            # Ensure account holder exists
            await self.create_account_holder()

            # Build payload
            payload = {
                "id": transaction.id,
                "description": transaction.description,
                "amount": abs(float(transaction.amount)),  # Ntropy expects positive amount
                "date": transaction.date.isoformat(),
                "entry_type": entry_type,
                "currency": "USD",
                "account_holder_id": self.default_account_holder_id
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/transactions",
                    headers=self.headers,
                    json=payload
                )

                if response.status_code != 200:
                    print(f"Ntropy API error: {response.status_code} - {response.text}")
                    return None

                data = response.json()

                # Extract merchant from entities.counterparty
                merchant = None
                if data.get("entities") and data["entities"].get("counterparty"):
                    merchant = data["entities"]["counterparty"].get("name")

                # Extract category from categories.general
                category = None
                if data.get("categories"):
                    category = data["categories"].get("general")

                return {
                    "merchant": merchant,
                    "category": category,
                    "location": data.get("location"),
                    "logo": data.get("entities", {}).get("counterparty", {}).get("logo"),
                    "website": data.get("entities", {}).get("counterparty", {}).get("website"),
                    "confidence": 0.9  # Ntropy doesn't return confidence, default to 0.9
                }

        except Exception as e:
            print(f"Failed to enrich transaction {transaction.id}: {e}")
            return None

    async def enrich_batch(self, transactions: List[Transaction]) -> List[Optional[Dict]]:
        """
        Enrich multiple transactions one at a time.

        Note: Ntropy API v3 doesn't support batch operations,
        so we process transactions sequentially.

        Args:
            transactions: List of Transaction objects

        Returns:
            List of enrichment dictionaries (same length as input)
            None entries where enrichment failed
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
        """
        Test the Ntropy API connection and credentials.

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Ensure account holder exists
            await self.create_account_holder()

            # Create a test transaction
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/transactions",
                    headers=self.headers,
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
            print(f"Ntropy connection test failed: {e}")
            return False
