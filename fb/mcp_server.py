"""MCP stdio server exposing FinanceBuddy data to Claude Code."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastmcp import FastMCP

from . import classify, db, sync as sync_mod

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


# ---------------------------------------------------------------------------
# Merchant classification
# ---------------------------------------------------------------------------


@mcp.tool()
def classify_merchant(
    merchant: str,
    classification: str,
    source: str = "user",
    notes: Optional[str] = None,
) -> dict:
    """Persist a classification for a merchant.

    `classification` must be one of the fixed taxonomy values:
      income:{salary,refund,other}
      fixed:{rent,utility,subscription,membership,insurance,loan,other}
      variable:{groceries,dining,transport,shopping,health,entertainment,travel,personal,fees,other}
      transfer

    `source` is 'user' (explicit confirmation), 'llm' (classified by Claude
    from world knowledge), or 'heuristic' (cadence/keyword detected).
    User-source entries are never overwritten by automated re-enrichment.

    Returns the stored row + an 'action' field: inserted|updated|skipped_user_override.
    """
    with db.cursor() as conn:
        action = classify.upsert(
            conn, merchant=merchant, classification=classification,
            source=source, notes=notes,
        )
        row = classify.get_classification(conn, merchant) or {}
    return {"action": action, **row}


@mcp.tool()
def list_classifications(classification: Optional[str] = None) -> list[dict]:
    """All merchant classifications, optionally filtered by classification string."""
    with db.cursor() as conn:
        if classification:
            rows = conn.execute(
                "SELECT merchant, classification, confidence, source, notes, created_at, updated_at "
                "FROM merchant_classifications WHERE classification = ? ORDER BY merchant",
                (classification,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT merchant, classification, confidence, source, notes, created_at, updated_at "
                "FROM merchant_classifications ORDER BY classification, merchant"
            ).fetchall()
    return _rows(rows)


@mcp.tool()
def auto_enrich(lookback_days: int = 180) -> dict:
    """Run heuristic merchant classification: salary cadence, stable subscriptions,
    keyword-matched categories. Never overwrites user-confirmed entries.

    Also returns `rent_candidates` — merchants that look like rent (large,
    monthly, stable, from depository) that the caller should ask the user
    to confirm, since rent often goes to a person's name.
    """
    with db.cursor() as conn:
        return classify.auto_enrich(conn, lookback_days=lookback_days)


@mcp.tool()
def get_unclassified_merchants(
    min_spend: float = 20.0, days: int = 90, limit: int = 30
) -> list[dict]:
    """Merchants with spend ≥min_spend in the trailing `days` window that have
    no classification. Intended for the LLM to classify using world knowledge.
    """
    with db.cursor() as conn:
        return classify.unclassified_merchants(
            conn, min_spend=min_spend, days=days, limit=limit
        )


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
    # Recurring charges: a merchant seen in ≥3 distinct calendar months. Uses
    # normalized flow so credit-card charges (positive in Teller) are treated
    # as outflows consistently with depository.
    FLOW = classify.FLOW_EXPR
    rows = conn.execute(
        f"""
        SELECT t.merchant,
               COUNT(*) AS tx_count,
               COUNT(DISTINCT strftime('%Y-%m', t.date)) AS months_seen,
               AVG(-{FLOW}) AS avg_amount,
               MIN(-{FLOW}) AS min_amount,
               MAX(-{FLOW}) AS max_amount,
               MIN(t.date) AS first_seen,
               MAX(t.date) AS last_seen
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        WHERE {FLOW} < 0
          {_HC_TRANSFERISH}
          AND t.date >= ? AND t.date <= ?
          AND t.merchant IS NOT NULL AND t.merchant != ''
        GROUP BY t.merchant
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
            SELECT AVG(CASE WHEN t.date >= ? THEN -{FLOW} END) AS cur_avg,
                   AVG(CASE WHEN t.date <  ? THEN -{FLOW} END) AS prior_avg
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            WHERE t.merchant = ? AND {FLOW} < 0
              {_HC_TRANSFERISH}
              AND t.date >= ? AND t.date <= ?
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


def _hc_outliers(conn, lookback_start: str, current_start: str, current_end: str) -> list[dict]:
    FLOW = classify.FLOW_EXPR
    # In the outer query both transactions (t) and baseline (b) have a merchant
    # column, so rewrite the shared transferish filter to qualify against t.
    t_filter = _HC_TRANSFERISH \
        .replace("is_transfer", "t.is_transfer") \
        .replace(" excluded ", " t.excluded ") \
        .replace("COALESCE(category", "COALESCE(t.category") \
        .replace("COALESCE(description", "COALESCE(t.description") \
        .replace("COALESCE(merchant", "COALESCE(t.merchant")
    rows = conn.execute(
        f"""
        WITH baseline AS (
            SELECT t.merchant, AVG(-{FLOW}) AS avg_spend, COUNT(*) AS n
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            WHERE {FLOW} < 0
              {_HC_TRANSFERISH}
              AND t.date >= ? AND t.date < ?
              AND t.merchant IS NOT NULL AND t.merchant != ''
            GROUP BY t.merchant
            HAVING n >= 2
        )
        SELECT t.id, t.date, t.merchant, t.category,
               -{FLOW} AS amount,
               b.avg_spend,
               ROUND(-{FLOW} / b.avg_spend, 2) AS ratio
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        JOIN baseline b ON b.merchant = t.merchant
        WHERE {FLOW} < 0
          {t_filter}
          AND t.date >= ? AND t.date <= ?
          AND -{FLOW} >= 20
          AND -{FLOW} > b.avg_spend * 2
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
    FLOW = classify.FLOW_EXPR
    rows = conn.execute(
        f"""
        SELECT t.merchant,
               MIN(t.date) AS first_seen,
               SUM(-{FLOW}) AS spent,
               COUNT(*) AS count
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        WHERE {FLOW} < 0
          {_HC_TRANSFERISH}
          AND t.merchant IS NOT NULL AND t.merchant != ''
          AND t.date >= ? AND t.date <= ?
          AND t.merchant NOT IN (
              SELECT DISTINCT t2.merchant FROM transactions t2
              JOIN accounts a2 ON a2.id = t2.account_id
              WHERE (CASE WHEN a2.type IN ('credit','loan') THEN -t2.amount ELSE t2.amount END) < 0
                AND t2.is_transfer = 0 AND t2.excluded = 0
                AND t2.merchant IS NOT NULL
                AND t2.date >= ? AND t2.date < ?
          )
        GROUP BY t.merchant
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
    FLOW = classify.FLOW_EXPR
    spend = conn.execute(
        f"""
        SELECT COALESCE(SUM(-{FLOW}), 0) AS total
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        WHERE {FLOW} < 0
          {_HC_TRANSFERISH}
          AND t.date >= ?
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


_GROUP_ORDER = {
    "income": ("salary", "refund", "other"),
    "fixed": ("rent", "utility", "subscription", "membership", "insurance", "loan", "other"),
    "variable": (
        "groceries", "dining", "transport", "shopping", "health",
        "entertainment", "travel", "personal", "fees", "other",
    ),
}


def _project_monthly(avg_amount: float, cadence: Optional[str]) -> Optional[float]:
    """Normalize a typical per-occurrence amount to a monthly-equivalent."""
    if not cadence or avg_amount is None:
        return None
    if cadence == "biweekly":
        return round(avg_amount * 26 / 12, 2)
    if cadence == "weekly":
        return round(avg_amount * 52 / 12, 2)
    if cadence == "monthly":
        return round(avg_amount, 2)
    if cadence == "bimonthly":
        return round(avg_amount / 2, 2)
    return None


def _infer_cadence_for_merchant(conn, merchant: str, lookback_start: str) -> Optional[str]:
    rows = conn.execute(
        "SELECT date FROM transactions WHERE merchant = ? AND excluded = 0 AND is_transfer = 0 "
        "AND date >= ? ORDER BY date",
        (merchant, lookback_start),
    ).fetchall()
    if len(rows) < 2:
        return None
    from .classify import _cadence_days, _cadence_label
    gap = _cadence_days([r["date"] for r in rows])
    if gap is None:
        return None
    return _cadence_label(gap)


@mcp.tool()
def healthcheck(window_days: int = 30, lookback_days: int = 180) -> dict:
    """Structured monthly financial picture using persisted merchant classifications.

    Expects `auto_enrich` + LLM classification to have been run first so that
    merchants are labeled. Any merchant without a classification ends up in
    `unclassified` and does not count toward income / fixed / variable totals.

    Output:
      window                — date ranges
      income                — actual in window + sources + projected monthly
      fixed                 — total + group breakdown + itemized list
      variable              — total + group breakdown + top merchants
      savings               — income - fixed - variable, rate %, projected
      buffer                — checking + total_liquid + runway_days
      cc_utilization        — credit card balances + available credit
      unclassified          — merchants with spend that need a label
      anomalies             — outliers, new_merchants, subscription_price_changes
      flags                 — high-level labels for the LLM to pick up on
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
        classifications = classify.all_classifications(conn)

        # Transactions in current window, excluding transfers/excluded/card-payments.
        # `flow` normalizes the sign across account types so flow > 0 = inflow
        # (income/refund) and flow < 0 = outflow (spend), regardless of whether
        # the tx is on a depository or credit account.
        rows = conn.execute(
            f"""
            SELECT t.merchant, t.description, t.date,
                   {classify.FLOW_EXPR} AS flow,
                   a.type AS account_type
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            WHERE t.date >= ? AND t.date <= ?
              {_HC_TRANSFERISH}
            """,
            (current_start_iso, current_end_iso),
        ).fetchall()

        # Bucket by classification
        income_by_merchant: dict[str, dict] = {}
        fixed_items: dict[tuple[str, str], dict] = {}   # (merchant, classification) -> aggregate
        variable_by_group: dict[str, float] = {g: 0.0 for g in _GROUP_ORDER["variable"]}
        variable_by_merchant: dict[str, float] = {}
        unclassified_total = 0.0
        unclassified_merchants: dict[str, dict] = {}
        refund_offsets = 0.0  # positive credit-card amounts with no merchant class

        for r in rows:
            m = r["merchant"] or (r["description"] or "").strip()
            if not m:
                continue
            cls_row = classifications.get(m)
            cls = cls_row["classification"] if cls_row else None
            amt = r["flow"]
            is_depository = r["account_type"] == "depository"

            if cls == "transfer":
                continue

            # Positive amount: income (depository + income class, or depository + unclassified),
            # or refund offsetting a classified spend merchant.
            if amt > 0:
                if cls and cls.startswith("income:"):
                    sub = cls.split(":", 1)[1]
                    agg = income_by_merchant.setdefault(
                        m,
                        {"merchant": m, "classification": cls, "subgroup": sub,
                         "total": 0.0, "count": 0},
                    )
                    agg["total"] += amt
                    agg["count"] += 1
                    continue
                if cls and cls.startswith("variable:"):
                    # Refund on a variable-spend merchant — offset the category.
                    sub = cls.split(":", 1)[1]
                    variable_by_group[sub] = variable_by_group.get(sub, 0.0) - amt
                    variable_by_merchant[m] = variable_by_merchant.get(m, 0.0) - amt
                    continue
                if cls and cls.startswith("fixed:"):
                    # Refund on a fixed-cost merchant — reduce that line item.
                    sub = cls.split(":", 1)[1]
                    key = (m, cls)
                    agg = fixed_items.setdefault(
                        key,
                        {"merchant": m, "classification": cls, "subgroup": sub,
                         "total": 0.0, "count": 0,
                         "notes": (cls_row or {}).get("notes")},
                    )
                    agg["total"] -= amt
                    continue
                # Unclassified positive: real income only if from depository;
                # credit-card positive is a pure refund (merchant unknown, so
                # we can't offset — count it as a refund we saw but didn't place).
                if is_depository:
                    agg = income_by_merchant.setdefault(
                        m,
                        {"merchant": m, "classification": "income:other",
                         "subgroup": "other", "total": 0.0, "count": 0},
                    )
                    agg["total"] += amt
                    agg["count"] += 1
                else:
                    refund_offsets += amt
                continue

            # amt < 0 from here on: spend
            spend = -amt

            if cls and cls.startswith("fixed:"):
                sub = cls.split(":", 1)[1]
                key = (m, cls)
                agg = fixed_items.setdefault(
                    key,
                    {"merchant": m, "classification": cls, "subgroup": sub,
                     "total": 0.0, "count": 0,
                     "notes": (cls_row or {}).get("notes")},
                )
                agg["total"] += spend
                agg["count"] += 1
                continue

            if cls and cls.startswith("variable:"):
                sub = cls.split(":", 1)[1]
                variable_by_group[sub] = variable_by_group.get(sub, 0.0) + spend
                variable_by_merchant[m] = variable_by_merchant.get(m, 0.0) + spend
                continue

            # Unclassified spend
            unclassified_total += spend
            u = unclassified_merchants.setdefault(
                m, {"merchant": m, "total": 0.0, "count": 0},
            )
            u["total"] += spend
            u["count"] += 1

        # Projected monthly income from cadence
        income_sources = []
        projected_income = 0.0
        for agg in income_by_merchant.values():
            m = agg["merchant"]
            cadence = None
            note = (classifications.get(m, {}) or {}).get("notes") or ""
            for tag in ("biweekly", "monthly", "weekly", "bimonthly"):
                if tag in note:
                    cadence = tag
                    break
            if not cadence:
                cadence = _infer_cadence_for_merchant(conn, m, lookback_start_iso)
            avg_per = agg["total"] / agg["count"] if agg["count"] else 0
            proj = _project_monthly(avg_per, cadence)
            if proj is not None:
                projected_income += proj
            income_sources.append({
                "merchant": m,
                "classification": agg["classification"],
                "total": round(agg["total"], 2),
                "count": agg["count"],
                "cadence": cadence,
                "projected_monthly": proj,
            })
        income_sources.sort(key=lambda x: x["total"], reverse=True)
        income_total = sum(s["total"] for s in income_sources)

        # Fixed groups
        fixed_groups = {g: 0.0 for g in _GROUP_ORDER["fixed"]}
        fixed_item_list = []
        for agg in fixed_items.values():
            fixed_groups[agg["subgroup"]] = fixed_groups.get(agg["subgroup"], 0.0) + agg["total"]
            fixed_item_list.append({
                "merchant": agg["merchant"],
                "classification": agg["classification"],
                "subgroup": agg["subgroup"],
                "total": round(agg["total"], 2),
                "count": agg["count"],
                "notes": agg.get("notes"),
            })
        fixed_item_list.sort(key=lambda x: x["total"], reverse=True)
        fixed_total = sum(fixed_groups.values())

        # Variable
        variable_merchants_sorted = sorted(
            [{"merchant": m, "total": round(t, 2)}
             for m, t in variable_by_merchant.items()],
            key=lambda x: x["total"], reverse=True,
        )[:10]
        variable_total = sum(variable_by_group.values())

        # Unclassified
        unclassified_list = sorted(
            [
                {"merchant": u["merchant"], "total": round(u["total"], 2), "count": u["count"]}
                for u in unclassified_merchants.values()
            ],
            key=lambda x: x["total"], reverse=True,
        )

        # Signals
        outliers = _hc_outliers(conn, lookback_start_iso, current_start_iso, current_end_iso)
        new_mers = _hc_new_merchants(conn, lookback_start_iso, current_start_iso, current_end_iso)
        subs_changes = _hc_subscriptions(conn, lookback_start_iso, today_iso, current_start_iso)
        buffer = _hc_buffer(conn, today_iso)
        cc = _hc_cc(conn)

    # Savings math
    net = income_total - fixed_total - variable_total
    rate_pct = round(net / income_total * 100, 1) if income_total > 0 else None
    projected_variable = round(variable_total * (30 / window_days), 2)
    # Fixed scales less cleanly in short windows; use the raw window total.
    projected_net = (
        projected_income - fixed_total - projected_variable
        if projected_income > 0 else None
    )
    projected_rate = (
        round(projected_net / projected_income * 100, 1)
        if projected_income > 0 and projected_net is not None else None
    )

    # Subscription price changes — reuse the old signal
    sub_price_changes = []
    for s in subs_changes:
        if not s["amount_stable"]:
            continue
        if s["amount_change_pct"] is not None and abs(s["amount_change_pct"]) >= 15:
            sub_price_changes.append({
                "merchant": s["merchant"],
                "avg_amount": s["avg_amount"],
                "change_pct": s["amount_change_pct"],
                "direction": "up" if s["amount_change_pct"] > 0 else "down",
            })

    flags: list[str] = []
    if rate_pct is not None and rate_pct < 0:
        flags.append(f"negative_savings:{rate_pct}%")
    elif rate_pct is not None and rate_pct < 10:
        flags.append(f"low_savings:{rate_pct}%")
    if buffer["runway_days"] is not None and buffer["runway_days"] < 60:
        flags.append(f"low_runway:{buffer['runway_days']}d")
    if unclassified_total >= max(100, variable_total * 0.25):
        flags.append(f"unclassified_spend:${round(unclassified_total, 2)}")
    for cc_row in cc:
        if cc_row["available_credit"] and cc_row["balance_owed"] > 0:
            total_limit = cc_row["balance_owed"] + cc_row["available_credit"]
            if total_limit > 0 and cc_row["balance_owed"] / total_limit > 0.5:
                flags.append(
                    f"cc_high_util:{cc_row['name']}:{round(cc_row['balance_owed'] / total_limit * 100, 1)}%"
                )
    for spc in sub_price_changes:
        flags.append(f"subscription_price_{spc['direction']}:{spc['merchant']}:{spc['change_pct']}%")
    if len(outliers) >= 3:
        flags.append(f"many_outliers:{len(outliers)}")

    return {
        "window": {
            "current_start": current_start_iso,
            "current_end": current_end_iso,
            "prior_start": prior_start_iso,
            "prior_end": prior_end_iso,
            "lookback_start": lookback_start_iso,
            "window_days": window_days,
        },
        "income": {
            "total": round(income_total, 2),
            "projected_monthly": round(projected_income, 2) if projected_income > 0 else None,
            "sources": income_sources,
        },
        "fixed": {
            "total": round(fixed_total, 2),
            "groups": {k: round(v, 2) for k, v in fixed_groups.items()},
            "items": fixed_item_list,
        },
        "variable": {
            "total": round(variable_total, 2),
            "groups": {k: round(v, 2) for k, v in variable_by_group.items()},
            "top_merchants": variable_merchants_sorted,
        },
        "savings": {
            "income": round(income_total, 2),
            "fixed": round(fixed_total, 2),
            "variable": round(variable_total, 2),
            "net": round(net, 2),
            "rate_pct": rate_pct,
            "projected_monthly_net": round(projected_net, 2) if projected_net is not None else None,
            "projected_monthly_rate_pct": projected_rate,
        },
        "buffer": buffer,
        "cc_utilization": cc,
        "unclassified": {
            "total": round(unclassified_total, 2),
            "merchants": unclassified_list,
        },
        "refunds_unattributed": round(refund_offsets, 2),
        "anomalies": {
            "outliers": outliers,
            "new_merchants": new_mers,
            "subscription_price_changes": sub_price_changes,
        },
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
