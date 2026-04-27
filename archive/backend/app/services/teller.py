"""
Teller API Service

Handles all communication with the Teller.io API using mTLS authentication.
"""
import httpx
from typing import Optional
from datetime import date
from ..core.config import get_settings


class TellerService:
    """Service for interacting with the Teller API."""

    def __init__(self, access_token: Optional[str] = None):
        self.settings = get_settings()
        self.base_url = self.settings.teller_api_url
        self.access_token = access_token

    def _get_client(self) -> httpx.AsyncClient:
        """Create an async HTTP client with mTLS certificates."""
        return httpx.AsyncClient(
            cert=(self.settings.teller_cert_path, self.settings.teller_key_path),
            auth=(self.access_token, "") if self.access_token else None,
            timeout=30.0
        )

    # ==================== Institutions ====================

    async def get_institutions(self) -> list:
        """Get list of all supported institutions (no auth required)."""
        async with httpx.AsyncClient(
            cert=(self.settings.teller_cert_path, self.settings.teller_key_path),
            timeout=30.0
        ) as client:
            response = await client.get(f"{self.base_url}/institutions")
            response.raise_for_status()
            return response.json()

    # ==================== Accounts ====================

    async def get_accounts(self) -> list:
        """Get all accounts for the authenticated user."""
        if not self.access_token:
            raise ValueError("Access token required for this operation")

        async with self._get_client() as client:
            response = await client.get(f"{self.base_url}/accounts")
            response.raise_for_status()
            return response.json()

    async def get_account(self, account_id: str) -> dict:
        """Get a specific account by ID."""
        if not self.access_token:
            raise ValueError("Access token required for this operation")

        async with self._get_client() as client:
            response = await client.get(f"{self.base_url}/accounts/{account_id}")
            response.raise_for_status()
            return response.json()

    async def get_account_balances(self, account_id: str) -> dict:
        """Get balances for a specific account."""
        if not self.access_token:
            raise ValueError("Access token required for this operation")

        async with self._get_client() as client:
            response = await client.get(f"{self.base_url}/accounts/{account_id}/balances")
            response.raise_for_status()
            return response.json()

    # ==================== Transactions ====================

    async def get_transactions(
        self,
        account_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        count: Optional[int] = None
    ) -> list:
        """
        Get transactions for a specific account.

        Args:
            account_id: The Teller account ID
            from_date: Start date for transactions (inclusive)
            to_date: End date for transactions (inclusive)
            count: Maximum number of transactions to return
        """
        if not self.access_token:
            raise ValueError("Access token required for this operation")

        params = {}
        if from_date:
            params["from_id"] = from_date.isoformat()
        if count:
            params["count"] = count

        async with self._get_client() as client:
            response = await client.get(
                f"{self.base_url}/accounts/{account_id}/transactions",
                params=params if params else None
            )
            response.raise_for_status()
            return response.json()

    async def get_transaction_details(self, account_id: str, transaction_id: str) -> dict:
        """Get detailed information about a specific transaction."""
        if not self.access_token:
            raise ValueError("Access token required for this operation")

        async with self._get_client() as client:
            response = await client.get(
                f"{self.base_url}/accounts/{account_id}/transactions/{transaction_id}"
            )
            response.raise_for_status()
            return response.json()

    # ==================== Identity ====================

    async def get_identity(self, account_id: str) -> dict:
        """Get identity information for an account."""
        if not self.access_token:
            raise ValueError("Access token required for this operation")

        async with self._get_client() as client:
            response = await client.get(f"{self.base_url}/accounts/{account_id}/identity")
            response.raise_for_status()
            return response.json()

    # ==================== Enrollment Management ====================

    async def delete_enrollment(self) -> bool:
        """Delete/disconnect an enrollment."""
        if not self.access_token:
            raise ValueError("Access token required for this operation")

        async with self._get_client() as client:
            response = await client.delete(f"{self.base_url}/")
            return response.status_code == 204
