# Changelog

All notable changes to Finance Buddy are documented here.

Format: `[YYYY-MM-DD] - Summary`

---

## [2026-01-13] - Backend Production Optimizations

### Database Performance
- Added 11 database indexes for query optimization:
  - Foreign key indexes: `institutions.user_id`, `accounts.institution_id`, `transactions.account_id`, `transactions.category_id`, `income_sources.user_id`, `goals.user_id`, `insights.user_id`
  - Query indexes: `transactions.date`, `transactions.is_anomaly`, `transactions.categorization_source`
  - Composite index: `transactions(account_id, date)` for common query patterns
- Fixed N+1 query patterns in accounts and institutions routers using `joinedload()` and `selectinload()`
- Configured PostgreSQL connection pooling: `pool_size=20`, `max_overflow=40`, `pool_recycle=3600`, `pool_pre_ping=True`
- Added query timeout (30s) and connection timeout (10s)

### Security Hardening
- Added rate limiting to auth endpoints: register (5/min), login (10/min), refresh (20/min)
- Secret key validation - app fails fast if default key used in production
- Debug mode defaults to `false`
- Restricted CORS: specific methods and headers instead of wildcards
- Explicit bcrypt rounds (12) for password hashing
- Added `TellerEnvironment` enum validation

### Caching (Redis)
- New `cache.py` module with `CacheService` class
- Dashboard endpoints cached with 5-10 minute TTL
- Automatic cache invalidation on transaction updates
- Optional - app works without Redis configured

### Logging & Observability
- New structured logging system (`logging_config.py`)
- JSON format for production, readable format for development
- Replaced 40+ print statements across 12 files with proper logging
- Log levels configurable via DEBUG setting

### Async Improvements
- Converted Teller service from sync to async HTTP client
- No longer blocks event loop during external API calls

### New Dependencies
- `slowapi>=0.1.9` - Rate limiting
- `redis>=5.0.0` - Caching (optional)

### Files Changed
```
backend/
  app/core/
    cache.py              - NEW: Redis caching service
    config.py             - Security validation, TellerEnvironment enum
    database.py           - Connection pooling configuration
    logging_config.py     - NEW: Structured logging setup
    rate_limiter.py       - NEW: Auth rate limiting
    security.py           - Explicit bcrypt rounds
  app/models/models.py    - Database indexes
  app/routers/
    accounts.py           - Eager loading (joinedload)
    auth.py               - Rate limiting decorators
    dashboard.py          - Redis caching
    institutions.py       - Eager loading (selectinload)
    transactions.py       - Cache invalidation
    teller_connect.py     - Async Teller calls, logging
    categorization.py     - Logging
  app/services/
    teller.py             - Async HTTP client
    dashboard_service.py  - Logging
    cascade_enrichment.py - Logging
    ntropy_client.py      - Logging
  alembic/versions/
    d4e5f6g7h8i9_add_database_indexes.py - NEW
  requirements.txt        - slowapi, redis
```

---

## [2026-01-10] - Transaction Management & Dashboard Fixes

### Dashboard Credit Card Fix
- Fixed dashboard queries to include credit card transactions (Citi card was being excluded)
- Credit cards store purchases as positive amounts; debit accounts as negative
- Updated `dashboard_service.py` to join with Account table and use `_is_expense()` helper
- Groceries now correctly shows $425.40 (was $68.94)

### Transaction Category Editing
**Backend:**
- Added `GET /transactions/categories` - lists all categories with usage counts
- Added `PATCH /transactions/{id}/category` - updates transaction category, sets `categorization_source = "user"`
- Added `GET /transactions/list` - paginated list with sorting (date/amount/merchant/category) and filtering
- New schemas: `TransactionCategoryUpdate`, `TransactionListResponse`, `CategoryResponse`

**Frontend:**
- New `TransactionDetailModal` component - click transaction to edit category
- Integrated modal into `DailyTransactionsTimeline` - transactions now clickable
- New `/transactions` page with `TransactionsTable` component
- Table features: sortable columns, category filter, inline editing, pagination (50/page)
- Added navigation links in sidebar (Dashboard, All Transactions)

### Bug Fixes
- Fixed 6 rent transactions miscategorized as "donation" (LR2-ARCLUB = apartment rent)

### Files Changed
```
backend/
  app/schemas/schemas.py          - Added new schemas
  app/schemas/__init__.py         - Exported new schemas
  app/routers/transactions.py     - Added 3 new endpoints
  app/services/dashboard_service.py - Fixed credit card handling

frontend/
  src/lib/api.ts                  - Added category/transaction API functions
  src/lib/hooks.ts                - Added useCategories, useTransactionsList hooks
  src/components/transactions/
    TransactionDetailModal.tsx    - NEW: Edit modal
    TransactionsTable.tsx         - NEW: Spreadsheet view
  src/app/transactions/page.tsx   - NEW: Transactions page
  src/components/dashboard/
    DailyTransactionsTimeline.tsx - Added modal integration
    InstitutionSidebar.tsx        - Added navigation links
```
