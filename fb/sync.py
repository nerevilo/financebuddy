"""Pull fresh data from Teller and upsert into SQLite."""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone

import httpx

from . import db
from .teller import Teller


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _upsert_account(conn: sqlite3.Connection, institution_id: str, acc: dict, balances: dict | None) -> None:
    current = balances.get("ledger") if balances else None
    available = balances.get("available") if balances else None
    conn.execute(
        """
        INSERT INTO accounts (id, institution_id, name, type, subtype, currency, last_four,
                              current_balance, available_balance, balance_updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            type = excluded.type,
            subtype = excluded.subtype,
            currency = excluded.currency,
            last_four = excluded.last_four,
            current_balance = excluded.current_balance,
            available_balance = excluded.available_balance,
            balance_updated_at = excluded.balance_updated_at
        """,
        (
            acc["id"],
            institution_id,
            acc.get("name", "Account"),
            acc.get("type"),
            acc.get("subtype"),
            acc.get("currency", "USD"),
            acc.get("last_four"),
            float(current) if current is not None else None,
            float(available) if available is not None else None,
            _iso_now(),
        ),
    )


def _upsert_transaction(conn: sqlite3.Connection, account_id: str, tx: dict) -> None:
    details = tx.get("details") or {}
    category = details.get("category")
    counterparty = (details.get("counterparty") or {}).get("name")
    conn.execute(
        """
        INSERT INTO transactions (id, account_id, date, amount, description, merchant, category, status, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            date = excluded.date,
            amount = excluded.amount,
            description = excluded.description,
            merchant = excluded.merchant,
            category = excluded.category,
            status = excluded.status,
            raw_json = excluded.raw_json
        """,
        (
            tx["id"],
            account_id,
            tx.get("date"),
            float(tx.get("amount", 0)),
            tx.get("description"),
            counterparty,
            category,
            tx.get("status"),
            json.dumps(tx),
        ),
    )


def sync_institution(institution_id: str) -> dict:
    with db.cursor() as conn:
        row = conn.execute(
            "SELECT id, name, access_token FROM institutions WHERE id = ?",
            (institution_id,),
        ).fetchone()
    if not row:
        raise SystemExit(f"No institution with id={institution_id}")

    teller = Teller(access_token=row["access_token"])
    accounts_data = teller.accounts()
    tx_count = 0

    with db.cursor() as conn:
        for acc in accounts_data:
            try:
                balances = teller.balances(acc["id"])
            except httpx.HTTPError as e:
                print(f"  balances failed for {acc['id']}: {e}")
                balances = None
            _upsert_account(conn, institution_id, acc, balances)

            try:
                txs = teller.transactions(acc["id"])
            except httpx.HTTPError as e:
                print(f"  transactions failed for {acc['id']}: {e}")
                txs = []
            for tx in txs:
                _upsert_transaction(conn, acc["id"], tx)
            tx_count += len(txs)
            print(f"  {acc.get('name')}: {len(txs)} tx")

        conn.execute(
            "UPDATE institutions SET last_synced_at = ? WHERE id = ?",
            (_iso_now(), institution_id),
        )

    return {"institution": row["name"], "accounts": len(accounts_data), "transactions": tx_count}


def sync_all() -> list[dict]:
    db.init()
    with db.cursor() as conn:
        rows = conn.execute("SELECT id, name FROM institutions").fetchall()
    if not rows:
        print("No institutions linked. Open fb/connect.html in a browser first.")
        return []
    results = []
    for row in rows:
        print(f"Syncing {row['name']}...")
        try:
            results.append(sync_institution(row["id"]))
        except httpx.HTTPStatusError as e:
            print(f"  {row['name']} failed: {e.response.status_code} {e.response.text[:200]}")
    return results


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--institution", help="Sync only this institution id")
    args = p.parse_args()
    if args.institution:
        print(sync_institution(args.institution))
    else:
        for r in sync_all():
            print(r)


if __name__ == "__main__":
    main()
