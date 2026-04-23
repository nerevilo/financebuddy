---
name: fb-affordability
description: Answer "can I afford X?" and similar purchase-decision questions about the user's personal finances. Use when the user asks whether they can afford a specific purchase, whether a spend is safe, or wants a decision on a discretionary expense.
---

# fb-affordability — Purchase decision methodology

Triggered when the user is making a spend decision: "can I afford $X", "is it okay to buy Y", "should I get Z this month", "will I have enough for ___".

Do NOT answer from balance alone. A 5-step projection:

## The method

1. **Cash position** — call `mcp__financebuddy__get_balances`. Available (not current) is what matters. Separate liquid assets from credit lines.

2. **MTD burn** — call `mcp__financebuddy__month_summary` for the current calendar month. Flip sign on spend (Teller: negative = out).

3. **Fixed outflows remaining this month** — recurring bills not yet hit. Use `mcp__financebuddy__list_transactions` over the last 60–90 days, group by merchant, find monthly-cadence items (same merchant, ±5% amount, ≥2 occurrences ~30d apart) whose typical billing day is after today. Rent, utilities, subscriptions, insurance, loan payments.

4. **Discretionary pace** — `(MTD spend − recurring already hit this month) / days elapsed × days remaining`. That's the projected variable spend through month-end.

5. **Post-purchase projection** —
   ```
   projected_eom_cash = available − purchase − (fixed_outflows_remaining) − (discretionary_pace_remaining)
   ```
   Answer structure:
   - Current available: $X
   - After purchase: $X − $P
   - Expected remaining fixed bills: −$F  (list them)
   - Projected variable spend through month-end: −$V
   - **Projected cash on [last day of month]: $Y**
   - Verdict with buffer: safe if Y > ~1 month of typical fixed expenses; tight if Y > 0 but < that; risky if Y < 0.

## Rules

- Exclude transfers when computing spend (see `fb-transfers` skill — credit card payments, account-to-account moves inflate "spend").
- If the purchase is >20% of projected EOM cash, call it out explicitly regardless of verdict.
- If the user has a credit card with available credit, that's a fallback but not a yes — mention it as "you could float it on [card] but EOM cash goes negative".
- If sync is stale (>24h since `last_synced_at` from `list_institutions`), call `sync_now` first. Numbers based on week-old data are worse than asking the user to wait 10 seconds.
- Don't lecture. The user asked a yes/no. Give the projection, state the verdict, stop.

## Example output shape

> Available cash: $4,200. After a $800 purchase: $3,400.
> Fixed bills left this month: rent $1,800, Verizon $90, Spotify $12 → $1,902.
> Variable pace: $45/day × 11 days left ≈ $495.
> **Projected May 31 cash: ~$1,000.** Safe but thin — that's ~2 weeks of runway if income is delayed. Fine if your next paycheck lands before then.
