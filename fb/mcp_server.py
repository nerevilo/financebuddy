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


# Transactions that look like internal transfers even when is_transfer isn't set:
# credit-card payments (AUTOPAY, ONLINE PAYMENT, etc.) and merchants that are
# bank/card issuer names. Mirrors the heuristics in the fb-transfers skill so
# that aggregates (spend baseline, runway, outliers) don't count these as spend.
_HC_TRANSFERISH = """
  AND is_transfer = 0 AND excluded = 0
  AND COALESCE(category, '') NOT IN ('transfer', 'investment')
  AND UPPER(COALESCE(description, '')) NOT LIKE '%AUTOPAY%'
  AND UPPER(COALESCE(description, '')) NOT LIKE '%AUTO-PMT%'
  AND UPPER(COALESCE(description, '')) NOT LIKE '%AUTOMATIC PAYMENT%'
  AND UPPER(COALESCE(description, '')) NOT LIKE '%ONLINE PAYMENT%'
  AND UPPER(COALESCE(description, '')) NOT LIKE '%MOBILE PAYMENT%'
  AND UPPER(COALESCE(description, '')) NOT LIKE '%CC PAYMENT%'
  AND UPPER(COALESCE(description, '')) NOT LIKE '%PAYMENT THANK YOU%'
  -- Capital One self-transfer pattern: "Withdrawal to <name> XXXXXXXnnnn"
  AND UPPER(COALESCE(description, '')) NOT LIKE 'WITHDRAWAL TO %XXXXXXX%'
  -- PayPal / Zelle instant transfers are typically self-moves
  AND UPPER(COALESCE(description, '')) NOT LIKE '%INST XFER%'
  AND UPPER(COALESCE(description, '')) NOT LIKE '%PAYPAL%INST%'
  AND UPPER(COALESCE(merchant, '')) NOT IN (
        'CITI', 'CITIBANK', 'CHASE', 'JPMORGAN CHASE',
        'AMEX', 'AMERICAN EXPRESS', 'CAPITAL ONE', 'CAPITALONE',
        'DISCOVER', 'BARCLAYCARD', 'BARCLAYS', 'WELLS FARGO',
        'BANK OF AMERICA', 'BOFA', 'US BANK', 'USAA',
        'ROBINHOOD', 'MSPBNA', 'FIDELITY', 'VANGUARD', 'SCHWAB',
        'MORGAN STANLEY', 'E*TRADE', 'ETRADE'
  )
"""


def _hc_subscriptions(conn, lookback_start: str, today: str, current_start: str) -> list[dict]:
    # Recurring charges: a merchant seen in ≥3 distinct calendar months. We no
    # longer require tight amount spread — variable subscriptions (overage
    # billing, annual-vs-monthly plans) are still useful to surface. The
    # `amount_stable` flag distinguishes fixed-price subs from variable ones.
    rows = conn.execute(
        f"""
        SELECT merchant,
               COUNT(*) AS tx_count,
               COUNT(DISTINCT strftime('%Y-%m', date)) AS months_seen,
               AVG(-amount) AS avg_amount,
               MIN(-amount) AS min_amount,
               MAX(-amount) AS max_amount,
               MIN(date) AS first_seen,
               MAX(date) AS last_seen
        FROM transactions
        WHERE amount < 0
          {_HC_TRANSFERISH}
          AND date >= ? AND date <= ?
          AND merchant IS NOT NULL AND merchant != ''
        GROUP BY merchant
        HAVING months_seen >= 3
           AND avg_amount >= 5
           AND tx_count >= months_seen
        ORDER BY avg_amount DESC
        """,
        (lookback_start, today),
    ).fetchall()

    out = []
    for r in rows:
        split = conn.execute(
            f"""
            SELECT AVG(CASE WHEN date >= ? THEN -amount END) AS cur_avg,
                   AVG(CASE WHEN date <  ? THEN -amount END) AS prior_avg
            FROM transactions
            WHERE merchant = ? AND amount < 0
              {_HC_TRANSFERISH}
              AND date >= ? AND date <= ?
            """,
            (current_start, current_start, r["merchant"], lookback_start, today),
        ).fetchone()
        change_pct = None
        if split["cur_avg"] is not None and split["prior_avg"]:
            change_pct = round((split["cur_avg"] - split["prior_avg"]) / split["prior_avg"] * 100, 1)
        spread = (r["max_amount"] - r["min_amount"]) / r["avg_amount"] if r["avg_amount"] else 0
        out.append({
            "merchant": r["merchant"],
            "avg_amount": round(r["avg_amount"], 2),
            "min_amount": round(r["min_amount"], 2),
            "max_amount": round(r["max_amount"], 2),
            "months_seen": r["months_seen"],
            "tx_count": r["tx_count"],
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
            "new": r["first_seen"] >= current_start,
            "amount_stable": spread <= 0.25,
            "amount_change_pct": change_pct,
        })
    return out


def _hc_category_trends(conn, prior_start: str, current_start: str, current_end: str) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT COALESCE(category, 'uncategorized') AS category,
               SUM(CASE WHEN date >= ? THEN -amount ELSE 0 END) AS cur_total,
               SUM(CASE WHEN date <  ? THEN -amount ELSE 0 END) AS prior_total
        FROM transactions
        WHERE amount < 0
          {_HC_TRANSFERISH}
          AND date >= ? AND date <= ?
        GROUP BY COALESCE(category, 'uncategorized')
        """,
        (current_start, current_start, prior_start, current_end),
    ).fetchall()

    out = []
    for r in rows:
        cur = round(r["cur_total"] or 0, 2)
        prior = round(r["prior_total"] or 0, 2)
        abs_change = round(cur - prior, 2)
        if prior > 0:
            pct = round((cur - prior) / prior * 100, 1)
        elif cur > 0:
            pct = None  # undefined — flag via "new_category" instead
        else:
            pct = 0.0
        out.append({
            "category": r["category"],
            "current": cur,
            "prior": prior,
            "abs_change": abs_change,
            "pct_change": pct,
            "new_category": prior == 0 and cur > 0,
        })
    out.sort(key=lambda x: abs(x["abs_change"]), reverse=True)
    return out


def _hc_outliers(conn, lookback_start: str, current_start: str, current_end: str) -> list[dict]:
    # Build the outlier query: inline the transfer-ish filter in the baseline CTE
    # and again in the outer tx scan. Aliased for the outer `t.*` references.
    t_filter = _HC_TRANSFERISH.replace(" is_transfer ", " t.is_transfer ") \
                              .replace(" excluded ", " t.excluded ") \
                              .replace("COALESCE(category", "COALESCE(t.category") \
                              .replace("COALESCE(description", "COALESCE(t.description") \
                              .replace("COALESCE(merchant", "COALESCE(t.merchant")
    rows = conn.execute(
        f"""
        WITH baseline AS (
            SELECT merchant, AVG(-amount) AS avg_spend, COUNT(*) AS n
            FROM transactions
            WHERE amount < 0
              {_HC_TRANSFERISH}
              AND date >= ? AND date < ?
              AND merchant IS NOT NULL AND merchant != ''
            GROUP BY merchant
            HAVING n >= 2
        )
        SELECT t.id, t.date, t.merchant, t.category,
               -t.amount AS amount,
               b.avg_spend,
               ROUND(-t.amount / b.avg_spend, 2) AS ratio
        FROM transactions t
        JOIN baseline b ON b.merchant = t.merchant
        WHERE t.amount < 0
          {t_filter}
          AND t.date >= ? AND t.date <= ?
          AND -t.amount >= 20
          AND -t.amount > b.avg_spend * 2
        ORDER BY ratio DESC
        LIMIT 20
        """,
        (lookback_start, current_start, current_start, current_end),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "date": r["date"],
            "merchant": r["merchant"],
            "category": r["category"],
            "amount": round(r["amount"], 2),
            "typical": round(r["avg_spend"], 2),
            "ratio": r["ratio"],
        }
        for r in rows
    ]


def _hc_new_merchants(conn, lookback_start: str, current_start: str, current_end: str) -> list[dict]:
    rows = conn.execute(
        f"""
        SELECT merchant,
               MIN(date) AS first_seen,
               SUM(-amount) AS spent,
               COUNT(*) AS count
        FROM transactions
        WHERE amount < 0
          {_HC_TRANSFERISH}
          AND merchant IS NOT NULL AND merchant != ''
          AND date >= ? AND date <= ?
          AND merchant NOT IN (
              SELECT DISTINCT merchant FROM transactions
              WHERE amount < 0
                {_HC_TRANSFERISH}
                AND merchant IS NOT NULL
                AND date >= ? AND date < ?
          )
        GROUP BY merchant
        HAVING spent >= 20
        ORDER BY spent DESC
        LIMIT 20
        """,
        (current_start, current_end, lookback_start, current_start),
    ).fetchall()
    return [
        {
            "merchant": r["merchant"],
            "first_seen": r["first_seen"],
            "spent": round(r["spent"], 2),
            "count": r["count"],
        }
        for r in rows
    ]


def _hc_buffer(conn, today_iso: str) -> dict:
    lookback_90 = (date.fromisoformat(today_iso) - timedelta(days=90)).isoformat()
    acct = conn.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN LOWER(name) LIKE '%checking%' THEN current_balance END), 0) AS checking,
               COALESCE(SUM(CASE WHEN type = 'depository' THEN current_balance END), 0) AS total_liquid
        FROM accounts
        """
    ).fetchone()
    spend = conn.execute(
        f"""
        SELECT COALESCE(SUM(-amount), 0) AS total
        FROM transactions
        WHERE amount < 0
          {_HC_TRANSFERISH}
          AND date >= ?
        """,
        (lookback_90,),
    ).fetchone()
    avg_monthly = round((spend["total"] or 0) / 3.0, 2)
    runway_days = None
    # Runway uses total liquid (checking + savings) because savings are instantly
    # transferable. Checking alone dramatically understates real runway.
    if avg_monthly > 0:
        runway_days = round(acct["total_liquid"] / (avg_monthly / 30), 1)
    return {
        "checking_balance": round(acct["checking"], 2),
        "total_liquid": round(acct["total_liquid"], 2),
        "avg_monthly_spend_90d": avg_monthly,
        "runway_days": runway_days,
    }


def _hc_cc(conn) -> list[dict]:
    rows = conn.execute(
        """
        SELECT name, current_balance, available_balance
        FROM accounts
        WHERE type IN ('credit', 'loan') AND current_balance IS NOT NULL
        ORDER BY current_balance DESC
        """
    ).fetchall()
    return [
        {
            "name": r["name"],
            "balance_owed": round(r["current_balance"], 2),
            "available_credit": round(r["available_balance"], 2) if r["available_balance"] is not None else None,
        }
        for r in rows
    ]


@mcp.tool()
def healthcheck(window_days: int = 30, lookback_days: int = 180) -> dict:
    """
    Structured financial-health signals: subscriptions, category MoM trends,
    transaction outliers, new merchants, cash buffer, credit-card utilization.

    Compares a trailing `window_days` window to the prior window of the same
    length (default: last 30d vs. 30d before that). Baselines for outliers and
    new-merchant detection look back `lookback_days` (default 180).

    All amounts are dollars, positive = money out. Transfers (is_transfer=1)
    and excluded (excluded=1) transactions are filtered from every signal.

    Caller is expected to narrate: return value is machine signals + a `flags`
    array of high-level labels for the LLM to pick up on.
    """
    window_days = max(7, min(window_days, 90))
    lookback_days = max(window_days * 2, min(lookback_days, 365))

    today = date.today()
    current_end = today
    current_start = today - timedelta(days=window_days)
    prior_end = current_start - timedelta(days=1)
    prior_start = prior_end - timedelta(days=window_days - 1)
    lookback_start = today - timedelta(days=lookback_days)

    today_iso = today.isoformat()
    current_start_iso = current_start.isoformat()
    current_end_iso = current_end.isoformat()
    prior_start_iso = prior_start.isoformat()
    prior_end_iso = prior_end.isoformat()
    lookback_start_iso = lookback_start.isoformat()

    with db.cursor() as conn:
        subs = _hc_subscriptions(conn, lookback_start_iso, today_iso, current_start_iso)
        trends = _hc_category_trends(conn, prior_start_iso, current_start_iso, current_end_iso)
        outliers = _hc_outliers(conn, lookback_start_iso, current_start_iso, current_end_iso)
        new_mers = _hc_new_merchants(conn, lookback_start_iso, current_start_iso, current_end_iso)
        buffer = _hc_buffer(conn, today_iso)
        cc = _hc_cc(conn)

    flags: list[str] = []
    for s in subs:
        # Only flag amount-change signals on STABLE subscriptions. Grocery/restaurant
        # spend naturally varies and flagging those as "price changes" is noise.
        if not s["amount_stable"]:
            continue
        if s["new"]:
            flags.append(f"new_subscription:{s['merchant']}:${s['avg_amount']}")
        elif s["amount_change_pct"] is not None and abs(s["amount_change_pct"]) >= 15:
            direction = "up" if s["amount_change_pct"] > 0 else "down"
            flags.append(f"subscription_price_{direction}:{s['merchant']}:{s['amount_change_pct']}%")
    for t in trends:
        if t["new_category"] and t["current"] >= 50:
            flags.append(f"new_category_spend:{t['category']}:${t['current']}")
        elif t["pct_change"] is not None and t["pct_change"] >= 25 and t["abs_change"] >= 50:
            flags.append(f"category_surge:{t['category']}:+${t['abs_change']}:{t['pct_change']}%")
        elif t["pct_change"] is not None and t["pct_change"] <= -25 and t["abs_change"] <= -50:
            flags.append(f"category_drop:{t['category']}:${t['abs_change']}:{t['pct_change']}%")
    if len(outliers) >= 3:
        flags.append(f"many_outliers:{len(outliers)}")
    if buffer["runway_days"] is not None and buffer["runway_days"] < 60:
        flags.append(f"low_runway:{buffer['runway_days']}d")

    return {
        "window": {
            "current_start": current_start_iso,
            "current_end": current_end_iso,
            "prior_start": prior_start_iso,
            "prior_end": prior_end_iso,
            "lookback_start": lookback_start_iso,
        },
        "subscriptions": subs,
        "category_trends": trends,
        "outliers": outliers,
        "new_merchants": new_mers,
        "buffer": buffer,
        "cc_utilization": cc,
        "flags": flags,
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
