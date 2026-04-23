# CLAUDE.md — FinanceBuddy

## What this is

A **local, single-user** personal finance tool. Pulls real bank data from Teller.io and exposes it to Claude Code via an MCP server so you can ask questions like "can I afford X?" or "how much did I spend on Y?" in conversation.

**No web UI, no hosted backend, no auth, no cloud DB.** Just:
- `fb/` — Python package (~5 files)
- `financebuddy.db` — SQLite at project root
- Teller mTLS certs at `backend/certificate.pem` + `backend/private_key.pem`
- `financebuddy` MCP server registered at user scope in `~/.claude.json`

## Architecture

```
fb/
  db.py             SQLite schema + connection helpers
  teller.py         Teller API client (mTLS, synchronous httpx)
  sync.py           CLI: Teller → SQLite upsert (accounts, balances, transactions)
  link_bank.py      CLI: save one enrollment to SQLite
  connect.html      Teller Connect browser page
  connect_server.py Localhost HTTP server (port 8787) that serves connect.html
                    and receives enrollment POSTs — needed because Teller Connect
                    refuses file:// origins
  mcp_server.py     fastmcp stdio server — the surface Claude Code talks to

financebuddy.db     SQLite, 3 tables: institutions, accounts, transactions
backend/            LEGACY — old FastAPI + SaaS code, dormant, untouched
frontend/           LEGACY — old Next.js UI, dormant, untouched
```

The `backend/` venv (`backend/venv/`) is what `fb/` runs under — it already has `httpx`, `fastmcp`, `sqlalchemy`, etc. Don't create a new venv.

## How to use from Claude Code

MCP server name: **`financebuddy`** (stdio, user scope). Tools exposed:

| Tool | What it does |
|---|---|
| `list_institutions` | Linked banks + last-synced time |
| `list_accounts` | All accounts with current + available balances |
| `get_balances` | Totals: assets, debt, net |
| `list_transactions` | Filter by date / account / merchant / amount |
| `spending_by_category` | Teller categories grouped, defaults to last 30 days |
| `top_merchants` | Highest spend by merchant |
| `month_summary` | Income / spend / net / tx count for a calendar month |
| `search` | LIKE on description + merchant |
| `sync_now` | Pull fresh data from Teller (all institutions, or one) |

**Amount convention (Teller):** negative = money out (spend), positive = money in (income/refund). The MCP tools return raw Teller amounts — flip the sign when reporting spend to the user.

Defaults to last 30 days when date range is omitted. Always confirm whether "last month" means calendar month (`month_summary`) or trailing 30 days.

## How to add a bank

```bash
cd /Users/jialanren/projects/financebuddy
./backend/venv/bin/python -m fb.connect_server
```

This starts a tiny server on `http://localhost:8787/` and opens the browser. User clicks **Connect**, completes Teller Connect, token saves directly to SQLite. Kill the server (Ctrl-C or `kill <pid>`) when done.

Environments: `sandbox` (fake data, `username`/`password`), `development` (real accounts, limited institutions), `production` (requires Teller approval). App ID `app_pn55bmnf8k4papve7o000` is currently wired for development.

## How to sync

From the terminal:
```bash
./backend/venv/bin/python -m fb.sync             # all institutions
./backend/venv/bin/python -m fb.sync --institution <enr_...>
```

Or via MCP: ask and Claude calls `sync_now`. Teller returns ~90 days of history per call, so a full reseed after a gap pulls a bounded window — you keep earlier data because sync is upsert-only.

## Data model (SQLite)

```sql
institutions(id, name, access_token, enrollment_id, created_at, last_synced_at)
accounts(id, institution_id, name, type, subtype, currency, last_four,
         current_balance, available_balance, balance_updated_at)
transactions(id, account_id, date, amount, description, merchant, category,
             status, raw_json)
```

`raw_json` is the full Teller payload — if you need a field the schema doesn't surface (e.g. `running_balance`, `details.processing_status`), parse it from there.

Schema changes: edit `fb/db.py` and add a migration block. No Alembic, just idempotent `ALTER TABLE` guarded with `PRAGMA table_info`.

## Gotchas

- **Access tokens are plaintext in SQLite.** Local-only, single user, low blast radius — but don't check `financebuddy.db` into git.
- **Teller Connect refuses `file://` origins.** Always serve `connect.html` via `connect_server.py`, not `open`.
- **The MCP server caches nothing.** Every tool call hits SQLite directly. That's fine at 1k tx.
- **Sync is blocking/synchronous.** A full sync with ~6 accounts takes a few seconds. Teller does rate-limit — if you see 429s, back off.
- **Transactions that later settle change ID sometimes.** Sync is upsert on the current ID, so a pending→posted transition may create a new row. Acceptable; dedupe at query time if it matters.
- **Don't touch `backend/` or `frontend/`** unless you're explicitly reviving the SaaS. They still reference Supabase (currently paused) and will error on startup.

## Reconfiguring the MCP server

```bash
claude mcp list                                      # see registered servers
claude mcp get financebuddy                          # status
claude mcp remove financebuddy -s user               # unregister
claude mcp add -s user -e "PYTHONPATH=/Users/jialanren/projects/financebuddy" \
  -- financebuddy /Users/jialanren/projects/financebuddy/backend/venv/bin/python \
  -m fb.mcp_server                                   # re-register
```

`PYTHONPATH` is required so Python can import `fb` without a cwd.

## Typical user questions and how to answer them

- **"Can I afford a $X purchase?"** → `get_balances` + `month_summary` for current month + `list_transactions` filtered to recurring/upcoming fixed costs. Reason about post-purchase cash position vs. known outflows through month-end.
- **"What am I spending on subscriptions?"** → `list_transactions` with recent date range, group by merchant, flag the ones that recur monthly at similar amounts. (There's no `recurring` table anymore — infer it.)
- **"Keep me under $X this month"** → `month_summary` now + pace vs. days remaining. Proactively flag if MTD spend × (30/day_of_month) > target.
- **"What's new since last sync?"** → call `sync_now` first; it returns counts. Then `list_transactions` sorted DESC.
