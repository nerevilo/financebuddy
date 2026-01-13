# Implementation Plan: LLM with Search Tools for Transaction Enrichment

**Date:** January 8, 2026
**Status:** Planning Phase
**Goal:** Build intelligent transaction enrichment using LLM + web search, reducing costs by 85-90%

---

## 📋 Executive Summary

### Current State
- ✅ Ntropy API integrated and working
- ✅ Transfer detection implemented (production-ready)
- ✅ Pattern matching built (33% coverage out of the box)
- 💰 Cost: $15.82 per 791 transactions

### Target State
- 🎯 Pattern matching: 70% coverage (FREE)
- 🎯 LLM with search tools: 25% ($0.005 each)
- 🎯 Ntropy fallback: 5% ($0.020 each)
- 💰 Target cost: ~$1.80 per 791 transactions (88% savings)

### Key Innovation
**Give LLM the ability to search the web when uncertain about business locations**
- LLM analyzes transaction
- If unsure → searches web for store location
- Extracts information from search results
- Returns accurate data with sources

---

## 🎯 Goals & Success Metrics

### Primary Goals
1. **Reduce enrichment costs by 85-90%**
2. **Maintain 90%+ accuracy** for merchant names and categories
3. **Achieve 80%+ accuracy** for store locations
4. **Stay under $2 per 791 transactions**

### Success Metrics
| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Cost per 791 txns | $15.82 | $1.80 | Track API costs |
| Merchant accuracy | 95% | 90%+ | Manual validation |
| Location accuracy | 90% | 80%+ | Manual validation |
| Pattern match rate | 33% | 70% | Count pattern hits |
| Search success rate | N/A | 85%+ | Track search results |
| Avg enrichment time | 200ms | <3s | Log timestamps |

### Non-Goals
- Not trying to match Ntropy's 95% accuracy (diminishing returns)
- Not building our own merchant database
- Not scraping store locators manually
- Not implementing store location caching (yet)

---

## 🏗️ Architecture Overview

### Three-Tier Cascade System

```
┌─────────────────────────────────────────────────────────┐
│                  New Transaction                         │
│   "Debit Card Purchase - HARDEE'S 594"                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   TIER 1: CACHE        │ ◄── Check if already enriched
        │   Cost: $0.000         │
        │   Time: <1ms           │
        └────────┬───────────────┘
                 │
          Already enriched? ──YES──► Return cached result
                 │
                NO
                 │
                 ▼
        ┌────────────────────────┐
        │ TIER 2: PATTERN MATCH  │ ◄── Lookup in dictionary
        │ Cost: $0.000           │      "HARDEE" → "Hardee's"
        │ Time: <1ms             │
        │ Coverage: 70%          │
        └────────┬───────────────┘
                 │
          Found + confident? ──YES──► Return result
                 │                     Save to database
                NO
                 │
                 ▼
        ┌────────────────────────┐
        │ TIER 3: LLM + SEARCH   │ ◄── GPT-4 with search tools
        │ Cost: $0.005           │     Can search web for info
        │ Time: 2-3s             │
        │ Coverage: 25%          │
        └────────┬───────────────┘
                 │
          Confident? ──YES──► Return result
                 │              Learn pattern
                 │              Save to database
                NO
                 │
                 ▼
        ┌────────────────────────┐
        │ TIER 4: NTROPY API     │ ◄── Fallback for hard cases
        │ Cost: $0.020           │
        │ Time: 200ms            │
        │ Coverage: 5%           │
        └────────┬───────────────┘
                 │
                 ▼
           Return result
           Learn pattern
           Save to database
```

### Flow Chart

```
Transaction
    ↓
Check cache → HIT → Return
    ↓ MISS
Pattern match → HIT (confidence ≥ 0.85) → Return + Save
    ↓ MISS
LLM analyzes → Needs more info? → YES → Search web → Extract info
    ↓ NO                              ↓
Direct answer ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
    ↓
Confidence ≥ 0.75? → YES → Return + Learn pattern + Save
    ↓ NO
Ntropy API → Return + Learn pattern + Save
```

---

## 📊 Cost Analysis

### Breakdown by Tier (791 transactions)

| Tier | Transactions | Coverage | Unit Cost | Total Cost | Cumulative |
|------|-------------|----------|-----------|------------|------------|
| Cache (free) | 791 (100%) | 100% | $0.000 | $0.00 | $0.00 |
| Pattern (free) | 553 (70%) | 70% | $0.000 | $0.00 | $0.00 |
| LLM + Search | 198 (25%) | 25% | $0.005 | $0.99 | $0.99 |
| Ntropy (fallback) | 40 (5%) | 5% | $0.020 | $0.80 | $1.79 |

**Total: $1.79** (vs $15.82 with Ntropy only = **88.7% savings**)

### Monthly Costs (Assuming 1,000 transactions/month)

| Scenario | Cost | Savings |
|----------|------|---------|
| Ntropy only | $20.00 | Baseline |
| Pattern + Ntropy | $6.00 | 70% |
| Pattern + LLM + Ntropy | $2.26 | 88.7% |
| Pattern + LLM only (no Ntropy) | $1.50 | 92.5% |

### Annual Savings

- Current (Ntropy): $240/year
- With cascade: $27/year
- **Savings: $213/year** (88.7%)

---

## 🛠️ Technical Implementation

### Phase 1: Foundation Setup (Week 1)

**Goal:** Set up infrastructure and APIs

#### Tasks:

**1.1 API Selection & Setup**
```bash
# Sign up for APIs
1. Tavily API (tavily.com) - 1,000 free searches/month
2. OpenAI API (platform.openai.com) - For GPT-4-turbo
3. Keep Ntropy as fallback
```

**1.2 Install Dependencies**
```bash
cd backend
pip install tavily-python openai anthropic
```

**1.3 Update Configuration**
```python
# app/core/config.py
class Settings(BaseSettings):
    # Existing...
    ntropy_api_key: str = ""

    # New additions
    openai_api_key: str = ""
    tavily_api_key: str = ""
    anthropic_api_key: str = ""

    # Feature flags
    use_pattern_matching: bool = True
    use_llm_search: bool = True
    use_ntropy_fallback: bool = True
```

**1.4 Update Environment Variables**
```bash
# backend/.env
OPENAI_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here (optional)
```

**Deliverables:**
- ✅ API accounts created
- ✅ Dependencies installed
- ✅ Configuration updated
- ✅ Environment variables set

**Time Estimate:** 2-3 hours

---

### Phase 2: Build LLM + Search Integration (Week 1-2)

**Goal:** Implement LLM with search tool capabilities

#### Tasks:

**2.1 Create Tavily Search Service**

**File:** `app/services/search_service.py`

```python
"""
Web search service using Tavily API
"""
from tavily import TavilyClient
from typing import List, Dict, Optional
from ..core.config import get_settings


class SearchService:
    """Web search for business information"""

    def __init__(self):
        settings = get_settings()
        self.client = TavilyClient(api_key=settings.tavily_api_key)
        self.enabled = bool(settings.tavily_api_key)

    async def search(self, query: str) -> List[Dict]:
        """
        Search the web for business information

        Args:
            query: Search query (e.g., "Hardees store 594 location")

        Returns:
            List of search results with titles, snippets, URLs
        """
        if not self.enabled:
            return []

        try:
            response = self.client.search(
                query=query,
                search_depth="basic",  # or "advanced" for more results
                max_results=3
            )

            return [
                {
                    "title": result.get("title", ""),
                    "snippet": result.get("content", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0.0)
                }
                for result in response.get("results", [])
            ]

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def is_enabled(self) -> bool:
        """Check if search is available"""
        return self.enabled
```

**2.2 Create LLM with Function Calling**

**File:** `app/services/llm_enrichment_advanced.py`

```python
"""
LLM enrichment with search tool capabilities
"""
import json
from openai import AsyncOpenAI
from typing import Optional, Dict
from ..models.models import Transaction
from ..core.config import get_settings
from .search_service import SearchService


class LLMEnrichmentAdvanced:
    """
    LLM that can search the web when needed

    Uses OpenAI's function calling to let GPT-4 decide
    when to search for information.
    """

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.search_service = SearchService()
        self.enabled = bool(settings.openai_api_key)

    async def enrich(self, transaction: Transaction) -> Optional[Dict]:
        """
        Enrich transaction using LLM with search capabilities

        Process:
        1. LLM analyzes transaction description
        2. If uncertain, LLM calls search_web function
        3. Search returns results
        4. LLM synthesizes final answer from search results

        Returns:
            Enrichment data with merchant, category, location
        """
        if not self.enabled:
            return None

        # Define tools available to the LLM
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for information about a business, store location, or address. Use this when you need to find specific store locations, verify business information, or look up addresses.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query. Examples: 'Hardees store 594 location', 'Dominos 4290 Blacksburg VA address', 'Publix 1189 Gulf Breeze FL'"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        # System prompt
        system_prompt = """You are a financial transaction analyzer. Extract business information from transaction descriptions.

You have access to a web search tool. Use it when:
- You see a store number and need to find the location
- You're unsure about a business name or details
- You need to verify or look up an address

Your goal: Extract accurate merchant name, category, and location information.

Respond in JSON format:
{
    "merchant": "Official Business Name",
    "category": "business category",
    "address": "full address or null",
    "city": "city or null",
    "state": "state or null",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}"""

        # User prompt
        user_prompt = f"""Analyze this transaction:

Description: "{transaction.description}"
Amount: ${abs(transaction.amount)}

If you see a store number or location indicator, search for the specific location.

Extract merchant, category, and location information."""

        # Initial LLM call
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1
            )

            message = response.choices[0].message

            # Check if LLM wants to use tools
            if message.tool_calls:
                # LLM decided to search!
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "search_web":
                        # Extract search query
                        args = json.loads(tool_call.function.arguments)
                        query = args["query"]

                        print(f"🔍 LLM searching: {query}")

                        # Execute search
                        results = await self.search_service.search(query)

                        # Format for LLM
                        search_summary = self._format_search_results(results)

                        # Add tool response to conversation
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call.dict()]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": search_summary
                        })

                # Get final answer with search results
                final_response = await self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    temperature=0.1
                )

                content = final_response.choices[0].message.content
                result = json.loads(content)
                result["searched"] = True
                result["search_query"] = query
                result["source"] = "llm_with_search"
                result["cost"] = 0.005  # Approximate

                return result

            else:
                # LLM answered directly without searching
                content = message.content
                result = json.loads(content)
                result["searched"] = False
                result["source"] = "llm_direct"
                result["cost"] = 0.002  # Approximate

                return result

        except Exception as e:
            print(f"LLM enrichment error: {e}")
            return None

    def _format_search_results(self, results: List[Dict]) -> str:
        """Format search results for LLM consumption"""
        if not results:
            return "No search results found."

        formatted = "Search results:\n\n"
        for i, result in enumerate(results[:3], 1):
            formatted += f"Result {i}:\n"
            formatted += f"Title: {result['title']}\n"
            formatted += f"Content: {result['snippet']}\n"
            formatted += f"URL: {result['url']}\n\n"

        return formatted
```

**2.3 Create Unified Enrichment Service**

**File:** `app/services/unified_enrichment.py`

```python
"""
Unified enrichment service with cascade logic
"""
from typing import Optional, Dict
from datetime import datetime
from ..models.models import Transaction
from ..core.config import get_settings
from .merchant_patterns import MerchantPatternMatcher
from .llm_enrichment_advanced import LLMEnrichmentAdvanced
from .ntropy_client import NtropyClient


class UnifiedEnrichmentService:
    """
    Three-tier cascade enrichment:
    1. Pattern matching (free)
    2. LLM with search (cheap)
    3. Ntropy (fallback)
    """

    def __init__(self):
        settings = get_settings()

        self.pattern_matcher = MerchantPatternMatcher()
        self.llm_enricher = LLMEnrichmentAdvanced()
        self.ntropy_client = NtropyClient()

        # Feature flags
        self.use_patterns = settings.use_pattern_matching
        self.use_llm = settings.use_llm_search
        self.use_ntropy = settings.use_ntropy_fallback

        # Stats tracking
        self.stats = {
            "cache_hits": 0,
            "pattern_matches": 0,
            "llm_enrichments": 0,
            "llm_searches": 0,
            "ntropy_calls": 0,
            "failures": 0
        }

    async def enrich(self, transaction: Transaction) -> Optional[Dict]:
        """
        Enrich transaction using cascade approach

        Returns enrichment data and updates transaction in database
        """

        # Tier 0: Check cache (already enriched?)
        if transaction.enriched_merchant:
            self.stats["cache_hits"] += 1
            return {
                "merchant": transaction.enriched_merchant,
                "category": transaction.enriched_category,
                "source": "cache"
            }

        # Tier 1: Pattern matching
        if self.use_patterns:
            result = self.pattern_matcher.recognize_merchant(
                transaction.description
            )

            if result and result.get("confidence", 0) >= 0.85:
                self.stats["pattern_matches"] += 1

                # Save to database
                transaction.enriched_merchant = result["merchant"]
                transaction.enriched_category = result["category"]
                transaction.categorization_source = "pattern_match"
                transaction.categorization_confidence = result["confidence"]
                transaction.enriched_at = datetime.utcnow()

                return result

        # Tier 2: LLM with search
        if self.use_llm:
            result = await self.llm_enricher.enrich(transaction)

            if result and result.get("confidence", 0) >= 0.75:
                self.stats["llm_enrichments"] += 1
                if result.get("searched"):
                    self.stats["llm_searches"] += 1

                # Save to database
                transaction.enriched_merchant = result.get("merchant")
                transaction.enriched_category = result.get("category")
                transaction.categorization_source = result.get("source")
                transaction.categorization_confidence = result.get("confidence")
                transaction.enriched_at = datetime.utcnow()

                # Learn pattern for future
                await self._learn_pattern(transaction, result)

                return result

        # Tier 3: Ntropy fallback
        if self.use_ntropy:
            result = await self.ntropy_client.enrich_transaction(transaction)

            if result:
                self.stats["ntropy_calls"] += 1

                # Save to database
                transaction.enriched_merchant = result.get("merchant")
                transaction.enriched_category = result.get("category")
                transaction.categorization_source = "ntropy"
                transaction.categorization_confidence = result.get("confidence")
                transaction.enriched_at = datetime.utcnow()

                # Learn pattern for future
                await self._learn_pattern(transaction, result)

                return result

        # All tiers failed
        self.stats["failures"] += 1
        return None

    async def _learn_pattern(self, transaction: Transaction, result: Dict):
        """
        Learn new patterns from successful enrichments

        Extract pattern from transaction description and add to database
        for future pattern matching.
        """
        # TODO: Implement pattern learning
        # This would extract key terms from description and map to merchant
        pass

    def get_stats(self) -> Dict:
        """Get enrichment statistics"""
        total = sum(self.stats.values())
        if total == 0:
            return self.stats

        return {
            **self.stats,
            "total": total,
            "cache_hit_rate": f"{(self.stats['cache_hits'] / total) * 100:.1f}%",
            "pattern_rate": f"{(self.stats['pattern_matches'] / total) * 100:.1f}%",
            "llm_rate": f"{(self.stats['llm_enrichments'] / total) * 100:.1f}%",
            "ntropy_rate": f"{(self.stats['ntropy_calls'] / total) * 100:.1f}%"
        }
```

**Deliverables:**
- ✅ Search service implemented
- ✅ LLM with function calling working
- ✅ Cascade logic implemented
- ✅ Stats tracking added

**Time Estimate:** 6-8 hours

---

### Phase 3: Update API Endpoints (Week 2)

**Goal:** Integrate new enrichment service into existing endpoints

#### Tasks:

**3.1 Update Categorization Router**

**File:** `app/routers/categorization.py`

```python
# Add to existing router

from ..services.unified_enrichment import UnifiedEnrichmentService

# Initialize service
unified_enricher = UnifiedEnrichmentService()

@router.post("/enrich/smart")
async def smart_enrich_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Enrich transaction using smart cascade approach
    (pattern → LLM+search → Ntropy)
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    result = await unified_enricher.enrich(transaction)

    if result:
        db.commit()
        return {
            "success": True,
            "result": result,
            "source": result.get("source"),
            "searched": result.get("searched", False)
        }
    else:
        return {
            "success": False,
            "message": "Enrichment failed"
        }

@router.get("/stats/enrichment")
def get_enrichment_stats():
    """Get cascade enrichment statistics"""
    return unified_enricher.get_stats()
```

**3.2 Update Batch Enrichment**

```python
@router.post("/enrich/all/smart")
async def smart_enrich_all(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Enrich all transactions using smart cascade
    Runs in background
    """
    background_tasks.add_task(smart_enrich_task, db)

    return {
        "message": "Smart enrichment started in background",
        "approach": "pattern → LLM+search → Ntropy"
    }

async def smart_enrich_task(db: Session):
    """Background task for smart enrichment"""
    enricher = UnifiedEnrichmentService()

    # Get unenriched transactions
    transactions = db.query(Transaction).filter(
        Transaction.enriched_merchant == None
    ).all()

    print(f"Enriching {len(transactions)} transactions...")

    for i, tx in enumerate(transactions):
        await enricher.enrich(tx)

        if (i + 1) % 50 == 0:
            db.commit()
            print(f"Progress: {i + 1}/{len(transactions)}")

    db.commit()

    # Print final stats
    stats = enricher.get_stats()
    print(f"\nEnrichment complete!")
    print(f"Stats: {stats}")
```

**Deliverables:**
- ✅ New smart enrichment endpoint
- ✅ Batch enrichment updated
- ✅ Stats endpoint added

**Time Estimate:** 2-3 hours

---

### Phase 4: Testing & Validation (Week 2)

**Goal:** Test the cascade system and validate accuracy

#### Test Cases:

**4.1 Unit Tests**

**File:** `tests/test_smart_enrichment.py`

```python
import pytest
from app.services.unified_enrichment import UnifiedEnrichmentService
from app.models.models import Transaction


@pytest.mark.asyncio
async def test_pattern_matching():
    """Test that pattern matching catches common merchants"""
    enricher = UnifiedEnrichmentService()

    tx = Transaction(
        description="Debit Card Purchase - HARDEE'S 594",
        amount=-7.39
    )

    result = await enricher.enrich(tx)

    assert result is not None
    assert result["merchant"] == "Hardee's"
    assert result["category"] == "fast food"
    assert result["source"] == "pattern_match"


@pytest.mark.asyncio
async def test_llm_with_search():
    """Test LLM enrichment with search for unknown merchant"""
    enricher = UnifiedEnrichmentService()

    # Unknown merchant that should trigger search
    tx = Transaction(
        description="Debit Card Purchase - LOCAL COFFEE SHOP 123",
        amount=-4.50
    )

    result = await enricher.enrich(tx)

    # Should use LLM (maybe with search)
    assert result["source"] in ["llm_direct", "llm_with_search"]


@pytest.mark.asyncio
async def test_cascade_order():
    """Test that cascade tries methods in correct order"""
    enricher = UnifiedEnrichmentService()

    # Should hit pattern matching first
    tx1 = Transaction(description="STARBUCKS 12345", amount=-5.00)
    result1 = await enricher.enrich(tx1)
    assert result1["source"] == "pattern_match"

    # Should skip pattern, use LLM
    tx2 = Transaction(description="UNKNOWN MERCHANT XYZ", amount=-10.00)
    result2 = await enricher.enrich(tx2)
    assert result2["source"] in ["llm_direct", "llm_with_search", "ntropy"]
```

**4.2 Integration Tests**

```python
@pytest.mark.asyncio
async def test_full_enrichment_flow(db_session):
    """Test complete enrichment flow with database"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    enricher = UnifiedEnrichmentService()

    # Get a real transaction
    tx = db.query(Transaction).first()

    result = await enricher.enrich(tx)

    assert result is not None
    assert tx.enriched_merchant is not None
    assert tx.categorization_source is not None

    db.commit()
```

**4.3 Manual Validation**

Create validation script:

```bash
# Test on sample transactions
python test_smart_enrichment_manual.py

# Should show:
# - Which tier handled each transaction
# - Search queries made (if any)
# - Accuracy of results
# - Cost breakdown
```

**Deliverables:**
- ✅ Unit tests passing
- ✅ Integration tests passing
- ✅ Manual validation complete
- ✅ Accuracy measured

**Time Estimate:** 4-6 hours

---

### Phase 5: Monitoring & Optimization (Week 3)

**Goal:** Add monitoring and optimize performance

#### Tasks:

**5.1 Cost Tracking**

**File:** `app/services/cost_tracker.py`

```python
"""
Track enrichment costs across all methods
"""
from datetime import datetime
from sqlalchemy import func
from ..models.models import Transaction
from ..core.database import SessionLocal


class CostTracker:
    """Track and analyze enrichment costs"""

    COST_PER_METHOD = {
        "pattern_match": 0.000,
        "llm_direct": 0.002,
        "llm_with_search": 0.005,
        "ntropy": 0.020
    }

    @staticmethod
    def calculate_costs(start_date=None, end_date=None):
        """Calculate costs for a date range"""
        db = SessionLocal()

        query = db.query(
            Transaction.categorization_source,
            func.count(Transaction.id)
        ).filter(
            Transaction.categorization_source != None
        )

        if start_date:
            query = query.filter(Transaction.enriched_at >= start_date)
        if end_date:
            query = query.filter(Transaction.enriched_at <= end_date)

        counts = query.group_by(Transaction.categorization_source).all()

        total_cost = 0.0
        breakdown = {}

        for source, count in counts:
            cost = count * CostTracker.COST_PER_METHOD.get(source, 0)
            total_cost += cost
            breakdown[source] = {
                "count": count,
                "unit_cost": CostTracker.COST_PER_METHOD.get(source, 0),
                "total_cost": cost
            }

        return {
            "total_cost": round(total_cost, 2),
            "breakdown": breakdown,
            "total_transactions": sum(c for _, c in counts)
        }
```

**5.2 Performance Monitoring**

Add logging to track:
- Time spent in each tier
- Search query effectiveness
- Pattern match hit rate
- LLM confidence scores

**5.3 Pattern Learning**

Implement automatic pattern learning:

```python
async def learn_from_enrichment(transaction, result):
    """
    Extract pattern from successful enrichment
    Add to pattern database for future use
    """
    # Extract key from description
    desc_upper = transaction.description.upper()

    # Remove common prefixes
    for prefix in PREFIXES:
        desc_upper = desc_upper.replace(prefix, "")

    # Extract merchant keyword
    words = desc_upper.split()
    for word in words:
        if len(word) >= 4:  # Minimum length
            # Check if this word appears in result merchant
            if word in result["merchant"].upper():
                # Add to pattern database
                add_pattern(word, result["merchant"])
                break
```

**Deliverables:**
- ✅ Cost tracking implemented
- ✅ Performance monitoring added
- ✅ Pattern learning working
- ✅ Dashboard with stats

**Time Estimate:** 4-6 hours

---

## 📈 Rollout Plan

### Week 1: Development
- Day 1-2: API setup and configuration
- Day 3-4: Build search service and LLM integration
- Day 5: Build unified enrichment service

### Week 2: Integration & Testing
- Day 1-2: Update API endpoints
- Day 3: Write tests
- Day 4: Manual validation
- Day 5: Fix bugs and optimize

### Week 3: Deployment & Monitoring
- Day 1: Deploy to production
- Day 2-3: Monitor performance and costs
- Day 4: Optimize pattern database
- Day 5: Analyze results and plan improvements

### Week 4: Optimization
- Expand pattern database from results
- Fine-tune confidence thresholds
- Optimize search queries
- Reduce unnecessary API calls

---

## 🎯 Success Criteria

### Must Have
- ✅ Cost per 791 transactions < $2.00
- ✅ Merchant name accuracy > 90%
- ✅ Pattern match rate > 60%
- ✅ All tests passing
- ✅ No breaking changes to existing API

### Should Have
- ✅ Location accuracy > 80%
- ✅ Average enrichment time < 3s
- ✅ Pattern match rate > 70%
- ✅ Search success rate > 85%

### Nice to Have
- ⭐ Automatic pattern learning
- ⭐ Cost tracking dashboard
- ⭐ Search query optimization
- ⭐ Confidence calibration

---

## 🚧 Risks & Mitigations

### Risk 1: Search API Rate Limits
**Impact:** High
**Probability:** Medium
**Mitigation:**
- Use Tavily (1,000/month free tier)
- Implement caching of search results
- Fall back to Ntropy if search fails
- Monitor usage carefully

### Risk 2: LLM Accuracy Below Target
**Impact:** Medium
**Probability:** Low
**Mitigation:**
- Use GPT-4-turbo (most accurate)
- Validate with test set before rollout
- Keep Ntropy as fallback
- Lower confidence thresholds if needed

### Risk 3: Costs Higher Than Expected
**Impact:** Medium
**Probability:** Low
**Mitigation:**
- Track costs in real-time
- Adjust tier thresholds dynamically
- Increase pattern matching coverage
- Disable search if budget exceeded

### Risk 4: Search Results Not Helpful
**Impact:** Medium
**Probability:** Medium
**Mitigation:**
- Improve search query formulation
- Try multiple search queries
- Fall back to Ntropy
- Learn from failures

### Risk 5: Performance Too Slow
**Impact:** Low
**Probability:** Low
**Mitigation:**
- Run enrichment in background
- Cache aggressively
- Batch process transactions
- Optimize search timeout

---

## 📊 Monitoring & Metrics

### Real-Time Metrics

**Dashboard should show:**
- Enrichments per tier (pie chart)
- Cost per transaction (line graph)
- Pattern match hit rate (%)
- Search success rate (%)
- Average enrichment time (ms)
- Daily/weekly/monthly costs

**Alerts:**
- Cost exceeds budget
- Error rate > 5%
- Search rate limit approaching
- Accuracy drops below 90%

### Weekly Review

Every Monday, analyze:
1. Total costs vs budget
2. Accuracy on sample set
3. New patterns learned
4. Search query effectiveness
5. Optimization opportunities

---

## 🎓 Learning & Improvement

### Pattern Database Growth

**Goal:** Grow from 40 → 200+ patterns in 1 month

**Strategy:**
1. Let Ntropy/LLM enrich for first week
2. Extract patterns from all successful enrichments
3. Add to pattern database
4. Week 2 onwards: 70%+ pattern match rate

### Search Query Optimization

**Track:**
- Which queries find good results
- Which queries fail
- Common query patterns

**Optimize:**
- Refine query formulation
- Add location hints when available
- Try alternative phrasings

### Confidence Calibration

**Monitor:**
- False positives (confident but wrong)
- False negatives (not confident but could work)

**Adjust:**
- Confidence thresholds per tier
- Pattern matching confidence
- LLM confidence interpretation

---

## 💰 Budget & ROI

### One-Time Costs
- Development time: 40 hours × $0/hour = $0 (your time)
- Testing: 8 hours × $0/hour = $0
- API setup: Free (free tiers)

**Total one-time: $0**

### Monthly Operating Costs

**Current (Ntropy only):**
- 1,000 transactions/month × $0.02 = $20/month

**After Implementation:**
- Pattern matching: 700 × $0.00 = $0.00
- LLM + Search: 250 × $0.005 = $1.25
- Ntropy: 50 × $0.02 = $1.00
**Total: $2.25/month**

**Savings: $17.75/month** (88% reduction)

### Annual ROI
- Savings: $213/year
- Development cost: $0
- **ROI: Infinite** (all savings, no cost)

### Break-Even
Immediate (no upfront costs)

---

## 📝 Documentation

### User Documentation
- How to use smart enrichment
- How to view enrichment sources
- How to read cost reports
- Troubleshooting guide

### Developer Documentation
- Architecture overview
- Adding new search providers
- Customizing confidence thresholds
- Extending pattern database

### API Documentation
- New endpoints
- Request/response formats
- Error codes
- Rate limits

---

## 🚀 Next Steps

### Immediate (This Week)
1. ✅ Review this plan
2. ⬜ Get API keys (Tavily, OpenAI)
3. ⬜ Start Phase 1 implementation
4. ⬜ Test search service

### Short Term (Next 2 Weeks)
1. ⬜ Complete implementation
2. ⬜ Run tests and validation
3. ⬜ Deploy to production
4. ⬜ Monitor first results

### Medium Term (Next Month)
1. ⬜ Optimize pattern database
2. ⬜ Fine-tune cascade thresholds
3. ⬜ Implement pattern learning
4. ⬜ Achieve 90%+ savings target

### Long Term (3-6 Months)
1. ⬜ Consider training custom model
2. ⬜ Evaluate dropping Ntropy entirely
3. ⬜ Add more search providers
4. ⬜ Build merchant database

---

## ✅ Definition of Done

- ✅ All code implemented and tested
- ✅ Tests passing (unit + integration)
- ✅ Cost < $2 per 791 transactions
- ✅ Accuracy > 90% on validation set
- ✅ Documentation complete
- ✅ Monitoring dashboard live
- ✅ Pattern database growing automatically
- ✅ No breaking changes to existing API
- ✅ Fallbacks working correctly

---

## 🎊 Conclusion

This plan implements your brilliant idea: **Give LLM search tools to find information when uncertain**.

**Key Benefits:**
1. 85-90% cost reduction
2. Transparent (see what was searched)
3. Up-to-date information (real-time search)
4. Flexible (LLM decides when to search)
5. Still accurate (90%+ for most categories)

**What Makes This Work:**
- Pattern matching handles common cases (FREE)
- LLM + search handles complex cases (cheap)
- Ntropy fallback ensures reliability
- Automatic learning improves over time

**Ready to build?** Let's start with Phase 1! 🚀

---

**Last Updated:** January 8, 2026
**Status:** Ready for Implementation
**Estimated Completion:** 3 weeks
**Expected Savings:** $213/year (88.7%)
