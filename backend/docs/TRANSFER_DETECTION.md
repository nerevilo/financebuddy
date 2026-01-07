# Transfer Detection System

## Overview

The transfer detection system identifies transactions that should be excluded from spending calculations. It uses a **configurable, multi-tiered approach** that will evolve from rules-based to ML-powered.

## Current Architecture (Phase 1: Rules-Based)

```
┌────────────────────────────────────────────────────────────┐
│                    Transaction Input                        │
└─────────────────────────┬──────────────────────────────────┘
                          │
        ┌─────────────────▼──────────────────┐
        │   Tier 1: Teller API Category      │
        │   (90% confidence)                 │
        │   • teller_category = "transfer"   │
        └─────────────────┬──────────────────┘
                          │
        ┌─────────────────▼──────────────────┐
        │   Tier 2: Account Matching         │
        │   (95% confidence)                 │
        │   • Find opposite transaction      │
        │   • Same amount, different account │
        └─────────────────┬──────────────────┘
                          │
        ┌─────────────────▼──────────────────┐
        │   Tier 3: Payment Detection        │
        │   (85% confidence)                 │
        │   • Credit card payments           │
        │   • Loan/mortgage payments         │
        │   • Uses configurable keywords     │
        └─────────────────┬──────────────────┘
                          │
        ┌─────────────────▼──────────────────┐
        │   Tier 4: User Custom Rules        │
        │   (User-defined)                   │
        │   • Database rules                 │
        │   • Highest priority               │
        └─────────────────┬──────────────────┘
                          │
        ┌─────────────────▼──────────────────┐
        │   Tier 5: Keyword Patterns         │
        │   (70% confidence)                 │
        │   • "TRANSFER TO", "WITHDRAWAL TO" │
        │   • Uses configurable keywords     │
        └─────────────────┬──────────────────┘
                          │
                 ┌────────▼─────────┐
                 │  Final Decision  │
                 └──────────────────┘
```

---

## Configuration

### 1. Default Rules (JSON Config)

Edit `/backend/app/config/transfer_rules.json`:

```json
{
  "internal_transfer_keywords": [
    "WITHDRAWAL TO",
    "TRANSFER TO",
    "YOUR CUSTOM KEYWORD"
  ],
  "credit_card_companies": [
    "CHASE",
    "YOUR CREDIT UNION"
  ]
}
```

**When to use:** Adding keywords that apply to all users.

### 2. User-Specific Rules (Database)

Add custom rules via API or database:

```python
# Example: Add rule for user
rule = TransferRule(
    user_id="user123",
    rule_type="payment",  # or "internal_transfer", "exclude"
    pattern="MY ROOMMATE VENMO",
    is_regex=False,
    priority=10,
    description="Roommate's Venmo transfers should not count as spending"
)
```

**When to use:** User-specific edge cases that don't apply globally.

---

## Rule Types

| Type | Description | Example |
|------|-------------|---------|
| `internal_transfer` | Flag as transfer (exclude) | "WITHDRAWAL TO 360" |
| `payment` | Credit card/loan payment | "CHASE CC PAYMENT" |
| `exclude` | NOT a transfer (override) | "TRANSFER TAPE CO." (it's a store) |

---

## Future Architecture (Phase 2-3: ML-Powered)

### Phase 2: Ntropy API (Weeks 3-4)

```
┌───────────────────────────────────────┐
│      Transaction Input                │
└────────────────┬──────────────────────┘
                 │
      ┌──────────▼──────────┐
      │  Quick Rule Check   │  ← 80% of cases handled
      │  (Tiers 1-2)        │     instantly
      └──────────┬──────────┘
                 │
         ┌───────▼────────┐
         │   Ambiguous?   │
         └───┬────────┬───┘
             │        │
          NO │        │ YES
             │        │
   ┌─────────▼──┐  ┌─▼──────────────┐
   │  Done ✓    │  │  Ntropy API    │  ← $0.03/transaction
   └────────────┘  │  ML enrichment │     (20% of cases)
                   └────────────────┘
```

**Benefits:**
- Professional ML categorization
- Merchant name cleanup
- Works immediately (no training needed)

**Cost:** ~$30/month for 100k transactions (only unclear cases)

### Phase 3: Custom BERT Model (Month 2-3)

```
┌──────────────────────────────────────────┐
│         Transaction Input                 │
└─────────────────┬────────────────────────┘
                  │
       ┌──────────▼─────────────┐
       │  Deterministic Rules   │  ← 60% handled
       │  (Always use these)    │     (instant)
       └──────────┬─────────────┘
                  │
         ┌────────▼────────┐
         │   Ambiguous?    │
         └────┬────────┬───┘
              │        │
      ┌───────▼──┐  ┌─▼───────────────┐
      │ Done ✓   │  │  Local BERT     │  ← 35% (free)
      └──────────┘  │  Fine-tuned on  │     Runs locally
                    │  your data      │
                    └────┬────────────┘
                         │
                    ┌────▼────────────┐
                    │ Still unclear?  │
                    └────┬────────────┘
                         │
                    ┌────▼──────────┐
                    │  Ntropy API   │  ← 5% (minimal cost)
                    │  Last resort  │
                    └───────────────┘
```

**Benefits:**
- Learns from YOUR transactions
- Learns from user corrections
- Free to run (after training)
- Falls back to Ntropy for edge cases

**Cost:** ~$3-5/month (only very ambiguous cases)

---

## What STAYS Even with ML

Even after full ML implementation, these rules remain necessary:

### 1. Account Matching (Cannot ML This)
```python
# Checking: -$500 (withdrawal)
# Savings:  +$500 (deposit)
# → MUST use rule-based matching to see both sides
```

### 2. User Preferences
```python
# User: "My roommate's Venmo = transfer"
# User: "Other Venmo = expense"
# → ML can't know this without user teaching it
```

### 3. Institution Quirks
```python
# User: "My credit union labels everything as ACH"
# → Need custom rule to handle this
```

### 4. Overrides & Corrections
```python
# ML says: "This is shopping"
# User says: "No, this is a transfer to my friend"
# → Custom rule overrides ML
```

---

## Adding Custom Keywords (Quick Guide)

### For All Users (JSON)
```bash
# Edit the config file
vim backend/app/config/transfer_rules.json

# Add your keyword
"internal_transfer_keywords": [
  "WITHDRAWAL TO",
  "YOUR NEW KEYWORD"  # ← Add here
]

# Restart server
```

### For One User (Database)
```sql
-- Add custom rule
INSERT INTO transfer_rules (
  user_id, rule_type, pattern, description
) VALUES (
  'user123',
  'internal_transfer',
  'MY WEIRD BANK DESCRIPTION',
  'My bank uses weird wording for transfers'
);
```

---

## Testing Your Rules

```bash
# Run tests
python backend/test_transfer_detection.py

# Add your own test case to verify behavior
```

---

## Migration Path

| Phase | Timeline | Detection Method | Cost/100k txns |
|-------|----------|------------------|----------------|
| **Phase 1** (Current) | Now | Rules + Account Matching | $0 |
| **Phase 2** | Week 3-4 | Rules + Ntropy (ambiguous only) | ~$30 |
| **Phase 3** | Month 2-3 | Rules + BERT + Ntropy (fallback) | ~$3-5 |

**Key Point:** Rules are NOT temporary - they're the foundation that makes ML work efficiently and affordably!

---

## FAQ

### Q: Why not just use ML for everything?
**A:**
1. **Cost** - ML APIs charge per transaction ($3,000/mo for 100k txns)
2. **Deterministic cases** - Account matching can't be ML'd
3. **Cold start** - New users have no training data
4. **User control** - Users need to override ML decisions

### Q: When do I need to add custom rules?
**A:** When you see:
- Transfers not being filtered
- Real expenses being filtered incorrectly
- Bank-specific wording not recognized

### Q: Will my custom rules be lost with ML?
**A:** No! Custom rules have **highest priority** and override ML.

### Q: Can I use regex patterns?
**A:** Yes! Set `is_regex=True` in the database rule.

```python
TransferRule(
    pattern=r"XFER.*TO.*\d{4}",  # Regex pattern
    is_regex=True
)
```

---

## Summary

**Current System:** Configurable rules that work today
**Future System:** Rules + ML hybrid (best of both worlds)
**Cost Evolution:** $0 → $30/mo → $3-5/mo
**Accuracy Evolution:** 85% → 95% → 98%+

**The rules you configure now will continue working with ML - they're not wasted effort!**
