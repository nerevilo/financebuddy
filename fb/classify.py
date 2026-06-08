"""Heuristic merchant classification.

Persists per-merchant labels to merchant_classifications. The healthcheck tool
reads this table to build a structured Income / Fixed / Variable / Savings view.

Sources:
  - 'user'      — explicit confirmation (never overwritten by automation)
  - 'heuristic' — detected by cadence/amount pattern or keyword match
  - 'llm'       — classified by Claude using merchant name + description

Taxonomy is fixed (see TAXONOMY). Unknown values raise ValueError.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional


def _start_iso(lookback_days: int) -> str:
    return (date.today() - timedelta(days=lookback_days)).isoformat()


# On this user's data, Teller reports credit-card amounts with the OPPOSITE
# sign of depository accounts (positive = charge/spend, negative = payment/refund).
# Normalize to cash-flow convention: flow > 0 = inflow (income/refund),
# flow < 0 = outflow (spend). Use this expression in any query that needs to
# reason about money direction across account types.
FLOW_EXPR = "(CASE WHEN a.type IN ('credit','loan') THEN -t.amount ELSE t.amount END)"


# Canonical merchant key. Teller leaves `merchant` (counterparty.name) NULL for
# bank-initiated rows — rent ACH, interest, internal transfers, Zelle — which is
# ~25% of this user's transactions. The healthcheck reporting layer keys those on
# `merchant or description` (mcp_server.py:694), so the classification pipeline
# MUST use the same key, or null-merchant rows are invisible to every detector
# and can never be auto-classified or surfaced for the LLM. Use this everywhere
# a query groups by or returns a "merchant". Requires the transactions table to
# be aliased `t`.
MERCHANT_KEY = "COALESCE(NULLIF(TRIM(t.merchant), ''), t.description)"


# Description / merchant patterns that indicate an internal transfer or card
# payment even when is_transfer isn't set. Mirrors _HC_TRANSFERISH in
# mcp_server.py. Append to a detector's WHERE clause (the detectors already
# constrain is_transfer = 0 and excluded = 0). Critical now that detectors see
# null-merchant rows: without it, internal "Deposit from … XXXXXXX" moves and
# CC autopays would leak into salary / rent / subscription detection.
_TRANSFERISH = """
  AND COALESCE(t.category, '') NOT IN ('transfer', 'investment')
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%AUTOPAY%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%AUTO-PMT%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%AUTOMATIC PAYMENT%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%ONLINE PAYMENT%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%MOBILE PAYMENT%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%CC PAYMENT%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%PAYMENT THANK YOU%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE 'WITHDRAWAL TO %XXXXXXX%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE 'DEPOSIT FROM %XXXXXXX%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%INST XFER%'
  AND UPPER(COALESCE(t.description, '')) NOT LIKE '%PAYPAL%INST%'
  AND UPPER(COALESCE(t.merchant, '')) NOT IN (
        'CITI', 'CITIBANK', 'CHASE', 'JPMORGAN CHASE',
        'AMEX', 'AMERICAN EXPRESS', 'CAPITAL ONE', 'CAPITALONE',
        'DISCOVER', 'BARCLAYCARD', 'BARCLAYS', 'WELLS FARGO',
        'BANK OF AMERICA', 'BOFA', 'US BANK', 'USAA',
        'ROBINHOOD', 'MSPBNA', 'FIDELITY', 'VANGUARD', 'SCHWAB',
        'MORGAN STANLEY', 'E*TRADE', 'ETRADE'
  )
"""


TAXONOMY: set[str] = {
    "income:salary",
    "income:refund",
    "income:other",
    "fixed:rent",
    "fixed:utility",
    "fixed:subscription",
    "fixed:membership",
    "fixed:insurance",
    "fixed:loan",
    "fixed:other",
    "variable:groceries",
    "variable:dining",
    "variable:transport",
    "variable:shopping",
    "variable:health",
    "variable:entertainment",
    "variable:travel",
    "variable:personal",
    "variable:fees",
    "variable:other",
    "transfer",
}


# Keyword matches on UPPER(merchant) or UPPER(description). Substring match.
# Ordered first-match-wins within each classification. Keep lists small — this
# is a safety net, not a full merchant database. Prefer specific substrings
# ("WHOLE FOODS") over generic ones ("FOOD").
_KEYWORDS: dict[str, list[str]] = {
    "fixed:utility": [
        "COMCAST", "XFINITY", "SPECTRUM", "COX COMM",
        "AT&T", "VERIZON", "T-MOBILE", "SPRINT", "GOOGLE FI",
        "PG&E", "CON EDISON", "CONED", "DTE ENERGY", "DUKE ENERGY",
        "SOCALGAS", "NATIONAL GRID", "EVERSOURCE", "DOMINION ENERGY",
        "CITY WATER", "WATER DEPT", "SEWER", "TRASH",
    ],
    "fixed:membership": [
        "LR2 ARCLUB", "ARCLUB", "EQUINOX", "PLANET FITNESS",
        "LA FITNESS", "CROSSFIT", "SOULCYCLE", "SOUL CYCLE",
        "PELOTON INTERACTIVE", "ORANGETHEORY", "24 HOUR FITNESS",
        "ANYTIME FITNESS", "CORE POWER", "YMCA", "GOLD'S GYM",
    ],
    "fixed:insurance": [
        "GEICO", "STATE FARM", "ALLSTATE", "PROGRESSIVE INS",
        "LIBERTY MUTUAL", "FARMERS INS", "METLIFE", "NATIONWIDE INS",
        "AMICA", "LEMONADE INS",
    ],
    "fixed:subscription": [
        "CLAUDE AI", "CLAUDE.AI", "ANTHROPIC",
        "OPENAI", "CHATGPT",
        "GITHUB", "REPLIT", "NOTION", "FIGMA",
        "1PASSWORD", "DROPBOX", "GOOGLE STORAGE", "ICLOUD",
        "NETFLIX", "SPOTIFY", "HULU", "DISNEY+", "DISNEY PLUS",
        "HBO MAX", "YOUTUBE PREMIUM", "APPLE.COM/BILL",
        "PLAYSTATION", "STEAMGAMES", "XBOX LIVE", "NVIDIA",
    ],
    "variable:groceries": [
        "KROGER", "WHOLE FOODS", "WHOLEFDS", "TRADER JOE",
        "SAFEWAY", "ALBERTSONS", "H MART", "HMART",
        "COSTCO WHSE", "SAM'S CLUB", "WEGMANS", "PUBLIX",
        "ALDI", "MEIJER", "SPROUTS", "HARRIS TEETER",
    ],
    "variable:dining": [
        "STARBUCKS", "DUNKIN", "DOMINO", "PIZZA HUT",
        "CHIPOTLE", "MCDONALD", "SUBWAY", "CHICK-FIL-A",
        "PANERA", "UBER EATS", "DOORDASH", "GRUBHUB",
        "POSTMATES", "SEAMLESS", "CAVIAR",
    ],
    "variable:transport": [
        "UBER TRIP", "UBER BV", "LYFT", "SHELL OIL", "CHEVRON",
        "EXXON", "EXXONMOBIL", "COSTCO GAS", "WAWA",
        "METRO TRANSIT", "PARKING",
    ],
    "variable:shopping": [
        "AMAZON", "AMZN", "TARGET", "WALMART", "BEST BUY",
        "HOME DEPOT", "LOWE'S", "LOWES", "IKEA", "WAYFAIR",
        "ETSY", "EBAY",
    ],
    "variable:health": [
        "CVS", "WALGREENS", "RITE AID", "PHARMACY",
    ],
    "variable:fees": [
        "STATE OF ", "IRS USATAXPYMT", "IRS DIRECT PAY",
        "DMV ", "BANK FEE", "OVERDRAFT FEE",
    ],
}


def validate(cls: str) -> None:
    if cls not in TAXONOMY:
        raise ValueError(f"Unknown classification {cls!r}. Allowed: {sorted(TAXONOMY)}")


def get_classification(conn: sqlite3.Connection, merchant: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT merchant, classification, confidence, source, notes, created_at, updated_at "
        "FROM merchant_classifications WHERE merchant = ?",
        (merchant,),
    ).fetchone()
    return dict(row) if row else None


def upsert(
    conn: sqlite3.Connection,
    merchant: str,
    classification: str,
    source: str,
    confidence: float = 1.0,
    notes: Optional[str] = None,
) -> str:
    """Insert or update one merchant classification.

    Returns one of: 'inserted', 'updated', 'skipped_user_override'.

    Never overwrites a user-confirmed entry with a heuristic/llm entry.
    """
    validate(classification)
    if source not in ("user", "heuristic", "llm"):
        raise ValueError(f"Unknown source {source!r}")
    if not merchant:
        raise ValueError("merchant is required")

    existing = conn.execute(
        "SELECT source FROM merchant_classifications WHERE merchant = ?",
        (merchant,),
    ).fetchone()
    if existing and existing["source"] == "user" and source != "user":
        return "skipped_user_override"

    conn.execute(
        """
        INSERT INTO merchant_classifications (merchant, classification, confidence, source, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ON CONFLICT(merchant) DO UPDATE SET
            classification = excluded.classification,
            confidence     = excluded.confidence,
            source         = excluded.source,
            notes          = excluded.notes,
            updated_at     = datetime('now')
        """,
        (merchant, classification, confidence, source, notes),
    )
    return "inserted" if existing is None else "updated"


def all_classifications(conn: sqlite3.Connection) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT merchant, classification, confidence, source, notes FROM merchant_classifications"
    ).fetchall()
    return {r["merchant"]: dict(r) for r in rows}


# ---------------------------------------------------------------------------
# Heuristic detectors
# ---------------------------------------------------------------------------


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def _cadence_days(dates: list[str]) -> Optional[float]:
    """Median gap in days between consecutive dates. None if <2 dates."""
    if len(dates) < 2:
        return None
    ds = sorted(datetime.fromisoformat(d).date() for d in dates)
    gaps = [(ds[i] - ds[i - 1]).days for i in range(1, len(ds))]
    return _median([float(g) for g in gaps])


def _cadence_label(median_gap: float) -> Optional[str]:
    if 5 <= median_gap <= 9:
        return "weekly"
    if 12 <= median_gap <= 16:
        return "biweekly"
    if 25 <= median_gap <= 35:
        return "monthly"
    if 55 <= median_gap <= 70:
        return "bimonthly"
    return None


_SALARY_DESC_KEYWORDS = ("PAYROLL", "DIR DEP", "DIRECT DEP", "SALARY", " PAY ", "REG PAY")


def detect_salary(conn: sqlite3.Connection, lookback_days: int = 180) -> list[dict]:
    """Recurring positive deposits. Two paths:

    1. Description contains an unambiguous payroll keyword (PAYROLL, DIRECT DEP,
       SALARY) — classify immediately with high confidence.
    2. Cadence + amount stability — fallback heuristic. The first paycheck in
       a new job is often prorated, so we also accept when the most recent 2
       occurrences are stable within 5% even if the full series isn't.
    """
    start = _start_iso(lookback_days)
    # Salary is always inflow on depository. Using flow > 0 (normalized).
    rows = conn.execute(
        f"""
        SELECT {MERCHANT_KEY} AS merchant,
               COUNT(*) AS n,
               AVG({FLOW_EXPR}) AS avg_amt,
               MIN({FLOW_EXPR}) AS min_amt,
               MAX({FLOW_EXPR}) AS max_amt,
               GROUP_CONCAT(t.date, '|') AS dates,
               GROUP_CONCAT({FLOW_EXPR}, '|') AS amounts,
               MAX(UPPER(COALESCE(t.description, ''))) AS sample_desc
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        WHERE {FLOW_EXPR} > 0 AND t.excluded = 0 AND t.is_transfer = 0
          AND {MERCHANT_KEY} IS NOT NULL AND {MERCHANT_KEY} != ''
          AND a.type = 'depository'
          AND t.date >= ?
          {_TRANSFERISH}
        GROUP BY {MERCHANT_KEY}
        HAVING n >= 2 AND avg_amt >= 200
        """,
        (start,),
    ).fetchall()

    out: list[dict] = []
    for r in rows:
        avg = r["avg_amt"] or 0
        if avg <= 0:
            continue
        dates = r["dates"].split("|")
        gap = _cadence_days(dates)
        if gap is None:
            continue
        cadence = _cadence_label(gap)
        if cadence is None or cadence == "weekly":
            continue

        desc = r["sample_desc"] or ""
        has_payroll_keyword = any(k in desc for k in _SALARY_DESC_KEYWORDS)

        full_spread = (r["max_amt"] - r["min_amt"]) / avg
        # Recent-2 spread: first paycheck of a new job is often prorated.
        paired = sorted(
            zip(dates, [float(a) for a in r["amounts"].split("|")]),
            key=lambda p: p[0],
        )
        recent_amts = [a for _, a in paired[-2:]]
        recent_spread = (
            (max(recent_amts) - min(recent_amts)) / (sum(recent_amts) / len(recent_amts))
            if recent_amts else 1.0
        )

        accept = False
        confidence = 0.0
        if has_payroll_keyword:
            accept = True
            confidence = 0.98
        elif full_spread <= 0.15:
            accept = True
            confidence = 0.9 if full_spread <= 0.05 else 0.8
        elif recent_spread <= 0.05 and r["n"] >= 3:
            accept = True
            confidence = 0.75
        if not accept:
            continue

        out.append(
            {
                "merchant": r["merchant"],
                "avg_amount": round(avg, 2),
                "min_amount": round(r["min_amt"], 2),
                "max_amount": round(r["max_amt"], 2),
                "cadence": cadence,
                "cadence_gap_days": round(gap, 1),
                "occurrences": r["n"],
                "stable_pct": round(full_spread * 100, 1),
                "recent_stable_pct": round(recent_spread * 100, 1),
                "keyword_match": has_payroll_keyword,
                "confidence": confidence,
            }
        )
    return out


def detect_rent_candidates(conn: sqlite3.Connection, lookback_days: int = 180) -> list[dict]:
    """Large monthly outflows from depository accounts with stable amounts.

    We surface these as candidates (not auto-apply) because rent can go to a
    person's name (Zelle to landlord/roommate) which is indistinguishable from
    a regular gift without user context.
    """
    start = _start_iso(lookback_days)
    rows = conn.execute(
        f"""
        SELECT {MERCHANT_KEY} AS merchant,
               COUNT(*) AS n,
               AVG(-{FLOW_EXPR}) AS avg_amt,
               MIN(-{FLOW_EXPR}) AS min_amt,
               MAX(-{FLOW_EXPR}) AS max_amt,
               GROUP_CONCAT(t.date, '|') AS dates
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        LEFT JOIN merchant_classifications mc ON mc.merchant = {MERCHANT_KEY}
        WHERE {FLOW_EXPR} < 0 AND t.excluded = 0 AND t.is_transfer = 0
          AND {MERCHANT_KEY} IS NOT NULL AND {MERCHANT_KEY} != ''
          AND -{FLOW_EXPR} BETWEEN 600 AND 6000
          AND a.type = 'depository'
          AND t.date >= ?
          AND mc.merchant IS NULL
          {_TRANSFERISH}
        GROUP BY {MERCHANT_KEY}
        HAVING n >= 2
        """,
        (start,),
    ).fetchall()

    out: list[dict] = []
    for r in rows:
        avg = r["avg_amt"] or 0
        if avg <= 0:
            continue
        spread = (r["max_amt"] - r["min_amt"]) / avg
        if spread > 0.05:  # rent is very stable
            continue
        gap = _cadence_days(r["dates"].split("|"))
        if gap is None or _cadence_label(gap) != "monthly":
            continue
        out.append(
            {
                "merchant": r["merchant"],
                "avg_amount": round(avg, 2),
                "cadence_gap_days": round(gap, 1),
                "occurrences": r["n"],
                "stable_pct": round(spread * 100, 1),
            }
        )
    out.sort(key=lambda x: x["avg_amount"], reverse=True)
    return out


def detect_subscriptions(conn: sqlite3.Connection, lookback_days: int = 180) -> list[dict]:
    """Stable-amount monthly outflows $1-$200, seen ≥3 months.

    Investment contributions (category='investment') and transfers are excluded —
    a recurring monthly Robinhood contribution looks like a subscription but
    is really a savings flow.
    """
    start = _start_iso(lookback_days)
    rows = conn.execute(
        f"""
        SELECT {MERCHANT_KEY} AS merchant,
               COUNT(*) AS n,
               COUNT(DISTINCT strftime('%Y-%m', t.date)) AS months,
               AVG(-{FLOW_EXPR}) AS avg_amt,
               MIN(-{FLOW_EXPR}) AS min_amt,
               MAX(-{FLOW_EXPR}) AS max_amt,
               GROUP_CONCAT(t.date, '|') AS dates
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        WHERE {FLOW_EXPR} < 0 AND t.excluded = 0 AND t.is_transfer = 0
          AND {MERCHANT_KEY} IS NOT NULL AND {MERCHANT_KEY} != ''
          AND -{FLOW_EXPR} BETWEEN 1 AND 200
          AND t.date >= ?
          {_TRANSFERISH}
        GROUP BY {MERCHANT_KEY}
        HAVING months >= 3
        """,
        (start,),
    ).fetchall()

    out: list[dict] = []
    for r in rows:
        avg = r["avg_amt"] or 0
        if avg <= 0:
            continue
        spread = (r["max_amt"] - r["min_amt"]) / avg
        if spread > 0.10:  # stable within 10%
            continue
        gap = _cadence_days(r["dates"].split("|"))
        if gap is None:
            continue
        cadence = _cadence_label(gap)
        if cadence not in ("monthly", "bimonthly"):
            continue
        out.append(
            {
                "merchant": r["merchant"],
                "avg_amount": round(avg, 2),
                "months_seen": r["months"],
                "cadence": cadence,
                "stable_pct": round(spread * 100, 1),
                "confidence": 0.9,
            }
        )
    return out


def keyword_scan(conn: sqlite3.Connection, lookback_days: int = 180) -> list[dict]:
    """Match merchants (or descriptions) against known keyword lists.

    Returns candidates with classification + the matched keyword. The caller
    upserts these; keyword matches are high-confidence but never override user.
    """
    start = _start_iso(lookback_days)
    rows = conn.execute(
        f"""
        SELECT {MERCHANT_KEY} AS merchant,
               MAX(UPPER(COALESCE(t.description, ''))) AS sample_desc,
               COUNT(*) AS n
        FROM transactions t
        WHERE {MERCHANT_KEY} IS NOT NULL AND {MERCHANT_KEY} != ''
          AND t.excluded = 0 AND t.is_transfer = 0
          AND t.date >= ?
          {_TRANSFERISH}
        GROUP BY {MERCHANT_KEY}
        """,
        (start,),
    ).fetchall()

    out: list[dict] = []
    for r in rows:
        m_up = (r["merchant"] or "").upper()
        desc_up = r["sample_desc"] or ""
        for cls, patterns in _KEYWORDS.items():
            matched = None
            for p in patterns:
                if p in m_up or p in desc_up:
                    matched = p
                    break
            if matched:
                out.append(
                    {
                        "merchant": r["merchant"],
                        "classification": cls,
                        "keyword": matched,
                        "occurrences": r["n"],
                    }
                )
                break  # first-matching classification wins
    return out


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def auto_enrich(conn: sqlite3.Connection, lookback_days: int = 180) -> dict:
    """Run all heuristics. Writes heuristic classifications to the table.

    Returns a summary with counts + the list of rent candidates (not
    auto-applied — caller asks user to confirm) + skipped (user-overridden).
    """
    summary = {
        "salary_classified": [],
        "subscriptions_classified": [],
        "keyword_classified": [],
        "rent_candidates": [],
        "skipped_user_override": 0,
    }

    for cand in detect_salary(conn, lookback_days=lookback_days):
        note = f"{cand['cadence']} avg ${cand['avg_amount']} ({cand['occurrences']}x, spread {cand['stable_pct']}%)"
        result = upsert(
            conn, cand["merchant"], "income:salary", "heuristic",
            confidence=cand["confidence"], notes=note,
        )
        if result == "skipped_user_override":
            summary["skipped_user_override"] += 1
        else:
            summary["salary_classified"].append(cand)

    for cand in detect_subscriptions(conn, lookback_days=lookback_days):
        note = f"{cand['cadence']} ${cand['avg_amount']} x{cand['months_seen']}mo"
        result = upsert(
            conn, cand["merchant"], "fixed:subscription", "heuristic",
            confidence=cand["confidence"], notes=note,
        )
        if result == "skipped_user_override":
            summary["skipped_user_override"] += 1
        else:
            summary["subscriptions_classified"].append(cand)

    for cand in keyword_scan(conn, lookback_days=lookback_days):
        note = f"keyword:{cand['keyword']}"
        result = upsert(
            conn, cand["merchant"], cand["classification"], "heuristic",
            confidence=0.9, notes=note,
        )
        if result == "skipped_user_override":
            summary["skipped_user_override"] += 1
        else:
            summary["keyword_classified"].append(cand)

    # Rent — surface as candidates, only if user hasn't already set a rent merchant.
    existing_rent = conn.execute(
        "SELECT COUNT(*) AS n FROM merchant_classifications WHERE classification = 'fixed:rent' AND source = 'user'"
    ).fetchone()
    if existing_rent["n"] == 0:
        summary["rent_candidates"] = detect_rent_candidates(conn, lookback_days=lookback_days)

    conn.commit()
    return summary


def unclassified_merchants(
    conn: sqlite3.Connection,
    min_spend: float = 20.0,
    days: int = 90,
    limit: int = 30,
) -> list[dict]:
    """Merchants with meaningful spend in the window that have no classification.

    Intended to be handed to the LLM for world-knowledge classification.
    """
    start = (date.today() - timedelta(days=days)).isoformat()
    # _TRANSFERISH filtering so credit-card autopay, investment contributions
    # (Robinhood), and self-transfers don't show up as unclassified spend that
    # the LLM has to label. Keyed on MERCHANT_KEY so null-merchant rows (rent
    # ACH, bills) surface here for classification instead of falling silent.
    rows = conn.execute(
        f"""
        SELECT {MERCHANT_KEY} AS merchant,
               SUM(-{FLOW_EXPR}) AS spent,
               COUNT(*) AS n,
               MAX(t.description) AS sample_description,
               MAX(t.category) AS sample_category,
               MIN(t.date) AS first_seen,
               MAX(t.date) AS last_seen
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        LEFT JOIN merchant_classifications mc ON mc.merchant = {MERCHANT_KEY}
        WHERE {FLOW_EXPR} < 0
          AND t.excluded = 0 AND t.is_transfer = 0
          AND {MERCHANT_KEY} IS NOT NULL AND {MERCHANT_KEY} != ''
          AND t.date >= ?
          AND mc.merchant IS NULL
          {_TRANSFERISH}
        GROUP BY {MERCHANT_KEY}
        HAVING spent >= ?
        ORDER BY spent DESC
        LIMIT ?
        """,
        (start, min_spend, limit),
    ).fetchall()
    return [
        {
            "merchant": r["merchant"],
            "spent": round(r["spent"], 2),
            "count": r["n"],
            "sample_description": r["sample_description"],
            "sample_category": r["sample_category"],
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
        }
        for r in rows
    ]
