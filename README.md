# FinanceBuddy

**Rocket Money charges you $8/mo to tell you that you spent too much on DoorDash.**

If you already pay for Claude Code, your finance copilot is one `git clone` away.

FinanceBuddy wires your real bank accounts (via [Teller.io](https://teller.io)) into Claude through MCP — locally. Ask in plain English:

> *"Can I afford a $2k flight in May?"*
> *"What subscriptions am I leaking on?"*
> *"How am I tracking vs last month?"*

Claude answers with your actual numbers. No dashboards. No CSV exports. No "AI Insights" upsell screen.

---

## Why this exists

- **You already pay for Claude.** The smartest LLM on the planet lives in your terminal. It should know how broke you are.
- **Mint is dead. Rocket Money is mid.** Both upsell you. Both ship your data somewhere downstream.
- **Your bank data shouldn't live in someone else's S3 bucket.** SQLite. On your laptop. That's the whole architecture.
- **~200 lines of glue beats a SaaS subscription.** The repo is ~8 files. You can read it in a coffee.

---

## The trust model, in one paragraph

Your transactions live in `financebuddy.db` — a SQLite file at the project root that you can `rm` any time. Nothing leaves your machine except calls to Teller (your bank's API, mTLS-pinned). The only LLM that ever sees the numbers is whichever model Claude Code is wired to in the session you're chatting in — so the floor of your trust is *"how much do I trust Anthropic with the contents of an MCP tool response."* That's a lower bar than *"trust Rocket Money to never get breached, sold, or acquired by Intuit."* You decide.

---

## What you get

- **14 MCP tools** — `get_balances`, `month_summary`, `spending_by_category`, `top_merchants`, `healthcheck`, `search`, `sync_now`, and friends.
- **Auto-classifier** that learns your salary cadence, finds subscription creep, and flags self-transfers so "dining" isn't inflated by your Schwab top-up.
- **Sign normalization** for the eternal credit-card vs checking-account sign war, so "spend" actually means spend.
- **One-shot Teller Connect flow** at `localhost:8787` — link a bank in 30 seconds, token persists straight to SQLite.

---

## Setup

You need:

- macOS or Linux with `python3 ≥ 3.10`
- [Claude Code](https://claude.com/claude-code) installed (`claude` on PATH)
- A free [Teller.io](https://teller.io) account (dev tier is free and hits real banks)

Then:

```bash
git clone https://github.com/<you>/financebuddy.git
cd financebuddy
bash setup.sh
```

`setup.sh` is idempotent. It creates `.venv/`, installs deps (`httpx`, `fastmcp`), checks your Teller mTLS certs, registers the `financebuddy` MCP server with Claude Code at user scope, and pops Teller Connect open so you can link your first bank. Re-run it whenever.

---

## Daily use

Open Claude Code anywhere on your machine. Just talk to it.

| You say | Claude calls |
|---|---|
| "what's my net worth" | `get_balances` |
| "how much on groceries last month" | `month_summary`, `list_transactions` |
| "sync my accounts" | `sync_now` |
| "anything weird in my spending" | `healthcheck` |
| "can I afford $2k for SF→Tokyo?" | `get_balances` + `month_summary` + reasoning |

Full tool list in [CLAUDE.md](./CLAUDE.md).

Shell access if you want it:

```bash
./.venv/bin/python -m fb.sync                 # pull fresh data
./.venv/bin/python -m fb.connect_server       # link another bank
```

---

## How the data gets cleaned up for Claude

Raw bank data is gross. Credit cards have the opposite sign of checking. Transfers double-count as both income and spend. Merchant strings look like `SQ *AC SF CA` and `AMZN MKTP US*M3K91`. We unscrew it in three layers:

**1. Sync writes Teller's payload almost verbatim.**
`fb/sync.py` upserts each transaction as-is. Only `category` and `merchant` get lifted out of `details`; everything else stays in `raw_json`. No normalization happens here — the goal is to never lose Teller data.

**2. Queries normalize at read time.**
`fb/classify.py` defines a `FLOW_EXPR` SQL fragment that flips the sign on credit/loan accounts so positive always means inflow and negative means outflow, regardless of account type. Every newer query joins `accounts` and uses this expression. Per-row noise filters (`excluded`, `is_transfer`) hide manually-flagged junk and internal transfers from aggregates.

**3. Merchant classification (`auto_enrich`).**
A merchant taxonomy (`income:salary`, `fixed:rent`, `variable:dining`, …) is built up by combining four sources:

- **Salary detection** — recurring positive deposits on depository accounts with stable amounts and biweekly/monthly cadence, or unambiguous payroll keywords (`PAYROLL`, `DIRECT DEP`).
- **Subscription detection** — stable monthly outflows $1–$200 across ≥3 months, with investment contributions excluded so Robinhood doesn't get labeled as Netflix.
- **Keyword scan** — substring matches against curated lists of utilities, gyms, insurance providers, streaming services, grocers, gas stations, etc.
- **LLM gap-fill** — `get_unclassified_merchants` returns the remaining merchants with meaningful spend (pre-filtered to drop card-payment and brokerage noise), Claude classifies them from world knowledge, and the labels persist via `classify_merchant`.

User-confirmed labels (`source='user'`) are never overwritten by automation. The `healthcheck` tool reads the resulting taxonomy to produce a structured Income / Fixed / Variable / Savings rollup — which is what makes "anything weird in my spending" a question Claude can actually answer.

---

## What's in the repo

```
fb/                      ~8 file Python package — the whole app
  db.py                  SQLite schema + connection helpers
  teller.py              Teller API client (mTLS)
  sync.py                CLI: Teller → SQLite upsert
  link_bank.py           CLI: save one enrollment
  connect.html           Teller Connect browser page
  connect_server.py      Localhost server (port 8787) for Teller Connect
  classify.py            Merchant taxonomy + auto-classify heuristics
  mcp_server.py          fastmcp stdio server — what Claude talks to

financebuddy.db          Your data. Gitignored. Don't commit it.
certificate.pem          Teller mTLS cert. Gitignored.
private_key.pem          Teller mTLS key. Gitignored.
.env                     TELLER_APP_ID, TELLER_ENV. Gitignored.
setup.sh                 One-shot installer (above).
requirements.txt         httpx, fastmcp.
CLAUDE.md                Project notes for Claude Code (read this).

archive/                 Old SaaS-era code (FastAPI + Next.js). Dormant.
                         Kept for history; nothing in the live app references it.
```

---

## Privacy & safety

- Everything is **local**. No telemetry, no third-party servers besides Teller.
- `financebuddy.db` is plain SQLite. Access tokens are stored unencrypted — fine for a single-user laptop, but **never commit the DB or the certs** (the included `.gitignore` blocks `*.pem`, `*.db`, and `.env`).
- The MCP server is registered at **user scope** — only your account on this machine can talk to it. No network listener.
- Claude has opinions about your money. They are not financial advice and the author isn't liable for what you do with them. Sanity-check before you YOLO.

---

## Troubleshooting

**`claude mcp list` doesn't show `financebuddy`.**
Re-run `bash setup.sh`. If `claude` isn't on your PATH, install Claude Code first.

**`Teller certs missing` error on sync.**
Drop your certs at `./certificate.pem` and `./private_key.pem`, or set `TELLER_CERT_PATH` / `TELLER_KEY_PATH` env vars to wherever you keep them.

**`429 Too Many Requests` from Teller.**
You're rate-limited. Wait a minute and re-run `fb.sync`.

**Want a fresh start?**
`rm financebuddy.db && bash setup.sh` wipes local data and re-links.
