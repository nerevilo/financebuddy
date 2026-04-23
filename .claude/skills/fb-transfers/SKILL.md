---
name: fb-transfers
description: Exclude self-transfers (credit card payments, account-to-account moves) when aggregating spend or income. Use whenever you sum, group, or compare transaction amounts — "how much did I spend", "total spending", "spending by category/merchant", "monthly spend", "net cash flow", "income this month".
---

# fb-transfers — Don't double-count money moving between your own accounts

A silent correctness bug: if you sum negative amounts across all accounts without filtering transfers, you count a credit card payment as BOTH a "spend" (bank → card) AND the original purchases on that card. Same dollars, counted twice. Similarly, a transfer from checking to savings looks like an outflow, but it's not spend.

## When this skill fires

Any aggregation question: "how much did I spend", "total outflow", "category breakdown", "top merchants", "income", "net", "budget". Also fires on `month_summary`, `spending_by_category`, `top_merchants` tool use.

## The filter

Before summing, exclude transactions matching any of:

1. **Teller category `transfer`** — primary signal. `transactions.category = 'transfer'`.
2. **Credit card payments** — descriptions like `AUTOPAY`, `ONLINE PAYMENT`, `PAYMENT THANK YOU`, `CC PAYMENT`, `AUTOMATIC PAYMENT`, `MOBILE PAYMENT`. Usually show up as positive on the card account and negative on the bank account.
3. **Paired cross-account transactions** — a negative amount on account A and a positive amount of the same absolute value on account B within ±2 days. Both sides of the pair must be excluded.
4. **Merchant descriptions** containing the user's own bank names (e.g., `TRANSFER TO CHASE SAVINGS`, `ZELLE FROM SELF`).

## How to apply it

- **`month_summary`** returns raw totals. The tool itself may or may not filter — treat its output as untrusted for this purpose. If doing precise spend math, re-query `list_transactions` for the month and filter in post.
- **`spending_by_category`** — already groups by category, so explicitly note and subtract the `transfer` bucket before reporting "total spend". Don't show `transfer` as a category in user-facing breakdowns.
- **`top_merchants`** — filter out merchants whose transactions are all `category = transfer`. Chase, Capital One, American Express payments frequently appear as "top merchants" otherwise — they're not spend.
- **`list_transactions`** — when the user asks "show me my biggest transactions" with intent of "biggest spends", filter transfers out and say so. If they literally want all transactions, don't.

## Reporting

When you've filtered, say so in one line: *"(excluded $X in transfers between your own accounts)"*. This lets the user cross-check against raw bank statements, which include transfers.

## When NOT to filter

- User explicitly asks about transfers: "how much did I move to savings this month".
- User asks about account balances, not flows.
- Income questions where a positive from a known employer should count (these are not transfers; don't over-filter).

## Quick sanity check

If your reported "monthly spend" is >1.5× the sum of all purchase-category amounts, you probably didn't filter transfers. Recompute.
