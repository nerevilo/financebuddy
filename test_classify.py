"""
Tests for the classification pipeline (fb.classify).

Focus: null-merchant rows. Teller leaves `merchant` NULL for bank-initiated
transactions (rent ACH, interest, internal transfers). ~25% of real rows. The
detectors must key on COALESCE(merchant, description) — the same key the
healthcheck reporting layer uses — or those rows are invisible to detection and
can never be auto-classified or surfaced for the LLM.

Regression guard for the bug where a $1,095 rent payment with merchant=NULL
never appeared as a rent candidate.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path


def _make_db(tmp_path: Path) -> Path:
    dbp = tmp_path / "classify_test.db"
    os.environ["FB_DB_PATH"] = str(dbp)
    from fb import db
    db.DB_PATH = dbp
    db.init()
    return dbp


def _conn(dbp: Path) -> sqlite3.Connection:
    c = sqlite3.connect(dbp)
    c.row_factory = sqlite3.Row
    return c


def _seed_account(conn) -> None:
    conn.execute(
        "INSERT INTO institutions(id, name, access_token) VALUES (?, ?, ?)",
        ("inst1", "TestBank", "tok"),
    )
    conn.execute(
        "INSERT INTO accounts(id, institution_id, name, type, current_balance, available_balance) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("acc_check", "inst1", "Test Checking", "depository", 5000.0, 5000.0),
    )
    conn.commit()


def _add(conn, tx_id, dt, amount, *, merchant=None, description=None,
         category="general", account="acc_check", is_transfer=0, excluded=0):
    """Insert a tx. merchant defaults to NULL (the bank-initiated case)."""
    conn.execute(
        "INSERT INTO transactions(id, account_id, date, amount, description, merchant, "
        "category, is_transfer, excluded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (tx_id, account, dt.isoformat(), amount, description, merchant, category,
         is_transfer, excluded),
    )


def _today():
    return date.today()


# ---------------------------------------------------------------------------
# The core regression: null-merchant rent must be detectable
# ---------------------------------------------------------------------------

def test_rent_candidate_detected_when_merchant_is_null():
    """A monthly stable ~$1.1k outflow with merchant=NULL (real rent ACH shape)
    must surface as a rent candidate keyed by its description."""
    with tempfile.TemporaryDirectory() as td:
        conn = _conn(_make_db(Path(td)))
        _seed_account(conn)

        today = _today()
        desc = "Withdrawal from LR2-ARCLUB WEB PMTS"
        for i, days_ago in enumerate([90, 60, 30, 1]):
            _add(conn, f"rent{i}", today - timedelta(days=days_ago), -1095.50,
                 merchant=None, description=desc)
        conn.commit()

        from fb import classify
        cands = classify.detect_rent_candidates(conn, lookback_days=180)
        merchants = [c["merchant"] for c in cands]
        assert desc in merchants, (
            f"null-merchant rent must surface as a candidate; got {merchants}"
        )
        rent = next(c for c in cands if c["merchant"] == desc)
        assert rent["avg_amount"] == 1095.50


def test_unclassified_surfaces_null_merchant_spend():
    """Null-merchant spend (e.g. a Costco run Teller didn't tag a counterparty
    on) must appear in the unclassified list for the LLM, not vanish."""
    with tempfile.TemporaryDirectory() as td:
        conn = _conn(_make_db(Path(td)))
        _seed_account(conn)

        today = _today()
        _add(conn, "c1", today - timedelta(days=3), -184.48,
             merchant=None, description="COSTCO WHSE #0333 EVERETT US")
        conn.commit()

        from fb import classify
        un = classify.unclassified_merchants(conn, min_spend=20, days=90)
        merchants = [u["merchant"] for u in un]
        assert "COSTCO WHSE #0333 EVERETT US" in merchants, (
            f"null-merchant spend must surface as unclassified; got {merchants}"
        )


def test_classification_roundtrips_for_null_merchant_row():
    """A classification stored under the description key (how the LLM/user
    classifies a null-merchant row) must make that row drop OUT of the
    unclassified list — proving detector and store agree on the key."""
    with tempfile.TemporaryDirectory() as td:
        conn = _conn(_make_db(Path(td)))
        _seed_account(conn)

        today = _today()
        desc = "Withdrawal from LR2-ARCLUB WEB PMTS"
        for i, days_ago in enumerate([60, 30, 1]):
            _add(conn, f"r{i}", today - timedelta(days=days_ago), -1095.50,
                 merchant=None, description=desc)
        conn.commit()

        from fb import classify
        # Before: appears unclassified
        before = [u["merchant"] for u in classify.unclassified_merchants(conn, min_spend=20)]
        assert desc in before

        classify.upsert(conn, desc, "fixed:rent", "user")
        conn.commit()

        after = [u["merchant"] for u in classify.unclassified_merchants(conn, min_spend=20)]
        assert desc not in after, "classified null-merchant row must leave unclassified set"


# ---------------------------------------------------------------------------
# _TRANSFERISH must keep internal moves / card payments out of detection
# even now that detectors see null-merchant rows.
# ---------------------------------------------------------------------------

def test_internal_deposit_not_flagged_as_salary():
    """A recurring stable ~$2k 'Deposit from … XXXXXXX' internal move (merchant
    NULL) must NOT be mistaken for salary now that detectors see null rows."""
    with tempfile.TemporaryDirectory() as td:
        conn = _conn(_make_db(Path(td)))
        _seed_account(conn)

        today = _today()
        desc = "Deposit from Emergency Savings XXXXXXX8031"
        for i, days_ago in enumerate([42, 28, 14, 0]):
            _add(conn, f"mv{i}", today - timedelta(days=days_ago), 2000.0,
                 merchant=None, description=desc)
        conn.commit()

        from fb import classify
        sal = [s["merchant"] for s in classify.detect_salary(conn, lookback_days=180)]
        assert desc not in sal, f"internal transfer leaked into salary: {sal}"


def test_cc_autopay_null_merchant_not_unclassified():
    """An AUTOPAY card payment with merchant NULL must be filtered from the
    unclassified spend list (it's a transfer, not consumption)."""
    with tempfile.TemporaryDirectory() as td:
        conn = _conn(_make_db(Path(td)))
        _seed_account(conn)

        today = _today()
        _add(conn, "ap", today - timedelta(days=5), -2799.53,
             merchant=None, description="AUTOPAY 251115114028065RAUTOPAY AUTO-PMT")
        conn.commit()

        from fb import classify
        un = [u["merchant"] for u in classify.unclassified_merchants(conn, min_spend=20)]
        assert not any("AUTOPAY" in m for m in un), f"autopay leaked: {un}"


# ---------------------------------------------------------------------------
# Existing behavior with populated merchants must still work
# ---------------------------------------------------------------------------

def test_populated_merchant_still_keyword_classified():
    with tempfile.TemporaryDirectory() as td:
        conn = _conn(_make_db(Path(td)))
        _seed_account(conn)

        today = _today()
        _add(conn, "tj", today - timedelta(days=3), -75.0,
             merchant="TRADER JOE'S", description="TRADER JOE S #501 BROOKLINE")
        conn.commit()

        from fb import classify
        hits = {h["merchant"]: h["classification"] for h in classify.keyword_scan(conn)}
        assert hits.get("TRADER JOE'S") == "variable:groceries"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
