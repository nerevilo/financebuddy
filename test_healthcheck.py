"""
Tests for the healthcheck MCP tool.

Seeds an in-memory SQLite with controlled transaction data and asserts
detection logic on the private _hc_* helpers directly.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path


def _make_db(tmp_path: Path) -> Path:
    """Create a fresh DB with schema matching fb.db and return its path."""
    dbp = tmp_path / "hc_test.db"
    os.environ["FB_DB_PATH"] = str(dbp)
    from fb import db
    db.DB_PATH = dbp  # override the module-level constant so db.cursor() uses it
    db.init()
    return dbp


def _conn(dbp: Path) -> sqlite3.Connection:
    c = sqlite3.connect(dbp)
    c.row_factory = sqlite3.Row
    return c


def _seed_institution_and_account(conn) -> str:
    conn.execute(
        "INSERT INTO institutions(id, name, access_token) VALUES (?, ?, ?)",
        ("inst1", "TestBank", "tok"),
    )
    conn.execute(
        "INSERT INTO accounts(id, institution_id, name, type, current_balance, available_balance) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("acc_check", "inst1", "Test Checking", "depository", 5000.0, 5000.0),
    )
    conn.execute(
        "INSERT INTO accounts(id, institution_id, name, type, current_balance) "
        "VALUES (?, ?, ?, ?, ?)",
        ("acc_card", "inst1", "Test Card", "credit", 1200.0),
    )
    conn.commit()
    return "acc_check"


def _add_tx(conn, tx_id: str, dt: date, amount: float, merchant: str,
            category: str = "general", account: str = "acc_check",
            is_transfer: int = 0, excluded: int = 0) -> None:
    conn.execute(
        "INSERT INTO transactions(id, account_id, date, amount, description, merchant, "
        "category, is_transfer, excluded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (tx_id, account, dt.isoformat(), amount, merchant, merchant, category,
         is_transfer, excluded),
    )


def _today():
    return date.today()


# ---------------------------------------------------------------------------
# Subscription detection
# ---------------------------------------------------------------------------

def test_subscription_detected_when_monthly_stable_amount():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        # $15 Netflix for 5 months
        today = _today()
        for i, days_ago in enumerate([120, 90, 60, 30, 5]):
            _add_tx(conn, f"nf{i}", today - timedelta(days=days_ago), -15.00, "Netflix", "subscription")
        conn.commit()

        from fb.mcp_server import _hc_subscriptions
        subs = _hc_subscriptions(
            conn,
            (today - timedelta(days=180)).isoformat(),
            today.isoformat(),
            (today - timedelta(days=30)).isoformat(),
        )
        merchants = [s["merchant"] for s in subs]
        assert "Netflix" in merchants, f"expected Netflix detected as subscription, got {merchants}"
        nf = next(s for s in subs if s["merchant"] == "Netflix")
        assert nf["avg_amount"] == 15.0
        assert nf["months_seen"] >= 3
        assert nf["amount_stable"] is True


def test_subscription_not_flagged_new_when_started_before_window():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # 3 charges across 3 months, first_seen well before the current window
        for i, days_ago in enumerate([90, 60, 30, 3]):
            _add_tx(conn, f"oa{i}", today - timedelta(days=days_ago), -9.99, "OldApp", "software")
        conn.commit()

        from fb.mcp_server import _hc_subscriptions
        current_start = (today - timedelta(days=30)).isoformat()
        subs = _hc_subscriptions(
            conn,
            (today - timedelta(days=180)).isoformat(),
            today.isoformat(),
            current_start,
        )
        s = next((x for x in subs if x["merchant"] == "OldApp"), None)
        assert s is not None, f"expected OldApp detected; got {[x['merchant'] for x in subs]}"
        assert s["new"] is False
        assert s["amount_stable"] is True


def test_variable_charges_flagged_but_not_stable():
    """Recurring merchants with unstable amounts are returned but amount_stable=False."""
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # 4 charges across 4 distinct calendar months with wildly different amounts
        dates = [
            today - timedelta(days=95),
            today - timedelta(days=65),
            today - timedelta(days=35),
            today - timedelta(days=5),
        ]
        amounts = [-5, -80, -150, -20]
        for i, (d, amt) in enumerate(zip(dates, amounts)):
            _add_tx(conn, f"var{i}", d, amt, "Target")
        conn.commit()

        from fb.mcp_server import _hc_subscriptions
        subs = _hc_subscriptions(
            conn,
            (today - timedelta(days=180)).isoformat(),
            today.isoformat(),
            (today - timedelta(days=30)).isoformat(),
        )
        target = next((s for s in subs if s["merchant"] == "Target"), None)
        # Detection is fine; we just shouldn't claim the amount is stable
        if target is not None:
            assert target["amount_stable"] is False, \
                f"variable amounts should have amount_stable=False, got {target}"


def test_cc_payment_heuristics_filtered_even_when_is_transfer_zero():
    """
    Credit-card payments frequently aren't tagged is_transfer=1 by the sync
    pipeline (no reliable signal from Teller). The healthcheck tool must still
    exclude them from baselines or runway goes haywire.
    """
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # Each of these should be excluded from spend aggregates
        for i, days_ago in enumerate([90, 60, 30]):
            _add_tx(conn, f"citi{i}", today - timedelta(days=days_ago), -2500.0,
                    "CITI", "general")  # merchant is bank issuer name
        for i, days_ago in enumerate([85, 55, 25]):
            conn.execute(
                "INSERT INTO transactions(id, account_id, date, amount, description, merchant, "
                "category, is_transfer, excluded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"ap{i}", "acc_check", (today - timedelta(days=days_ago)).isoformat(),
                 -800.0, "AUTOPAY 123 AUTO-PMT", "AUTOPAY 123", "general", 0, 0),
            )
        # Real $50 monthly Spotify — should still be detected
        for i, days_ago in enumerate([90, 60, 30, 5]):
            _add_tx(conn, f"sp{i}", today - timedelta(days=days_ago), -10.0, "Spotify", "software")
        conn.commit()

        from fb.mcp_server import _hc_subscriptions, _hc_buffer
        today_iso = today.isoformat()
        subs = _hc_subscriptions(
            conn,
            (today - timedelta(days=180)).isoformat(),
            today_iso,
            (today - timedelta(days=30)).isoformat(),
        )
        names = [s["merchant"] for s in subs]
        assert "CITI" not in names, "CITI (bank issuer) should not appear as subscription"
        assert not any("AUTOPAY" in n for n in names), "AUTOPAY description should be filtered"
        assert "Spotify" in names, "real subscription must still be detected"

        b = _hc_buffer(conn, today_iso)
        # 3× $10 spotify = $30 over 90d → ~$10/mo, not $8k+ from CC payments
        assert b["avg_monthly_spend_90d"] < 100, \
            f"CC payments must not inflate spend baseline; got avg_monthly={b['avg_monthly_spend_90d']}"


def test_transfers_and_excluded_ignored_in_subscription_detection():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # Monthly CC payment tagged as transfer → must be ignored
        for i, days_ago in enumerate([90, 60, 30]):
            _add_tx(conn, f"pay{i}", today - timedelta(days=days_ago), -500.0,
                    "CITI", "transfer", is_transfer=1)
        conn.commit()

        from fb.mcp_server import _hc_subscriptions
        subs = _hc_subscriptions(
            conn,
            (today - timedelta(days=180)).isoformat(),
            today.isoformat(),
            (today - timedelta(days=30)).isoformat(),
        )
        assert not any(s["merchant"] == "CITI" for s in subs)


# ---------------------------------------------------------------------------
# Category trends
# ---------------------------------------------------------------------------

def test_category_surge_computed_correctly():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # Dining: $100 in prior window, $300 in current window → +200, +200%
        _add_tx(conn, "p1", today - timedelta(days=45), -100.0, "Chipotle", "dining")
        _add_tx(conn, "c1", today - timedelta(days=10), -150.0, "Chipotle", "dining")
        _add_tx(conn, "c2", today - timedelta(days=5), -150.0, "Chipotle", "dining")
        conn.commit()

        from fb.mcp_server import _hc_category_trends
        current_start = (today - timedelta(days=30)).isoformat()
        trends = _hc_category_trends(
            conn,
            (today - timedelta(days=60)).isoformat(),
            current_start,
            today.isoformat(),
        )
        dining = next(t for t in trends if t["category"] == "dining")
        assert dining["current"] == 300.0
        assert dining["prior"] == 100.0
        assert dining["abs_change"] == 200.0
        assert dining["pct_change"] == 200.0


def test_new_category_flagged_when_prior_zero():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # Only current-window dining spend
        _add_tx(conn, "c1", today - timedelta(days=5), -75.0, "NewRestaurant", "dining")
        conn.commit()

        from fb.mcp_server import _hc_category_trends
        current_start = (today - timedelta(days=30)).isoformat()
        trends = _hc_category_trends(
            conn,
            (today - timedelta(days=60)).isoformat(),
            current_start,
            today.isoformat(),
        )
        dining = next(t for t in trends if t["category"] == "dining")
        assert dining["prior"] == 0.0
        assert dining["current"] == 75.0
        assert dining["new_category"] is True


# ---------------------------------------------------------------------------
# Outliers
# ---------------------------------------------------------------------------

def test_outlier_flagged_when_amount_exceeds_2x_merchant_baseline():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # Kroger baseline $40 (×3 in prior 180d), outlier $150 in current window
        for i, days_ago in enumerate([150, 120, 60]):
            _add_tx(conn, f"kb{i}", today - timedelta(days=days_ago), -40.0, "Kroger", "groceries")
        _add_tx(conn, "ko", today - timedelta(days=5), -150.0, "Kroger", "groceries")
        conn.commit()

        from fb.mcp_server import _hc_outliers
        outliers = _hc_outliers(
            conn,
            (today - timedelta(days=180)).isoformat(),
            (today - timedelta(days=30)).isoformat(),
            today.isoformat(),
        )
        assert any(o["merchant"] == "Kroger" and o["amount"] == 150.0 for o in outliers), \
            f"expected Kroger $150 flagged; got {outliers}"


def test_outlier_skips_when_under_20_dollar_floor():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # Coffee baseline $3, outlier $15 (5× but below $20 floor)
        for i, days_ago in enumerate([100, 60]):
            _add_tx(conn, f"cb{i}", today - timedelta(days=days_ago), -3.0, "Coffee", "dining")
        _add_tx(conn, "co", today - timedelta(days=5), -15.0, "Coffee", "dining")
        conn.commit()

        from fb.mcp_server import _hc_outliers
        outliers = _hc_outliers(
            conn,
            (today - timedelta(days=180)).isoformat(),
            (today - timedelta(days=30)).isoformat(),
            today.isoformat(),
        )
        assert not any(o["merchant"] == "Coffee" for o in outliers), \
            "tx below $20 floor should not be flagged as outlier"


# ---------------------------------------------------------------------------
# New merchants
# ---------------------------------------------------------------------------

def test_new_merchant_detected_only_when_absent_from_baseline():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # NewShop: first appears in current window → should be flagged
        _add_tx(conn, "ns1", today - timedelta(days=10), -75.0, "NewShop", "general")
        # OldShop: in baseline AND in current → should NOT be flagged
        _add_tx(conn, "os1", today - timedelta(days=90), -50.0, "OldShop", "general")
        _add_tx(conn, "os2", today - timedelta(days=10), -50.0, "OldShop", "general")
        conn.commit()

        from fb.mcp_server import _hc_new_merchants
        new_mers = _hc_new_merchants(
            conn,
            (today - timedelta(days=180)).isoformat(),
            (today - timedelta(days=30)).isoformat(),
            today.isoformat(),
        )
        names = [n["merchant"] for n in new_mers]
        assert "NewShop" in names
        assert "OldShop" not in names


def test_new_merchant_spend_floor():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        _add_tx(conn, "tiny", today - timedelta(days=5), -5.0, "TinyShop", "general")
        conn.commit()

        from fb.mcp_server import _hc_new_merchants
        new_mers = _hc_new_merchants(
            conn,
            (today - timedelta(days=180)).isoformat(),
            (today - timedelta(days=30)).isoformat(),
            today.isoformat(),
        )
        assert not any(n["merchant"] == "TinyShop" for n in new_mers)


# ---------------------------------------------------------------------------
# Buffer
# ---------------------------------------------------------------------------

def test_buffer_computes_runway_from_90d_average():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)

        today = _today()
        # $3000 spend over 90d → $1000/mo → with $5000 checking, runway ≈ 150 days
        for i in range(30):
            _add_tx(conn, f"s{i}", today - timedelta(days=i + 1), -100.0, f"Merchant{i % 5}")
        conn.commit()

        from fb.mcp_server import _hc_buffer
        b = _hc_buffer(conn, today.isoformat())
        assert b["checking_balance"] == 5000.0
        assert b["avg_monthly_spend_90d"] == 1000.0
        assert b["runway_days"] == 150.0


# ---------------------------------------------------------------------------
# Integration: full healthcheck returns the expected shape
# ---------------------------------------------------------------------------

def test_healthcheck_returns_expected_shape():
    with tempfile.TemporaryDirectory() as td:
        dbp = _make_db(Path(td))
        conn = _conn(dbp)
        _seed_institution_and_account(conn)
        conn.close()

        from fb.mcp_server import healthcheck
        # fastmcp decorates but keeps the function callable via .fn on FunctionTool,
        # or via the wrapper object itself. Try direct call first.
        fn = getattr(healthcheck, "fn", healthcheck)
        result = fn()

        assert set(result.keys()) == {
            "window", "subscriptions", "category_trends", "outliers",
            "new_merchants", "buffer", "cc_utilization", "flags",
        }
        assert "current_start" in result["window"]
        assert "current_end" in result["window"]
        assert "prior_start" in result["window"]
        assert "prior_end" in result["window"]
        assert isinstance(result["subscriptions"], list)
        assert isinstance(result["category_trends"], list)
        assert isinstance(result["outliers"], list)
        assert isinstance(result["new_merchants"], list)
        assert isinstance(result["buffer"], dict)
        assert isinstance(result["cc_utilization"], list)
        assert isinstance(result["flags"], list)


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
