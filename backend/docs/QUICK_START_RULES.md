# Quick Start: Configuring Transfer Rules

## Need to Add a Custom Keyword? Here's How

### Option 1: Edit JSON Config (Applies to All Users)

**Use when:** You want to add a keyword that applies to everyone.

```bash
# 1. Open the config file
vim backend/app/config/transfer_rules.json

# 2. Add your keyword to the appropriate section
{
  "internal_transfer_keywords": [
    "WITHDRAWAL TO",
    "YOUR NEW KEYWORD HERE"  ← Add here
  ]
}

# 3. Restart the server
# Changes take effect immediately
```

**Examples:**
- Your bank uses "XFER" instead of "TRANSFER"
- Add "ACH TRANSFER OUT"
- Add your credit union's name to `credit_card_companies`

---

### Option 2: Add Database Rule (For Specific Users)

**Use when:** User has a unique situation.

```python
# Via Python
from app.models import TransferRule

rule = TransferRule(
    user_id="user-id-here",  # Or None for global
    rule_type="internal_transfer",  # or "payment", "exclude"
    pattern="MY CUSTOM PATTERN",
    is_regex=False,
    priority=10,
    description="Why this rule exists"
)
db.add(rule)
db.commit()
```

**Or via SQL:**
```sql
INSERT INTO transfer_rules (
    id, user_id, rule_type, pattern, description
) VALUES (
    gen_random_uuid(),
    'user-123',
    'internal_transfer',
    'MY WEIRD BANK TRANSFER',
    'My bank uses weird wording'
);
```

---

## Common Scenarios

### Scenario 1: Credit Card Not Recognized
```json
// Add to transfer_rules.json
"credit_card_companies": [
  "CHASE",
  "YOUR CREDIT UNION NAME"  ← Add this
]
```

### Scenario 2: Bank Uses Different Transfer Wording
```json
// Add to transfer_rules.json
"internal_transfer_keywords": [
  "WITHDRAWAL TO",
  "YOUR BANK'S WORDING"  ← Add this
]
```

### Scenario 3: User Has Roommate Venmo (Transfer)
```sql
-- Add user-specific rule
INSERT INTO transfer_rules (user_id, rule_type, pattern, description)
VALUES ('user-123', 'internal_transfer', 'JOHN DOE VENMO', 'Roommate rent split');
```

### Scenario 4: Store Name Contains "TRANSFER"
```sql
-- Exclude from transfer detection
INSERT INTO transfer_rules (user_id, rule_type, pattern, description)
VALUES ('user-123', 'exclude', 'TRANSFER TAPE CO', 'This is a store, not a transfer');
```

---

## Rule Types Explained

| Type | Effect | Use When |
|------|--------|----------|
| `internal_transfer` | Flags as transfer (filtered) | Moving money between own accounts |
| `payment` | Flags as payment (filtered) | Credit card/loan payments |
| `exclude` | NOT a transfer (kept) | Override false positive |

---

## Priority System

Higher priority = checked first

```
Priority 10: User's custom rules (highest)
Priority 5:  Common patterns
Priority 0:  Default rules (lowest)
```

**Example:**
```sql
-- High priority user override
INSERT INTO transfer_rules (pattern, priority, rule_type)
VALUES ('CHASE PAYMENT', 100, 'exclude');  -- Never filter this

-- Normal priority
INSERT INTO transfer_rules (pattern, priority, rule_type)
VALUES ('WELLS FARGO CC', 5, 'payment');   -- Standard priority
```

---

## Testing Your Changes

```bash
# After editing JSON config
python test_transfer_detection.py

# Check if your keyword works
python -c "
from app.services.categorization import TransferDetector
d = TransferDetector()
print('Keywords loaded:', d.internal_keywords)
"
```

---

## Migration to ML

**Important:** These rules are NOT temporary!

When ML is added (Phases 2-3):
1. ✅ Your rules continue working
2. ✅ Rules have HIGHER priority than ML
3. ✅ ML handles ambiguous cases
4. ✅ You can still add overrides

**The system becomes:**
```
Your Custom Rules → ML Decision → Default Rules
     (Override)      (Smart)         (Fallback)
```

---

## Need Help?

See full documentation: `docs/TRANSFER_DETECTION.md`
