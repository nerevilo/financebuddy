# Changelog

All notable changes to the Finance Buddy backend will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

#### Intelligent Transaction Categorization System
- **Standardized Category Taxonomy** (`app/services/categories.py`)
  - 30 defined categories with IDs, display names, emojis, descriptions, and keywords
  - Categories include: groceries, fast_food, gas_stations, software_subscriptions, streaming, etc.
  - `normalize_category_id()` function to map free-form categories to standard ones
  - Handles common mis-categorizations (e.g., "television" → "streaming")

- **Semantic Matching System** (`app/services/semantic_matcher.py`)
  - 500+ merchant patterns with priority-based ordering
  - High-priority patterns checked first (e.g., "COSTCO GAS" priority 150 > "COSTCO" priority 50)
  - Solves the Costco Gas → groceries mis-categorization problem
  - BERT-based semantic similarity fallback (when sentence-transformers installed)
  - Comprehensive coverage for:
    - Gas stations at retail locations (Costco Gas, Sam's Club Gas, Kroger Fuel, etc.)
    - Software subscriptions (Claude, OpenAI, GitHub, Cursor, Notion, etc.)
    - Streaming services (Netflix, Spotify, Disney+, etc.)
    - Gaming (Steam, PlayStation, Xbox, etc.)
    - And 20+ other categories

- **LLM Response Caching** (`app/core/cache.py`, `app/services/gemini_enrichment.py`)
  - 7-day cache TTL for enrichment results
  - Smart cache key normalization (removes store numbers, prefixes)
  - In-memory LRU cache fallback when Redis unavailable
  - Cache keys: `enrichment:gemini:{normalized_description}`

- **Test Scripts**
  - `test_categorization.py` - Validates semantic matching and category normalization
  - Updated `test_cascade.py` - Tests full enrichment cascade with new system

### Changed

- **Cascade Enrichment** (`app/services/cascade_enrichment.py`)
  - Now uses semantic matcher instead of simple pattern matching
  - High-confidence matches (≥0.85) returned immediately (FREE)
  - Medium-confidence matches passed as hints to LLM for verification
  - Tracks cache hits separately in stats
  - New method counts: `semantic_rule`, `semantic_similarity`, `llm_cached`

- **Gemini Enrichment** (`app/services/gemini_enrichment.py`)
  - Updated prompts with standardized category list
  - Added explicit examples for problematic cases:
    - "COSTCO GAS" → gas_stations (NOT groceries)
    - "CLAUDE.AI" → software_subscriptions (NOT television)
  - Added `hint` parameter for LLM to verify uncertain matches
  - All responses normalized to standard category IDs
  - Results cached for 7 days

- **Budget Enrichment** (`app/services/budget_enrichment.py`)
  - Updated cost estimates to include semantic matching methods

- **Cache Service** (`app/core/cache.py`)
  - Added `InMemoryCache` class with LRU eviction and TTL support
  - Cache service now falls back to in-memory when Redis unavailable
  - Added `EnrichmentCacheKeys` helper for consistent cache key generation
  - Added `CacheTTL.LLM_ENRICHMENT` (7 days)

### Fixed

- **Costco Gas categorized as Groceries** - Now correctly categorized as `gas_stations`
- **Claude/Anthropic subscriptions categorized as Television** - Now correctly categorized as `software_subscriptions`
- **Inconsistent category names** - All categories now normalized to snake_case IDs

### Dependencies

- Added `sentence-transformers>=2.2.0` (optional, for semantic similarity)
- Added `numpy>=1.24.0` (required for embeddings)

## Cost Optimization

The new system significantly reduces enrichment costs:

| Method | Cost | When Used |
|--------|------|-----------|
| Semantic Rule Match | FREE | High-confidence pattern matches |
| LLM Cache Hit | FREE | Previously seen descriptions |
| Gemini Flash | ~FREE | 1,500/day free tier |
| Gemini + Search | $0.005 | Complex cases |
| Ntropy | $0.02 | Fallback only |

Expected savings: **95-99%** compared to Ntropy-only approach.
