"""Teller API client (mTLS)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TELLER_ENV = os.environ.get("TELLER_ENV", "sandbox")
TELLER_CERT_PATH = Path(
    os.environ.get("TELLER_CERT_PATH", PROJECT_ROOT / "backend" / "certificate.pem")
)
TELLER_KEY_PATH = Path(
    os.environ.get("TELLER_KEY_PATH", PROJECT_ROOT / "backend" / "private_key.pem")
)
TELLER_API_URL = "https://api.teller.io"


class Teller:
    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("access_token required")
        if not TELLER_CERT_PATH.exists() or not TELLER_KEY_PATH.exists():
            raise FileNotFoundError(
                f"Teller certs missing: {TELLER_CERT_PATH} / {TELLER_KEY_PATH}"
            )
        self.access_token = access_token

    def _client(self) -> httpx.Client:
        return httpx.Client(
            cert=(str(TELLER_CERT_PATH), str(TELLER_KEY_PATH)),
            auth=(self.access_token, ""),
            timeout=30.0,
            base_url=TELLER_API_URL,
        )

    def accounts(self) -> list[dict]:
        with self._client() as c:
            r = c.get("/accounts")
            r.raise_for_status()
            return r.json()

    def balances(self, account_id: str) -> dict:
        with self._client() as c:
            r = c.get(f"/accounts/{account_id}/balances")
            r.raise_for_status()
            return r.json()

    def transactions(self, account_id: str, count: Optional[int] = None) -> list[dict]:
        with self._client() as c:
            params = {"count": count} if count else None
            r = c.get(f"/accounts/{account_id}/transactions", params=params)
            r.raise_for_status()
            return r.json()
