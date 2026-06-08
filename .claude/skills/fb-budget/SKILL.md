---
name: fb-budget
description: Forward-looking budgeting for a specific period — project income, tally what's been spent so far (including cash), and tell the user how much is left to spend on a category (food, discretionary, etc.). Use for "budget for June", "what's my projected income", "how much can I spend on groceries/eating out", "how much do I have left this month", "what's my per-day/per-week food budget", or income-gap planning around a job change.
---

# fb-budget — How much is left to spend, this period

Distinct from the other finance skills:
- **fb-affordability** = one purchase decision ("can I afford $X").
- **fb-healthcheck** = retrospective wellness snapshot ("how are my finances").
- **fb-budget** = *forward* planning for a period: project income, subtract committed + spent, hand back a spendable envelope (often per-category, often per-day/week).

This is conversational and iterative. The user refines ("count it as 6k not 9", "we paid rent in cash", "I got a new job"). Carry their corrections forward — don't re-derive from scratch each turn.

## The method

### 1. Project income for the period — don't just annualize a paycheck

Pull recent inflows: `mcp__financebuddy__list_transactions` (last 60–90d) or `healthcheck` (it already computes `income.projected_monthly` from salary cadence). Then **reason about the actual period**, accounting for:

- **Pay cadence vs. calendar.** Biweekly = 26 checks/yr = ~2.17/mo, so **two months a year have 3 paychecks**. A 3-paycheck month is NOT your run-rate — when the user asks for a normal-month budget, count 2. Confirm which months get 3 by walking the actual pay dates forward 14 days at a time.
- **Job changes.** New job starting mid-period almost always pays **in arrears** — first paycheck lands 2–4 weeks after the start date, often in the *following* month. Don't count new-job income until it realistically clears. Treat it as upside.
- **Income ending.** If a job ends (last paycheck date known), model the gap. The dangerous month is usually the one *after* an income source ends and before the next starts — flag it explicitly even when the user only asked about the current month.
- **One-offs.** Tax refunds, bonuses, a 3rd paycheck, reimbursements — list them separately from recurring income. They fund splurges/moves; don't let them inflate the baseline.
- **Household.** If the user says "we"/"our" and a partner has income (stipend, salary), sum the household and say so. Food/rent are usually shared.

Output: **recurring income + one-offs, itemized**, with a clear "this is your run-rate vs. this is unusual" split.

### 2. Tally what's been spent so far — including money the tracker can't see

For the elapsed part of the period, sum real spend with the **cash-flow sign convention and transfers excluded** (see `fb-transfers` — this is mandatory; never use raw `month_summary`, it double-counts credit cards and counts CC purchases as income).

**Cash and off-bank spend is invisible.** Teller only sees bank/card activity. If the user mentions rent paid in cash, Venmo splits, or any off-bank expense, it will NOT be in the data and you'll under-report "spent so far". **Ask** about large known cash outflows (rent especially), and **record them** with `mcp__financebuddy__record_cash_transaction` so future runs include them. A budget that silently omits a $1,700 cash rent is wrong.

Separate **one-time costs** (move expenses, a deposit, annual prepaid phone, registration fees) from **recurring living**. One-offs are real cash gone *this period* — they don't free up budget — but they don't represent ongoing burn, so strip them when projecting future months.

### 3. Hand back the spendable envelope

The frame the user can run in their head:

```
period income
− spent so far (incl. cash)
− remaining necessities (rent if unpaid, subs, utilities, transit)
− desired savings
= free to spend on <category>
```

Whatever they don't spend, they save — say that. Then translate to **the unit they think in**:

- **Per-week** (for grocery trips): daily rate × 7.
- **Per-day** (for food): total ÷ days.
- **Per-category envelope** with a hard ceiling.

### 4. Run-rates from real consumption, not just totals

When the user wants "how much per day" for food/groceries, use their lived signal ("the Trader Joe's run lasted 4 days"), not just dollar totals:

- **Bulk/pantry distorts daily rate.** A Costco run or a stock-up (condiments, frozen, paper goods) is *front-loaded inventory*, not that day's consumption. Pull non-perishables and household goods out of the per-day food number — amortize them over weeks. Ask "how long did that last / is it mostly staples?" when a grocery line is large.
- **Groceries and dining trade against each other** within one food envelope. A lean cooking week funds a meal out with no net change — tell the user they're one budget, not two.
- **Timing the next trip.** From "X lasted N days", project the next shop date and a per-trip dollar target. Note that the trip right after a stock-up runs *lighter* (pantry already covered).

### 5. Always surface the runway/gap risk

Close with the forward risk, even if unasked: if an income gap is coming (job ending, between-jobs lag), name it and point at the cushion (this period's surplus, one-off income) that covers it. The reason to budget lean *now* is usually a lean month *next*.

## Recording cash / off-bank transactions

`mcp__financebuddy__record_cash_transaction(amount, description, date=None, kind="expense", category=None)`:
- `amount` is a positive magnitude; `kind="expense"` (outflow) or `kind="income"` (inflow). The tool stores it on a synthetic `cash` account with the correct sign.
- Use for: cash rent, cash tips, Venmo/Zelle the user describes, gifts, any spend they tell you about that won't be in Teller.
- These rows participate in all aggregates (they're real `transactions` rows), so once recorded, "spent so far" is correct on every future run.
- Don't double-record something already in the data — check `search`/`list_transactions` first if unsure.

## What NOT to do

- **Don't annualize a single paycheck or a 3-paycheck month** into a monthly run-rate.
- **Don't count new-job income before it clears** (arrears lag).
- **Don't use `month_summary` raw** for spend/income totals — it double-counts credit cards (see `fb-transfers`).
- **Don't ignore cash** — ask about and record large off-bank outflows.
- **Don't put bulk/pantry purchases into the per-day food rate** — they're inventory.
- **Don't prescribe a budget the user didn't ask for.** They often know their own constraints ("I know how long that lasts"); give them the numbers and the per-unit rate, let them decide. Offer a recommendation only if asked.
- **Don't moralize.** Report the envelope; don't judge the spending.

## Persisting what you learn

When the user states durable budgeting facts — rent amount and whether it's cash, household members and their income, a job change with dates, a target food number — write them to project memory so the next session doesn't re-ask. (See the memory instructions; these are `project`-type facts.)
