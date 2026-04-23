---
name: fb-healthcheck
description: Surface a financial health snapshot — income vs spend, fixed-cost breakdown, savings rate, subscription creep, outliers, cash buffer, credit-card utilization. Use when the user asks "how are my finances doing", "anything weird in my spending", "give me a financial checkup", "what's new in my spending", or any open-ended wellness question about their finances.
---

# fb-healthcheck — Financial wellness snapshot

Triggers on open-ended "how are things" finance questions. Produces a structured **Income / Fixed / Variable / Savings** picture using per-merchant classifications.

## When this skill fires

- "how are my finances", "how am I doing financially", "financial checkup", "any red flags"
- "anything weird in my spending", "what's new", "subscription creep", "am I eating out more"
- "run a healthcheck", "audit my spending"

Do NOT fire for specific purchase decisions (use `fb-affordability`) or pure lookups like "how much did I spend last week" (use the base `financebuddy` tools directly).

## The method

The flow has four steps: sync-check → auto-enrich heuristics → LLM fills in the unknowns → ask the user at most 2-3 high-impact questions → narrate.

### 1. Check staleness

Call `mcp__financebuddy__list_institutions` — if any `last_synced_at` is >24h old, offer to `sync_now`. Stale data → stale narrative.

### 2. Run heuristic auto-enrichment

Call `mcp__financebuddy__auto_enrich()`. Returns:
- `salary_classified` — merchants with biweekly/monthly inflows + stable amounts OR "PAYROLL" keyword in description
- `subscriptions_classified` — stable-amount monthly recurring $1-$200
- `keyword_classified` — merchants matching known keyword lists (COSTCO, KROGER, LYFT, GEICO, etc.)
- `rent_candidates` — $600-$6000 stable monthly outflows from depository that *aren't already classified* — candidates for user confirmation
- `skipped_user_override` — count of times a heuristic would have overwritten a user-confirmed entry

You are **not** expected to re-narrate this summary — it's diagnostic. Move straight to step 3.

### 3. LLM-classify the unknowns

Call `mcp__financebuddy__get_unclassified_merchants(min_spend=20, days=90)`. You get a list of merchants with sample descriptions, sample amounts, and counts. **Classify each one using world knowledge**, then write back via `mcp__financebuddy__classify_merchant(merchant, classification, source='llm', notes=...)`.

Taxonomy:
```
income:{salary,refund,other}
fixed:{rent,utility,subscription,membership,insurance,loan,other}
variable:{groceries,dining,transport,shopping,health,entertainment,travel,personal,fees,other}
transfer            — e.g. Zelle to self, payment to a person who is the user
```

Classification guide:
- **Restaurants / bars / cafés** (DONJUAN, HEYTEA, PROGRESSIVE GROUNDS, ZINGERMANS, HINODEYA, FANTUAN DELIVERY if prepared food) → `variable:dining`
- **Grocery stores / Asian markets / wholesale clubs** (TSAI GROCERY, KANBU MARKET) → `variable:groceries`
- **Rideshare / transit / gas** (WAYMO, UBER, flights on credit cards) → `variable:transport` (but **airlines are usually `variable:travel`**)
- **Travel-specific** (AIRBNB, EXPEDIA, AMERICAN/SOUTHWEST/DELTA AIRLINES, hotels) → `variable:travel`
- **Retail, department stores, home goods** → `variable:shopping`
- **Pharmacies, doctors, dentists** → `variable:health`
- **Movies, streaming (one-off), concerts, games** → `variable:entertainment`
- **Government/bank/IRS fees** → `variable:fees`
- **One-off big deposits** (client payments, refunds, insurance payouts) → `income:other`
- **Recurring large deposits that look like a salary** → `income:salary` (if heuristic missed it)
- **Zelle/Venmo to yourself, transfers between your own accounts, investment contributions (Robinhood, etc.)** → `transfer`. When a merchant name matches the user's name, it's almost always a self-transfer.

Don't invent classifications. If you truly don't know (obscure merchant with no description hints), use `variable:other` rather than skipping.

**Batch-call `classify_merchant` once per unknown.** Multiple tool calls in parallel are fine since they're independent writes.

### 4. Ask the user 1-3 targeted questions (only if needed)

Look at `auto_enrich`'s `rent_candidates` result. **If non-empty**, ask the user: "This $X monthly payment to `<MERCHANT>` looks like rent — is it?" If yes: `classify_merchant(merchant, 'fixed:rent', source='user')`. If no: `classify_merchant(merchant, 'variable:other' or 'transfer' depending, source='user')`.

Also scan `income:other` sources in the final healthcheck (step 5) for anything large/ambiguous. If there's a big inflow you're not sure is salary vs. refund vs. gift, ask. Cap at 3 questions total — don't interrogate.

### 5. Call healthcheck + get_balances

```
mcp__financebuddy__healthcheck()        # structured flow view
mcp__financebuddy__get_balances()       # net worth stocks
```

### 6. Narrate

Data tells stories. Lead with the story, then back it with numbers — don't open with a summary table.

#### 6a. Story pass (lead with this)

Before any totals, scan the data for 1-3 **stories** that explain what actually happened this window. A story is a cluster of signals that points to a life event, not a single merchant. Phrase tentatively ("looks like", "seems like", "reads like") unless the evidence is unambiguous.

Patterns to scan for:

- **Trip** — airline + lodging (Airbnb / hotel) + out-of-home-city dining or rideshare in a ≤10-day window. Name the destination if merchants geotag it ("SF + Palm Springs trip"). Two airlines to different hubs in one window = two trips, not one.
- **Work trip vs leisure** — weekday-heavy + chain hotel + airport rideshare + no entertainment → work. Weekend + Airbnb + bars/entertainment → leisure. Say which.
- **Move or new city** — merchant locations shift and *stay* shifted, plus home-goods bursts (IKEA, Home Depot, Target furniture, Wayfair) and a new recurring local grocery / coffee shop. One IKEA run alone is not a move.
- **New routine** — a merchant appearing 3+ times in the current window that wasn't in the prior window (new gym, new coffee shop, new commute pattern).
- **Car event** — auto parts + repair shop + unusual gas clustered in ≤30 days.
- **Health episode** — pharmacy + doctor/lab + possible urgent-care cluster.
- **Life admin season** — tax prep (Jan–Apr), insurance renewal, tuition, license/registration fees.
- **Big one-off purchase** — single transaction ≥2× the window's median non-fixed spend. Flag what it was, not just the amount.
- **Recurring inflows from people** — repeated Zelle/Venmo from the same person ≈ splitting rent, utilities, or shared trip costs.

Rules for stories:

- **≥2 independent signals** per story. One Airbnb charge is not a trip; an Airbnb + a flight + dining in that city is.
- **Ground every story in observable rows.** Mention the merchants that support it — the user should be able to verify.
- **Don't fabricate.** If a cluster is ambiguous, say so ("unclear whether the SF merchants were a trip or you're partly living there") or drop it.
- **Contrast with prior window** for "new" stories. The healthcheck's `new_merchants` field is a starting point but isn't enough alone — confirm with the top-merchants and category deltas.
- **Lead with the most interesting story**, not the largest dollar number. A routine $400 paycheck is not a story; a $400 ski pass is.

#### 6b. Health stamp + structured breakdown

After the story pass:

1. **Headline** (1 line): "Healthy / tight / red flags — N% projected savings rate, ~Xd runway."
2. **Income + projection**: actual window income + projected monthly (if cadence detected on primary salary). Mention one-off big deposits separately — these are often the seed of a story above.
3. **Fixed costs**: total + top line items with `notes` where interesting (rent, gym, subs). Call out new or changed fixed items.
4. **Variable spending**: total + top 3-4 categories + notable top merchants. Only call out categories that moved meaningfully vs. prior.
5. **Savings rate**: actual + projected monthly. Flag if <10%.
6. **Buffer**: liquid + runway + any CC >50% utilization.
7. **Anomalies**: outliers (merchant + amount + ratio), subscription price changes, new merchants only if >$100 or subscription-shaped *and not already absorbed into a story*.

## Visuals

The terminal renders markdown; it does not render images or SVG. Use inline ASCII bars + sparklines in the structured breakdown. If the user asks for a richer view ("show me a chart", "can I see this over time"), generate an HTML file on disk and print the `open` command.

### Inline ASCII bars (default, always on)

Use Unicode block chars: `█ ▉ ▊ ▋ ▌ ▍ ▎ ▏` (full through 1/8 block). Scale the longest bar to ~20 chars; everything else scales proportionally. Show the label, bar, and number on one line. Fixed-width so the bars align — wrap in a fenced code block.

```
Travel      ███████████████████▏ $1,196
Dining      ████████████▎         $770
Groceries   ███████▊              $482
Transport   █████▏                $315
Shopping    █▋                    $101
```

Use bars for: variable-category breakdown, top merchants (≤6), fixed-cost breakdown, CC utilization (color omitted, just "balance / limit"). Skip bars for single-value facts (net worth, savings rate) — prose is clearer.

### Sparklines (time series)

Use `▁▂▃▄▅▆▇█` scaled over the last N buckets. Good for 6–12 data points; useless beyond ~20 (no resolution). Label with the range.

```
Income (last 6 mo):   ▂▃▂▂█▃   spike = MATX $11k in April
Spending (last 6 mo): ▅▆▄▅▇▆   April elevated by SF trip
Net worth (last 6 mo): ▃▄▅▆▇█   trending up
```

Pull the underlying series with `mcp__financebuddy__month_summary` per month, or with `mcp__financebuddy__list_transactions` + manual bucket. Don't fabricate the shape — if you don't have the data, skip the sparkline.

### Deep-dive HTML (on user request)

Trigger: user explicitly asks for charts, "can I see this as a graph", "show me a breakdown", "visualize this". Don't volunteer HTML if they didn't ask — inline bars cover 90% of asks.

Flow:
1. Pull the data you need (additional `list_transactions` / `month_summary` calls if the healthcheck didn't already surface enough).
2. Write a self-contained HTML file to `/tmp/fb-healthcheck-YYYY-MM-DD.html` with inline `<script src="https://cdn.jsdelivr.net/npm/chart.js">` or hand-rolled inline SVG. No external CSS, no build step.
3. Print `open /tmp/fb-healthcheck-YYYY-MM-DD.html` so the user can launch it with one click.

Chart choices:
- **Stacked bar, monthly** — income / fixed / variable / savings over last 6–12 months
- **Line** — net worth trajectory, cumulative savings
- **Horizontal bar** — top N merchants or categories for a window
- **Treemap** — category → merchant hierarchy if the user wants "where did it all go"
- **Heatmap** — day-of-month spending pattern, or merchant cadence

Keep the HTML small (<100 KB). One page, one or two charts, a short headline at the top that matches the story-pass narrative. No dashboard sprawl — the terminal narration is still the primary artifact; HTML is a supplement.

### What NOT to visualize

- Don't bar-chart the story pass. Stories are prose.
- Don't sparkline a 30-day window as 30 buckets — it's noise. Roll up to weekly (4 buckets).
- Don't chart raw Teller amounts across mixed account types without applying the cash-flow sign convention — you'll get nonsense (credit-card purchases will subtract from spend).

## Healthcheck output shape

```
{
  window, income: {total, projected_monthly, sources: [...]},
  fixed: {total, groups: {rent, utility, subscription, membership, insurance, loan, other}, items: [...]},
  variable: {total, groups: {...}, top_merchants: [...]},
  savings: {income, fixed, variable, net, rate_pct, projected_monthly_net, projected_monthly_rate_pct},
  buffer: {checking_balance, total_liquid, avg_monthly_spend_90d, runway_days},
  cc_utilization: [{name, balance_owed, available_credit}, ...],
  unclassified: {total, merchants: [...]},          # should be small after step 3
  refunds_unattributed: float,                       # credit-card positive amounts w/o class
  anomalies: {outliers, new_merchants, subscription_price_changes},
  flags: [...]
}
```

## Sign convention

**Teller reports credit-card purchases as POSITIVE amounts** (opposite of depository). The healthcheck and classification heuristics normalize this internally — you see cash-flow convention: positive = inflow, negative = outflow, regardless of account.

## Classification persistence

User-confirmed classifications (source='user') are never overwritten by heuristics or LLM re-classification. If the user ever says "no, that's not rent, that's gift money to my brother", use `classify_merchant(..., source='user')` to lock it.

## What NOT to do

- Don't re-narrate the auto_enrich summary — it's diagnostic, not a story.
- Don't dump JSON.
- Don't ask more than 3 yes/no questions. One-time setup cost is fine; multi-turn interrogation is not.
- Don't ignore `unclassified` — if the total is >10% of variable spend, flag it and offer to classify in this session.
- Don't treat variable-amount recurring charges (groceries, gym with classes) as "subscription price changes" — only flag `subscription_price_up/down` entries, which are already gated on `amount_stable=True`.
- Don't narrate what the tool already handled (e.g., self-transfer exclusion).
- **Don't invent stories.** A single merchant is not a story. If you can't cite ≥2 supporting signals, skip it rather than pad. Tentative phrasing is fine; confident fabrication is not.
- **Don't moralize.** Narrate what happened ("looks like a Palm Springs trip"), not whether it was wise ("you should travel less"). The user asked for a picture, not advice.

## Tool restart

If `healthcheck` / `auto_enrich` / `classify_merchant` / `get_unclassified_merchants` aren't visible in the tool list, the MCP server needs a restart. Tell the user: exit Claude Code and reopen — the `financebuddy` stdio server reloads on session start.

## Example narration

> **Looks like you were in SF for a few days** — Airbnb $397, American Airlines $378, plus SF dining (Hinodeya Ramen, Progressive Grounds, Heytea). Reads like leisure, not work: weekend-clustered, Airbnb over a hotel.
>
> **Something also happened around the car** — Rock Auto $366 (parts) plus a visit to MDP Auto Tech. A repair, not routine.
>
> **Otherwise quiet.** Usual Kroger/Costco rhythm, LR2 rent on schedule, no new recurring charges.
>
> ---
>
> **Healthy.** 39% projected savings rate, ~6 months runway. Net $31k.
>
> **Income:** $17.6k this window — $6.2k from NUNCHI (biweekly, projects ~$6.7k/mo), $11k one-off from MATX.
>
> **Fixed: $1,266/mo.** LR2 rent $1,170, Claude AI $100, NVIDIA $10.
>
> **Variable: $2,859.**
> ```
> Travel      ███████████████████▏ $1,196
> Dining      ████████████▎         $770
> Groceries   ███████▊              $482
> Transport   █████▏                $315
> Shopping    █▋                    $101
> ```
> Travel drove the month (see trip above).
>
> **Spending last 6 mo:** `▅▆▄▅▇▆` — April elevated by the SF trip, otherwise flat.
>
> **Buffer:** $38.9k liquid. Costco Visa at 40% util — watchable.
