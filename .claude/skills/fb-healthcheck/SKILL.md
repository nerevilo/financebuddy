---
name: fb-healthcheck
description: Surface a financial health snapshot — subscription creep, category spending shifts, outlier transactions, new merchants, cash buffer, credit-card utilization. Use when the user asks "how are my finances doing", "anything weird in my spending", "give me a financial checkup", "what's new in my spending", or any open-ended wellness question about their finances.
---

# fb-healthcheck — Financial wellness snapshot

Triggers on open-ended "how are things" finance questions. The heavy lifting lives in a single MCP tool that returns pre-computed signals; your job is to narrate them.

## When this skill fires

- "how are my finances", "how am I doing financially", "financial checkup", "any red flags"
- "anything weird in my spending", "what's new", "subscription creep", "am I eating out more"
- "run a healthcheck", "audit my spending"

Do NOT fire for specific purchase decisions (use `fb-affordability`) or pure lookups like "how much did I spend last week" (use the base `financebuddy` tools directly).

## The method

1. **Check staleness first.** Call `mcp__financebuddy__list_institutions` — if any `last_synced_at` is >24h old, offer to `sync_now` before analyzing. Stale data → stale narrative.

2. **Call the healthcheck tool.** `mcp__financebuddy__healthcheck()` with defaults (30d vs. prior 30d, 180d baseline). Returns:
   - `subscriptions` — recurring merchants (≥3 months) with `amount_stable` flag and `amount_change_pct`
   - `category_trends` — MoM spend delta per category, sorted by absolute change
   - `outliers` — individual tx >2× merchant baseline, floor $20
   - `new_merchants` — first-seen merchants in current window, floor $20
   - `buffer` — checking, total liquid, avg monthly spend (90d), runway in days
   - `cc_utilization` — credit card balances + available credit
   - `flags` — machine-readable high-level signals (`new_subscription`, `category_surge`, `low_runway`, etc.)

3. **Also call `get_balances`** for net worth context — the healthcheck focuses on flows, not stocks.

4. **Narrate, don't dump.** The tool gives signals; you give the story.

## Narration guide

Structure the response as:

1. **Headline verdict** (1 line): "healthy / tight / watch your X" based on flags + buffer.
2. **Net worth + buffer** (1 line): `total_liquid`, `runway_days`, any cc_utilization >50% of available.
3. **Subscriptions** (only if interesting):
   - Stable recurring (REPLIT $24, Netflix $15) → just list, 1 line
   - Unstable recurring (LR2 ARCLUB, CLAUDE AI, KROGER) → call them out as "regular but variable" with avg + range
   - New ones that look like subscriptions (months_seen ≥ 3, amount_stable, new=True) → flag prominently
   - Price changes on stable subs → flag loudly (these are the subscription-creep signals the user wants)
4. **Category shifts** — only call out categories with `abs_change >= $50` AND `pct_change >= 25%` (or `new_category=True` with meaningful $). Dining spikes, groceries dropping, etc.
5. **Outliers** — if any, name them by merchant + amount + ratio. "$300 at Kroger — 4× your usual $70."
6. **New merchants** — name + amount. Often innocuous (one-off), but flag if >$100 or pattern suggests new subscription.
7. **Action prompt** — end with "want me to [sync / drill into X / tag self-transfers]?" only if there's a real next step.

## Filtering rules (already applied by the tool)

The healthcheck tool already excludes:
- `is_transfer=1` and `excluded=1` transactions
- Credit-card payments (AUTOPAY, ONLINE PAYMENT, etc., bank issuer names like CITI/CHASE)
- Capital One self-transfers (`Withdrawal to <acct> XXXXXXX...`)
- PayPal/Zelle INST XFER (self-moves)
- Investment contributions (category = 'investment')

You do not need to re-apply the `fb-transfers` skill manually — the numbers returned are already clean. But if the user asks why a specific transaction was excluded, check the patterns above.

## Interpreting buffer

- `runway_days` uses **total liquid** (checking + savings), not checking alone. Savings are instantly transferable — counting only checking dramatically understates real runway.
- A runway <60 days triggers a `low_runway` flag. Treat that as urgent.
- `avg_monthly_spend_90d` is 90d average divided by 3 — smooths out one-off big months.

## What NOT to do

- Don't restate every category from `category_trends` — the tool returns all of them, sorted by absolute change. Only mention ones that moved meaningfully.
- Don't treat unstable-amount recurring merchants (groceries, restaurants, gym with annual + monthly) as "price changes." The tool's `amount_stable=False` is the signal — if you see it, don't narrate a "subscription price increase."
- Don't dump JSON. Synthesize.
- Don't recommend actions the user didn't ask for. "Your buffer is healthy" is enough; don't pivot into unsolicited advice on IRA contributions.

## Example output shape

> Finances look healthy. Net $31k, ~300 days runway on current pace.
>
> **Subscriptions:** REPLIT $24/mo stable. Recurring-but-variable: Claude AI $20–100 (avg $63), LR2 ARCLUB $80–1115 (climbing gym — looks like a mix of membership + classes).
>
> **No category surges** vs. last month — dining actually down 50%, groceries slightly up.
>
> **Flagged:** $36 at Kroger on 4/14 is ~3× your usual ($12) — worth a glance, probably nothing.
>
> **New merchants this month:** DONJUAN $36, IKEA $24, STATE OF MI $27 (likely a tax/fee). No new subscriptions.

## Tool restart

If `mcp__financebuddy__healthcheck` is not visible in the tool list, the MCP server needs a restart. Tell the user: exit Claude Code and reopen — the `financebuddy` stdio server reloads on session start.
