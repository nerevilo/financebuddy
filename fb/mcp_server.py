"""MCP stdio server exposing FinanceBuddy data to Claude Code."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastmcp import FastMCP

from . import db, sync as sync_mod

mcp = FastMCP("financebuddy")


def _rows(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _decode_tags(s: Optional[str]) -> list[str]:
    if not s:
        return []
    return [t for t in s.strip(",").split(",") if t]


def _encode_tags(tags: list[str]) -> Optional[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for t in tags:
        t = t.strip()
        if not t or t in seen:
            continue
        if "," in t:
            raise ValueError(f"Tag cannot contain comma: {t!r}")
        seen.add(t)
        cleaned.append(t)
    if not cleaned:
        return None
    return "," + ",".join(cleaned) + ","


def _tx_rows(rows) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        if "tags" in d:
            d["tags"] = _decode_tags(d.get("tags"))
        out.append(d)
    return out


@mcp.tool()
def list_institutions() -> list[dict]:
    """Linked banks and when each was last synced."""
    with db.cursor() as conn:
        return _rows(
            conn.execute(
                "SELECT id, name, last_synced_at FROM institutions ORDER BY name"
            ).fetchall()
        )


@mcp.tool()
def list_accounts() -> list[dict]:
    """All connected accounts with current balances."""
    with db.cursor() as conn:
        return _rows(
            conn.execute(
                """
                SELECT a.id, a.name, a.type, a.subtype, a.last_four, a.currency,
                       a.current_balance, a.available_balance, a.balance_updated_at,
                       i.name AS institution_name
                FROM accounts a
                JOIN institutions i ON i.id = a.institution_id
                ORDER BY a.name
                """
            ).fetchall()
        )


@mcp.tool()
def get_balances() -> dict:
    """
    Net balance summary: total assets, total debt (credit cards/loans), net worth.

    Excluded transactions (see annotate_transaction) are backed out per-account:
      depository/investment: adjusted = current_balance - sum(excluded_tx.amount)
      credit/loan:           adjusted = current_balance + sum(excluded_tx.amount)
    """
    with db.cursor() as conn:
        rows = _rows(
            conn.execute(
                """
                SELECT a.id, a.name, a.type, a.current_balance,
                       COALESCE((SELECT SUM(amount) FROM transactions
                                 WHERE account_id = a.id AND excluded = 1), 0) AS excluded_sum
                FROM accounts a
                WHERE a.current_balance IS NOT NULL
                """
            ).fetchall()
        )
    for r in rows:
        sign = 1 if r["type"] in ("credit", "loan") else -1
        r["adjusted_balance"] = round(r["current_balance"] + sign * r["excluded_sum"], 2)
    assets = sum(r["adjusted_balance"] for r in rows if r["type"] in ("depository", "investment"))
    debt = sum(r["adjusted_balance"] for r in rows if r["type"] in ("credit", "loan"))
    return {
        "assets": round(assets, 2),
        "debt": round(debt, 2),
        "net": round(assets - debt, 2),
        "accounts": [
            {k: v for k, v in r.items() if k != "id"} for r in rows
        ],
    }


@mcp.tool()
def list_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[str] = None,
    merchant: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    tag: Optional[str] = None,
    include_transfers: bool = True,
    limit: int = 200,
) -> list[dict]:
    """
    Transactions matching filters. Dates are ISO (YYYY-MM-DD).
    Amount is Teller convention: negative = spend, positive = income/refund.

    `tag`: filter to txs tagged with this exact tag (see annotate_transaction).
    `include_transfers`: when False, hides internal-transfer txs (is_transfer=1).
    """
    limit = max(1, min(limit, 2000))
    sql = [
        """
        SELECT t.id, t.date, t.amount, t.description, t.merchant, t.category, t.status,
               t.note, t.excluded, t.tags, t.is_transfer,
               a.name AS account_name, a.last_four
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        WHERE 1=1
        """
    ]
    params: list = []
    if start_date:
        sql.append("AND t.date >= ?"); params.append(start_date)
    if end_date:
        sql.append("AND t.date <= ?"); params.append(end_date)
    if account_id:
        sql.append("AND t.account_id = ?"); params.append(account_id)
    if merchant:
        sql.append("AND (t.merchant LIKE ? OR t.description LIKE ?)")
        like = f"%{merchant}%"
        params.extend([like, like])
    if min_amount is not None:
        sql.append("AND t.amount >= ?"); params.append(min_amount)
    if max_amount is not None:
        sql.append("AND t.amount <= ?"); params.append(max_amount)
    if tag:
        sql.append("AND t.tags LIKE ?"); params.append(f"%,{tag},%")
    if not include_transfers:
        sql.append("AND t.is_transfer = 0")
    sql.append("ORDER BY t.date DESC, t.id DESC LIMIT ?")
    params.append(limit)
    with db.cursor() as conn:
        return _tx_rows(conn.execute(" ".join(sql), params).fetchall())


@mcp.tool()
def spending_by_category(start_date: Optional[str] = None, end_date: Optional[str] = None) -> list[dict]:
    """Spend grouped by Teller category. Defaults to last 30 days."""
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    with db.cursor() as conn:
        rows = conn.execute(
            """
            SELECT COALESCE(category, 'uncategorized') AS category,
                   SUM(amount) AS total,
                   COUNT(*) AS count
            FROM transactions
            WHERE date BETWEEN ? AND ? AND amount < 0 AND excluded = 0 AND is_transfer = 0
            GROUP BY COALESCE(category, 'uncategorized')
            ORDER BY total ASC
            """,
            (start_date, end_date),
        ).fetchall()
    return [
        {"category": r["category"], "spent": round(-r["total"], 2), "count": r["count"]}
        for r in rows
    ]


@mcp.tool()
def top_merchants(
    start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 20
) -> list[dict]:
    """Top merchants by total spend in window. Defaults to last 30 days."""
    limit = max(1, min(limit, 200))
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    with db.cursor() as conn:
        rows = conn.execute(
            """
            SELECT COALESCE(merchant, description) AS merchant,
                   SUM(amount) AS total,
                   COUNT(*) AS count
            FROM transactions
            WHERE date BETWEEN ? AND ? AND amount < 0 AND excluded = 0 AND is_transfer = 0
            GROUP BY COALESCE(merchant, description)
            ORDER BY total ASC
            LIMIT ?
            """,
            (start_date, end_date, limit),
        ).fetchall()
    return [
        {"merchant": r["merchant"], "spent": round(-r["total"], 2), "count": r["count"]}
        for r in rows
    ]


@mcp.tool()
def month_summary(year: int, month: int) -> dict:
    """Income, spend, net, and tx count for a calendar month."""
    start = date(year, month, 1).isoformat()
    next_month = date(year + (1 if month == 12 else 0), 1 if month == 12 else month + 1, 1)
    end = (next_month - timedelta(days=1)).isoformat()
    with db.cursor() as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN amount > 0 THEN amount END), 0) AS income,
                COALESCE(SUM(CASE WHEN amount < 0 THEN amount END), 0) AS spend,
                COUNT(*) AS tx_count
            FROM transactions
            WHERE date BETWEEN ? AND ? AND excluded = 0 AND is_transfer = 0
            """,
            (start, end),
        ).fetchone()
    return {
        "month": f"{year:04d}-{month:02d}",
        "start": start,
        "end": end,
        "income": round(row["income"], 2),
        "spend": round(-row["spend"], 2),
        "net": round(row["income"] + row["spend"], 2),
        "tx_count": row["tx_count"],
    }


@mcp.tool()
def sync_now(institution_id: Optional[str] = None) -> dict:
    """Pull fresh data from Teller. Omit institution_id to sync all."""
    if institution_id:
        return {"results": [sync_mod.sync_institution(institution_id)]}
    return {"results": sync_mod.sync_all()}


@mcp.tool()
def search(query: str, limit: int = 100) -> list[dict]:
    """Case-insensitive LIKE on description + merchant."""
    limit = max(1, min(limit, 500))
    like = f"%{query}%"
    with db.cursor() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.date, t.amount, t.description, t.merchant, t.category,
                   t.note, t.excluded, t.tags, t.is_transfer,
                   a.name AS account_name
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            WHERE t.description LIKE ? COLLATE NOCASE
               OR t.merchant LIKE ? COLLATE NOCASE
            ORDER BY t.date DESC
            LIMIT ?
            """,
            (like, like, limit),
        ).fetchall()
    return _tx_rows(rows)


@mcp.tool()
def annotate_transaction(
    tx_id: str,
    note: Optional[str] = None,
    excluded: Optional[bool] = None,
    tags: Optional[list[str]] = None,
    is_transfer: Optional[bool] = None,
) -> dict:
    """
    Annotate a transaction. Only fields you pass are updated.

    - `note`: free-form text. Empty string clears it.
    - `excluded`: True hides tx from month_summary / spending_by_category / top_merchants
      AND backs its amount out of get_balances. Use for bogus deposits (wrong payroll,
      duplicate, pending reversal) or spend that shouldn't count toward net worth.
      Caveat: if the bank later reverses the tx (a new offsetting tx appears), unflag
      this one — otherwise the adjustment double-counts against the real reversal.
    - `tags`: list of string tags (e.g. ["work-reimbursable", "tax-deductible"]).
      Replaces existing tags. Pass [] to clear. Tags must not contain commas.
    - `is_transfer`: True marks tx as internal transfer between your own accounts.
      Hides from income/spend aggregates but does NOT affect net worth (money just
      moved). Mark both sides of the transfer.

    Returns the updated row.
    """
    if note is None and excluded is None and tags is None and is_transfer is None:
        raise ValueError("Pass at least one field to update")
    sets: list[str] = []
    params: list = []
    if note is not None:
        sets.append("note = ?")
        params.append(note if note != "" else None)
    if excluded is not None:
        sets.append("excluded = ?")
        params.append(1 if excluded else 0)
    if tags is not None:
        sets.append("tags = ?")
        params.append(_encode_tags(tags))
    if is_transfer is not None:
        sets.append("is_transfer = ?")
        params.append(1 if is_transfer else 0)
    params.append(tx_id)
    with db.cursor() as conn:
        cur = conn.execute(
            f"UPDATE transactions SET {', '.join(sets)} WHERE id = ?", params
        )
        if cur.rowcount == 0:
            raise ValueError(f"No transaction with id {tx_id}")
        row = conn.execute(
            """
            SELECT t.id, t.date, t.amount, t.description, t.merchant, t.category,
                   t.note, t.excluded, t.tags, t.is_transfer,
                   a.name AS account_name
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            WHERE t.id = ?
            """,
            (tx_id,),
        ).fetchone()
    return _tx_rows([row])[0]


def main() -> None:
    db.init()
    mcp.run()


if __name__ == "__main__":
    main()
