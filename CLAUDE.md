# CLAUDE.md — Project Guidelines for FinanceBuddy

## Project Overview

FinanceBuddy is a personal finance app (Next.js + FastAPI + PostgreSQL) that connects to bank accounts via Teller, uses AI to categorize transactions, and provides a conversational chat API. It handles sensitive financial data — every code change must reflect that.

## Architecture

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (Supabase)
- **Frontend:** Next.js 14 (App Router), React 18, Tailwind CSS, Tremor, Radix UI, SWR
- **AI/ML:** Gemini Flash (primary enrichment), Claude (chat), FastEmbed (semantic matching), Tavily (search)
- **Banking:** Teller.io API with mTLS certificate auth
- **Caching:** Redis (optional), in-memory LRU fallback
- **Deploy:** Railway (backend), Vercel (frontend)

## Key Directories

- `backend/app/routers/` — API endpoints
- `backend/app/services/` — Business logic (enrichment, chat, dashboard)
- `backend/app/core/` — Config, database, auth, caching
- `backend/app/models/` — SQLAlchemy models
- `backend/alembic/versions/` — Database migrations
- `frontend/src/app/` — Next.js pages (App Router)
- `frontend/src/components/` — React components
- `frontend/src/lib/` — API client, auth, hooks, utilities

## Security Rules (Non-Negotiable)

### Secrets
- NEVER hardcode API keys, tokens, passwords, or connection strings in source code
- NEVER commit `.env` files — they are in `.gitignore` for a reason
- NEVER log secrets, tokens, or full database URLs — redact before logging
- NEVER expose internal config in API responses (no app IDs, env names, or API key names in error messages)
- Use environment variables for ALL secrets, loaded via `pydantic-settings`

### Authentication & Data Isolation
- EVERY database query that returns user data MUST filter by user_id — no exceptions
- NEVER trust user_id from request parameters alone for sensitive operations — verify against the authenticated user
- Background tasks and services MUST receive and enforce user_id scoping
- When creating `DashboardService` or similar scoped services, ALWAYS pass `user_id`
- API key scope enforcement: check `api_key.scopes` before allowing access to endpoints
- NEVER store auth tokens in localStorage — use httpOnly cookies

### Input Handling
- NEVER embed user-provided text directly into LLM prompts without sanitization
- Wrap untrusted content (transaction descriptions, user notes) in clear delimiters when used in prompts
- Validate ALL request inputs: string lengths, numeric bounds (`ge=`, `le=`), date formats
- Escape LIKE wildcards in search inputs (`%`, `_`)
- Validate regex patterns from users before compiling (wrap in try/except for `re.error`)

### CORS
- NEVER use `allow_origins=["*"]` with `allow_credentials=True`
- Keep CORS origin allowlists explicit — no broad regex patterns
- Anchor any regex patterns: `^https://exact-pattern\.example\.com$`

## Database Rules

### Queries
- ALWAYS use `joinedload()` or `selectinload()` when accessing relationships in loops — no N+1 queries
- NEVER use `.all()` on unbounded queries — always add `.limit()` or process in batches
- Use `SELECT ... FOR UPDATE SKIP LOCKED` when processing shared queues (enrichment batches)
- Batch database writes: use `db.add_all()` + single `db.commit()` instead of committing in loops
- NEVER use `Base.metadata.create_all()` — use Alembic migrations exclusively

### Migrations
- ALL schema changes go through Alembic — create a migration with `alembic revision --autogenerate -m "description"`
- Test both `upgrade()` and `downgrade()` paths
- Never modify a migration that has been applied to production

### Indexes
- Add indexes for columns that appear in `WHERE` clauses of frequent queries
- Use composite indexes for queries that filter on multiple columns together
- Verify with `EXPLAIN ANALYZE` before and after adding indexes

## API Design Rules

- Return proper HTTP status codes: 400 for bad input, 401 for auth failure, 403 for forbidden, 404 for not found, 409 for conflicts
- NEVER return 200 for error conditions — use appropriate error codes
- Use consistent error response format: `{"detail": "Human-readable message"}`
- NEVER expose internal details in error messages (no stack traces, config names, or file paths)
- Add rate limiting to expensive endpoints (enrichment triggers, LLM calls, background tasks)
- Validate pagination parameters: `limit` needs both `ge=1` and `le=<max>`, `offset` needs `ge=0`
- Add `max_length` to all string input fields (chat messages, notes, tag names, merchant names)

## External API Integration Rules

- ALWAYS set explicit timeouts on HTTP clients: `httpx.AsyncClient(timeout=30.0)`
- Add retry logic with exponential backoff for transient failures (429, 500, 502, 503, network errors)
- Reuse HTTP client instances — create once in `__init__`, don't create per-request
- NEVER block the async event loop with synchronous calls — use `asyncio.to_thread()` for CPU-bound work
- Log external API failures with context (service name, endpoint, status code, latency)
- Track actual API costs, not hardcoded estimates

## Frontend Rules

- NEVER store auth tokens or sensitive data in localStorage or sessionStorage
- Add Subresource Integrity (SRI) hashes to all externally loaded scripts
- Validate environment variables at build time — fail the build if required vars are missing
- Use proper TypeScript types for API responses — no `any` for data structures
- Wrap page-level components in React error boundaries
- Use Next.js router for navigation — no `window.location.href` redirects
- Deduplicate token refresh logic — only one refresh request should be in-flight at a time

## Code Quality

### Python
- Use `datetime.now(timezone.utc)` — NEVER use `datetime.utcnow()` (deprecated in 3.12, removed in 3.13)
- Type-hint all function signatures
- Use specific exception types — no bare `except:` or `except Exception:` without logging
- Log errors with context before returning None/fallback values
- Keep functions under 50 lines — extract helpers for complex logic

### TypeScript
- Define interfaces for all API response shapes
- No `any` types for data structures — use `unknown` with type guards if the shape is truly unknown
- Handle loading, error, and empty states for all data-fetching components

## Git & Deployment

- NEVER commit `.env`, `.pem`, or credential files
- Pin dependency versions in production — use lockfiles (`pip-compile`, `package-lock.json`)
- Run `alembic upgrade head` as part of deploy, before starting the server
- All schema changes go through Alembic, never through `create_all()`

## Testing (To Be Built)

- Write integration tests for auth flows and data isolation before shipping new features
- Test that user A cannot access user B's data through any endpoint
- Mock external APIs (Gemini, Teller, Ntropy) in tests — never call real APIs
- Run tests in CI before merge — no untested code reaches production

## Known Technical Debt

See `docs/CODE_REVIEW.md` for the full audit. Key items to resolve:
- Teller tokens stored unencrypted (models.py:84)
- Enrichment tasks lack user scoping (categorization.py:50-62)
- No automated tests or CI pipeline
- Auth tokens in localStorage instead of httpOnly cookies
- 49 instances of deprecated `datetime.utcnow()`
