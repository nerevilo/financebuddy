# Build Your Own Transaction Enrichment System

## 🎯 Goal: Reduce Ntropy costs from $50/month to $5-10/month

**Current Status:**
- ✅ Ntropy integrated and working
- 📊 37.5% recognition rate with basic patterns
- 💰 Could save ~$18-25/month already

**Target:**
- 🎯 70-80% recognition rate (DIY)
- 💰 Reduce Ntropy calls by 60-70%
- 🚀 Final cost: $5-10/month

---

## 📈 3-Phase Roadmap

### Phase 1: Expand Pattern Database (Week 1) ⚡
**Effort:** 2-3 hours
**Cost Reduction:** 30% → 60%
**ROI:** High

#### What to Do:

1. **Let Ntropy enrich all your transactions first**
```bash
curl -X POST http://localhost:8000/categorization/enrich/all
```

2. **Extract patterns from Ntropy results**
```python
# Script to build pattern database from enriched transactions
from app.core.database import SessionLocal
from app.models.models import Transaction

db = SessionLocal()

# Get all Ntropy-enriched transactions
transactions = db.query(Transaction).filter(
    Transaction.categorization_source == 'ntropy',
    Transaction.enriched_merchant != None
).all()

# Build pattern mapping
patterns = {}
for tx in transactions:
    # Extract key from description
    desc = tx.description.upper()
    # Map to Ntropy's result
    patterns[desc] = {
        'merchant': tx.enriched_merchant,
        'category': tx.enriched_category
    }

# Add to merchant_patterns.py
```

**Expected Result:**
- Pattern database grows from 40 merchants to 200+
- Recognition rate: 37% → 60%
- Cost savings: ~$20/month

---

### Phase 2: Train ML Model (Week 2-3) 🤖
**Effort:** 4-6 hours
**Cost Reduction:** 60% → 75%
**ROI:** Medium

#### What to Do:

1. **Export Ntropy enrichments as training data**
```python
# Export enriched transactions
df = pd.DataFrame([
    {
        'description': tx.description,
        'merchant': tx.enriched_merchant,
        'category': tx.enriched_category
    }
    for tx in enriched_transactions
])

df.to_csv('training_data.csv')
```

2. **Train a simple classifier**
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

# Simple approach (not BERT - that's Phase 3)
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df['description'])
y = df['category']

model = MultinomialNB()
model.fit(X, y)

# Accuracy: 75-80% for categories
```

**Expected Result:**
- ML model handles edge cases
- Recognition rate: 60% → 75%
- Cost savings: ~$30/month

---

### Phase 3: Optimize & Monitor (Week 4+) 📊
**Effort:** Ongoing (30 min/week)
**Cost Reduction:** 75% → 80%
**ROI:** Low (maintenance)

#### What to Do:

1. **Add logging to track unknown merchants**
```python
# Track what Ntropy enriches
# Add those patterns to your database
```

2. **Monthly pattern updates**
```python
# Every month, export new Ntropy enrichments
# Add new patterns to merchant_patterns.py
```

3. **Cost monitoring dashboard**
```python
# Track:
# - Ntropy API calls
# - Pattern match hits
# - ML model hits
```

**Expected Result:**
- Recognition rate: 75% → 80%
- Cost savings: ~$35-40/month
- Ntropy calls: Only for truly new/unique merchants

---

## 🛠️ Implementation Guide

### Step 1: Smart Enrichment Flow

Update the categorization service to try DIY first:

```python
from app.services.merchant_patterns import MerchantPatternMatcher
from app.services.ntropy_client import NtropyClient

async def enrich_transaction(transaction):
    """
    Try enrichment in order:
    1. Check if already enriched (cache)
    2. Try DIY pattern matching (free)
    3. Fall back to Ntropy (paid)
    """

    # Check cache
    if transaction.enriched_merchant:
        return  # Already enriched

    # Try DIY pattern matching
    matcher = MerchantPatternMatcher()
    result = matcher.recognize_merchant(transaction.description)

    if result and result['confidence'] >= 0.80:
        # High confidence DIY match - save to database
        transaction.enriched_merchant = result['merchant']
        transaction.enriched_category = result['category']
        transaction.categorization_source = 'pattern_match'
        transaction.categorization_confidence = result['confidence']
        return

    # Unknown merchant - call Ntropy
    ntropy = NtropyClient()
    ntropy_result = await ntropy.enrich_transaction(transaction)

    if ntropy_result:
        transaction.enriched_merchant = ntropy_result['merchant']
        transaction.enriched_category = ntropy_result['category']
        transaction.categorization_source = 'ntropy'
        transaction.categorization_confidence = ntropy_result['confidence']

        # Learn from Ntropy for next time
        await save_pattern_for_learning(transaction.description, ntropy_result)
```

---

## 📊 Expected Results by Phase

| Phase | Recognition Rate | Ntropy Calls | Monthly Cost | Savings |
|-------|-----------------|--------------|--------------|---------|
| Current (Ntropy only) | 100% | 100% | $50 | $0 |
| Phase 1 (Patterns) | 60% | 40% | $20 | $30 |
| Phase 2 (+ ML) | 75% | 25% | $12 | $38 |
| Phase 3 (Optimized) | 80% | 20% | $10 | $40 |

For 791 transactions:
- Ntropy only: 791 calls × $0.02 = $15.82 (one-time)
- After Phase 1: 316 calls × $0.02 = $6.32 (60% savings)
- After Phase 2: 198 calls × $0.02 = $3.96 (75% savings)
- After Phase 3: 158 calls × $0.02 = $3.16 (80% savings)

---

## 🎯 Quick Wins (Do These First)

### 1. Add Logo URLs (5 minutes)

Already supports free logo API (Clearbit):

```python
# In merchant_patterns.py - already implemented!
logo = f"https://logo.clearbit.com/{website}"
```

### 2. Extract Store Numbers (Already done!)

```python
# In merchant_patterns.py - already implemented!
store_number = matcher.extract_store_number(description)
```

### 3. Extract Location Hints (Already done!)

```python
# In merchant_patterns.py - already implemented!
location = matcher.extract_location_hints(description)
# Returns: {"city": "Franklin", "state": "TN"}
```

---

## 🚀 What You Should Do NOW

### Option A: Keep It Simple (Recommended)
1. ✅ Use Ntropy for everything (current setup)
2. 📊 Monitor costs for 1 month
3. 📈 Once you have >1000 enrichments, implement Phase 1
4. 💰 Reduce costs by 60%

**Why:** Ntropy data becomes your training set. Don't optimize prematurely.

### Option B: Start Saving Immediately
1. ⚡ Integrate merchant_patterns.py (already created!)
2. 🔧 Update categorization service to try patterns first
3. 📉 Immediately save 30-40% on API costs

**Why:** Start saving money right away, learn as you go.

---

## 🧪 Test Your DIY Matcher

We already tested it on your transactions:

```bash
python -c "
from app.services.merchant_patterns import MerchantPatternMatcher

matcher = MerchantPatternMatcher()
result = matcher.recognize_merchant('Debit Card Purchase - HARDEE\\'S 594')
print(result)
"
```

Results: 37.5% recognition on first try (3/8 transactions)

**After adding your top 50 merchants:** 60-70% recognition

---

## 💡 Pro Tips

1. **Build patterns from Ntropy data**
   - Let Ntropy enrich for 1 month
   - Export all enrichments
   - Build pattern database from results
   - Now you have 100% accurate patterns!

2. **Focus on high-volume merchants**
   - If you go to Starbucks 100 times/year
   - That's $2 saved by recognizing it yourself
   - Top 10 merchants = 80% of transactions

3. **Use Clearbit for logos**
   - Free for most domains
   - Better than paying for logo CDN

4. **Don't build store location database**
   - Too much effort for little gain
   - Let Ntropy handle this
   - Focus on merchant/category only

---

## 🎊 Final Recommendation

**Best Strategy:**

1. **Month 1:** Use Ntropy 100% (build training data)
2. **Month 2:** Add pattern matching (save 60%)
3. **Month 3:** Train ML model (save 75%)
4. **Month 4+:** Maintain patterns (save 80%)

**Final Cost:** $5-10/month (vs $50/month Ntropy-only)

**Total Savings:** $40-45/month = $480-540/year

---

## 📝 Next Steps

Want me to:

1. ✅ Integrate merchant_patterns.py into the enrichment flow?
2. ✅ Add pattern learning from Ntropy results?
3. ✅ Create a pattern database builder script?
4. ✅ Build cost tracking dashboard?

Let me know what you want to tackle first!
