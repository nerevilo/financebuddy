"""SQLite schema for local, single-user finance data."""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("FB_DB_PATH", PROJECT_ROOT / "financebuddy.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS institutions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    access_token TEXT NOT NULL,
    enrollment_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_synced_at TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    institution_id TEXT NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT,
    subtype TEXT,
    currency TEXT DEFAULT 'USD',
    last_four TEXT,
    current_balance REAL,
    available_balance REAL,
    balance_updated_at TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT,
    merchant TEXT,
    category TEXT,
    status TEXT,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_tx_account_date ON transactions(account_id, date);
CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_merchant ON transactions(merchant);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(transactions)")}
    if "note" not in cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN note TEXT")
    if "excluded" not in cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN excluded INTEGER NOT NULL DEFAULT 0")
    if "tags" not in cols:
        # stored as ",tag1,tag2," so that LIKE '%,X,%' matches exactly
        conn.execute("ALTER TABLE transactions ADD COLUMN tags TEXT")
    if "is_transfer" not in cols:
        conn.execute("ALTER TABLE transactions ADD COLUMN is_transfer INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS merchant_classifications (
            merchant TEXT PRIMARY KEY,
            classification TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 1.0,
            source TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mc_classification ON merchant_classifications(classification)"
    )


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()


@contextmanager
def cursor() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init()
    print(f"Initialized {DB_PATH}")
