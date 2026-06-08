# CLAUDE.md — FinanceBuddy

## What this is

A **local, single-user** personal finance tool. Pulls real bank data from Teller.io and exposes it to Claude Code via an MCP server so you can ask questions like "can I afford X?" or "how much did I spend on Y?" in conversation.

**No web UI, no hosted backend, no auth, no cloud DB.** Just:
- `fb/` — Python package (~8 files)
- `financebuddy.db` — SQLite at project root
- Teller mTLS certs at `certificate.pem` + `private_key.pem` (project root)
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

financebuddy.db     SQLite at project root
archive/            LEGACY — old FastAPI + Next.js SaaS code (dormant, kept for history)
  backend/          old Python API (don't run, references Supabase)
  frontend/         old Next.js UI
  docs/             SaaS-era design docs
```

Runtime env is `.venv/` at project root, created by `setup.sh`. Use `./.venv/bin/python` for one-off CLI invocations.

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
| `annotate_transaction` | Note / exclude / tag / mark-transfer one transaction |
| `record_cash_transaction` | Record a cash / off-bank expense or income Teller can't see (e.g. cash rent) |
| `classify_merchant` | Persist a merchant → taxonomy label (`income:salary`, `fixed:rent`, `variable:dining`, etc.) |
| `list_classifications` | View current merchant classifications |
| `auto_enrich` | Run heuristics (cadence + keyword) to bulk-classify merchants |
| `get_unclassified_merchants` | Merchants with meaningful spend that still need a label (for the LLM to fill in) |
| `healthcheck` | Structured Income / Fixed / Variable / Savings view using classifications |

**Amount convention (Teller, account-centric):**
- **Depository** (checking/savings): negative = outflow, positive = inflow. Standard.
- **Credit cards**: **positive = purchase** (charge to card), negative = payment/refund. Opposite sign!

The old `list_transactions` / `month_summary` / `top_merchants` / `spending_by_category` tools return **raw** Teller amounts. Filtering on `amount < 0` on a credit card MISSES purchases. The newer `healthcheck` / `auto_enrich` / `classify.FLOW_EXPR` normalize this internally to cash-flow convention (positive = inflow, negative = outflow regardless of account). When writing new queries that reason about direction across accounts, use the `(CASE WHEN a.type IN ('credit','loan') THEN -t.amount ELSE t.amount END)` flow expression.

Defaults to last 30 days when date range is omitted. Always confirm whether "last month" means calendar month (`month_summary`) or trailing 30 days.

## How to add a bank

```bash
cd $PROJECT_ROOT
./.venv/bin/python -m fb.connect_server
```

This starts a tiny server on `http://localhost:8787/` and opens the browser. User clicks **Connect**, completes Teller Connect, token saves directly to SQLite. Kill the server (Ctrl-C or `kill <pid>`) when done.

Environments: `sandbox` (fake data, `username`/`password`), `development` (real accounts, limited institutions), `production` (requires Teller approval). Set your own `TELLER_APP_ID` and `TELLER_ENV` in `.env`.

## How to sync

From the terminal:
```bash
./.venv/bin/python -m fb.sync             # all institutions
./.venv/bin/python -m fb.sync --institution <enr_...>
```

Or via MCP: ask and Claude calls `sync_now`. Teller returns ~90 days of history per call, so a full reseed after a gap pulls a bounded window — you keep earlier data because sync is upsert-only.

## Data model (SQLite)

```sql
institutions(id, name, access_token, enrollment_id, created_at, last_synced_at)
accounts(id, institution_id, name, type, subtype, currency, last_four,
         current_balance, available_balance, balance_updated_at)
transactions(id, account_id, date, amount, description, merchant, category,
             status, raw_json,
             note, excluded, tags, is_transfer)
merchant_classifications(merchant PRIMARY KEY, classification, confidence,
                         source, notes, created_at, updated_at)
```

`merchant_classifications` holds per-merchant taxonomy labels used by `healthcheck`. Taxonomy is fixed (see `fb.classify.TAXONOMY`):
- `income:{salary,refund,other}`
- `fixed:{rent,utility,subscription,membership,insurance,loan,other}`
- `variable:{groceries,dining,transport,shopping,health,entertainment,travel,personal,fees,other}`
- `transfer`

`source` is `user` (explicit confirmation — never overwritten by automation), `heuristic` (cadence/keyword detected), or `llm` (Claude classified from world knowledge).

`raw_json` is the full Teller payload — if you need a field the schema doesn't surface (e.g. `running_balance`, `details.processing_status`), parse it from there.

Schema changes: edit `fb/db.py` and add a migration block. No Alembic, just idempotent `ALTER TABLE` guarded with `PRAGMA table_info`.

## Gotchas

- **Access tokens are plaintext in SQLite.** Local-only, single user, low blast radius — but don't check `financebuddy.db` into git.
- **Teller Connect refuses `file://` origins.** Always serve `connect.html` via `connect_server.py`, not `open`.
- **The MCP server caches nothing.** Every tool call hits SQLite directly. That's fine at 1k tx.
- **Sync is blocking/synchronous.** A full sync with ~6 accounts takes a few seconds. Teller does rate-limit — if you see 429s, back off.
- **Transactions that later settle change ID sometimes.** Sync is upsert on the current ID, so a pending→posted transition may create a new row. Acceptable; dedupe at query time if it matters.
- **`archive/` is dead code.** The old FastAPI/Next.js SaaS lives there for history only. Nothing in the live app imports from it. Don't run it — it references Supabase (paused) and will error on startup.
- **~25% of transactions have `merchant = NULL`.** Teller only sets `merchant` from `details.counterparty.name`, which is absent for bank-initiated rows (rent ACH, interest, internal transfers, Zelle). The canonical merchant key is therefore `COALESCE(NULLIF(TRIM(merchant),''), description)` — see `classify.MERCHANT_KEY` and the healthcheck's `merchant or description` (mcp_server.py). **Any ad-hoc query that groups by raw `t.merchant` will silently drop these rows** (this once hid a $1,095 rent payment from spend totals). Use the COALESCE key when writing new aggregates.
- **Cash / off-bank spend is invisible.** Teller sees only bank + card activity. Rent paid in cash, Venmo/Zelle splits, cash tips won't appear, so "spent so far" / budget totals under-report unless you ask and record them via `record_cash_transaction` (stored on a synthetic `cash` depository account; participates in all aggregates, doesn't affect net worth).
- **Biweekly pay → two months/year have 3 paychecks.** 26 checks ÷ 12 ≈ 2.17/mo. A 3-paycheck month inflates windowed income and is NOT the run-rate — when budgeting a "normal" month, count 2. See the `fb-budget` skill for forward-budgeting methodology (income projection, arrears lag on new jobs, per-day/week run-rates).
- **`month_summary` double-counts credit card transactions as income.** The tool sums raw Teller amounts without normalizing for account type: credit card purchases (positive in Teller) are counted as *income*, and credit card payments/refunds (negative) are counted as *spend*. With a linked credit card, `month_summary` income is overstated and spend is understated by roughly the total of all CC charges that month. For accurate income/spend, use `healthcheck` (which uses the `FLOW_EXPR` normalization) or query SQLite directly with `CASE WHEN a.type IN ('credit','loan') THEN -t.amount ELSE t.amount END`. Also mark credit card autopayments as `is_transfer=true` via `annotate_transaction` — otherwise they inflate spend a second time on the depository side.

## Reconfiguring the MCP server

```bash
claude mcp list                                      # see registered servers
claude mcp get financebuddy                          # status
claude mcp remove financebuddy -s user               # unregister
claude mcp add -s user -e "PYTHONPATH=$PROJECT_ROOT" \
  -- financebuddy $PROJECT_ROOT/.venv/bin/python \
  -m fb.mcp_server                                   # re-register
```

`PYTHONPATH` is required so Python can import `fb` without a cwd.

## Typical user questions and how to answer them

- **"Can I afford a $X purchase?"** → `get_balances` + `month_summary` for current month + `list_transactions` filtered to recurring/upcoming fixed costs. Reason about post-purchase cash position vs. known outflows through month-end.
- **"What am I spending on subscriptions?"** → `list_transactions` with recent date range, group by merchant, flag the ones that recur monthly at similar amounts. (There's no `recurring` table anymore — infer it.)
- **"Keep me under $X this month"** → `month_summary` now + pace vs. days remaining. Proactively flag if MTD spend × (30/day_of_month) > target.
- **"What's new since last sync?"** → call `sync_now` first; it returns counts. Then `list_transactions` sorted DESC.
