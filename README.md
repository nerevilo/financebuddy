# FinanceBuddy

A **local, single-user** personal finance tool that lives inside Claude Code. 

It pulls real bank data from [Teller.io](https://teller.io) into a local SQLite
file, then exposes it to Claude through an MCP server — so you can ask things
like:

> *"Can I afford a $2k flight in May?"*
> *"What's my net cash flow this month?"*
> *"How much did I spend on dining last quarter?"*

…and Claude answers with your actual numbers.

No web UI, no hosted backend, no cloud DB. Your data stays on your machine.

---

## Setup (one shot)

You need:

- **macOS or Linux** with `python3` ≥ 3.10
- **[Claude Code](https://claude.com/claude-code)** installed (`claude` on PATH)
- A free **[Teller.io](https://teller.io)** account (development tier is free)

Then:

```bash
git clone https://github.com/<you>/financebuddy.git
cd financebuddy
bash setup.sh
```

`setup.sh` will:

1. Create `.venv/` and install dependencies (`httpx`, `fastmcp`).
2. Check for your Teller mTLS certs at `certificate.pem` + `private_key.pem`.
   If they're missing, it tells you exactly where to get them.
3. Copy `.env.example` → `.env` (you'll set your own `TELLER_APP_ID` here).
4. Register the `financebuddy` MCP server with Claude Code (user scope).
5. Launch Teller Connect at `http://localhost:8787/` so you can link your
   first bank account.

Re-running `setup.sh` is safe — every step is idempotent.

---

## Daily use

Open Claude Code anywhere on your machine and just talk to it:

| You say | Claude calls |
|---|---|
| "what's my net worth" | `get_balances` |
| "how much did I spend on groceries last month" | `month_summary`, `list_transactions` |
| "sync my accounts" | `sync_now` |
| "any new charges since yesterday" | `sync_now` then `list_transactions` |
| "anything weird in my spending" | `healthcheck` |

The full list of tools lives in [CLAUDE.md](./CLAUDE.md).

You can also drive it from the shell:

```bash
./.venv/bin/python -m fb.sync                 # pull fresh data
./.venv/bin/python -m fb.connect_server       # link another bank
```

---

## How data gets cleaned up for Claude

Raw Teller data is messy: credit-card amounts have the opposite sign of
checking accounts, transfers between your own accounts double-count as both
income and spend, and merchant names are often cryptic strings. FinanceBuddy
cleans this up in three layers so Claude can answer real questions.

**1. Sync writes Teller's payload almost verbatim.**
`fb/sync.py` upserts each transaction as-is. Only `category` and `merchant`
are lifted out of `details`; everything else stays in `raw_json`. No
normalization happens here — the goal is to never lose Teller data.

**2. Queries normalize at read time.**
`fb/classify.py` defines a `FLOW_EXPR` SQL fragment that flips the sign on
credit/loan accounts so positive always means inflow and negative means
outflow, regardless of account type. Every newer query joins `accounts` and
uses this expression. Per-row noise filters (`excluded`, `is_transfer`)
hide manually-flagged junk and internal transfers from aggregates.

**3. Merchant classification (`auto_enrich`).**
A merchant taxonomy (`income:salary`, `fixed:rent`, `variable:dining`, …)
is built up by combining four sources:

- **Salary detection** — recurring positive deposits on depository accounts
  with stable amounts and biweekly/monthly cadence, or unambiguous payroll
  keywords (`PAYROLL`, `DIRECT DEP`).
- **Subscription detection** — stable monthly outflows $1–$200 across ≥3
  months, with investment contributions excluded so Robinhood doesn't get
  labeled as Netflix.
- **Keyword scan** — substring matches against curated lists of utilities,
  gyms, insurance providers, streaming services, grocers, gas stations, etc.
- **LLM gap-fill** — `get_unclassified_merchants` returns the remaining
  merchants with meaningful spend (pre-filtered to drop card-payment and
  brokerage noise), Claude classifies them from world knowledge, and the
  labels persist via `classify_merchant`.

User-confirmed labels (`source='user'`) are never overwritten by automation.
The `healthcheck` tool reads the resulting taxonomy to produce a structured
Income / Fixed / Variable / Savings rollup — which is what makes "anything
weird in my spending" a question Claude can actually answer.

---

## What's in the repo

```
fb/                      ~6 file Python package — the whole app
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
- `financebuddy.db` is plain SQLite. Your access tokens are stored unencrypted —
  fine for a single-user laptop, but **don't commit the DB or the certs**
  (the included `.gitignore` already blocks `*.pem`, `*.db`, and `.env`).
- The MCP server is registered at **user scope** — only your account on this
  machine can talk to it. There is no network listener.

  Important: Advice from Claude should be taken carefully and owner of this repo is not responsible for any decisions made.

---

## Troubleshooting

**`claude mcp list` doesn't show `financebuddy`.**
Re-run `bash setup.sh`. If `claude` isn't on your PATH, install Claude Code first.

**`Teller certs missing` error on sync.**
Drop your certs at `./certificate.pem` and `./private_key.pem`, or set
`TELLER_CERT_PATH` / `TELLER_KEY_PATH` env vars to wherever you keep them.

**`429 Too Many Requests` from Teller.**
You're rate-limited. Wait a minute and re-run `fb.sync`.

**Want a fresh start?**
`rm financebuddy.db && bash setup.sh` will wipe local data and re-link.
