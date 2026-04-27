# Release Plan: 10-Person Beta

## Current State

The app is feature-complete for a personal finance tool: bank connection (Teller), AI categorization (Gemini cascade), dashboard analytics, AI chat (Claude), anomaly detection, goals, insights. Landing page, privacy policy, and terms of service exist. Deployed on Railway (backend) + Vercel (frontend).

**What's missing is hardening, not features.**

---

## Tier 1: Must Fix (Blocks Beta)

These will cause crashes, data leaks, or broken UX for your friends.

### 1. Input Validation on Auth Schemas
**Why:** `UserRegister`, `UserLogin`, `PasswordResetConfirm` accept unbounded strings. Someone fat-fingering or a bot could send a 1MB password and crash the server.
- Add `max_length` to email (254), password (128), name (100)
- Add `min_length` to password (8)
- Add `EmailStr` type for email fields
- Add password validation to `PasswordResetConfirm`
- **Files:** `backend/app/schemas/schemas.py`
- **Effort:** 30 min

### 2. LLM Call Timeouts
**Why:** Gemini and Claude calls have no timeout. One slow LLM response = request hangs forever, user thinks app is broken.
- Set explicit timeout on Anthropic client (30s)
- Set explicit timeout on Gemini calls (30s)
- Add timeout to chat service LLM calls
- **Files:** `backend/app/services/chat_service.py`, `backend/app/services/gemini_enrichment.py`
- **Effort:** 30 min

### 3. Background Task User Isolation
**Why:** Enrichment tasks can process transactions across all users. User A's sync could enrich User B's transactions.
- Add `user_id` filter to all enrichment queries in background tasks
- **Files:** `backend/app/routers/categorization.py:50-62`, `backend/app/services/cascade_enrichment.py`
- **Effort:** 1 hr

### 4. Unbounded Query Guards
**Why:** Several `.all()` calls with no `.limit()`. 10 users with 10K transactions each = 100K rows fetched into memory.
- Add `.limit()` to all unbounded `.all()` queries (tags, transactions, etc.)
- Audit every router for missing pagination bounds
- **Files:** Multiple routers, grep for `.all()`
- **Effort:** 1-2 hrs

### 5. Fix Branding Inconsistency
**Why:** App says "Finance Buddy" in some places, "FinTrack" in others. Contact emails reference `fintrack.app` and `financebuddy.com`. Looks unfinished.
- Pick one name. Unify across: layout metadata, landing page, privacy/terms, settings, contact emails
- **Files:** `frontend/src/app/layout.tsx`, `frontend/src/app/landing/page.tsx`, `frontend/src/app/privacy/page.tsx`, `frontend/src/app/terms/page.tsx`, `frontend/src/app/settings/page.tsx`
- **Effort:** 1 hr

### 6. Add Global Error Boundary
**Why:** No `error.tsx` files exist. An unhandled JS error = white screen. Your friends will think the app is dead.
- Add `error.tsx` to root app directory and key route groups
- Add a simple fallback UI: "Something went wrong" + retry button
- **Files:** `frontend/src/app/error.tsx`, `frontend/src/app/(authenticated)/error.tsx`
- **Effort:** 30 min

### 7. Pre-Deploy Migration Runner
**Why:** Railway doesn't run `alembic upgrade head` automatically. If you push a schema change, the app boots with a stale schema and crashes.
- Update Dockerfile CMD or add entrypoint script: `alembic upgrade head && uvicorn ...`
- **Files:** `backend/Dockerfile`
- **Effort:** 15 min

---

## Tier 2: Should Fix (Improves Beta Quality)

Won't block launch, but will cause confusion or minor issues.

### 8. Encrypt Teller Access Tokens
**Why:** Bank tokens stored in plaintext. For 10 friends this is low-risk, but if your Supabase DB is ever exposed, attackers get bank access.
- Encrypt at rest with Fernet (symmetric key from env var)
- Decrypt on read when calling Teller API
- **Files:** `backend/app/models/models.py`, `backend/app/services/teller_service.py`
- **Effort:** 3-4 hrs

### 9. Move Auth Tokens to httpOnly Cookies
**Why:** Tokens in localStorage are XSS-vulnerable. Low risk with 10 trusted users, but violates your own CLAUDE.md guidelines.
- Set tokens in httpOnly, Secure, SameSite=Lax cookies on login/refresh
- Update frontend to stop reading localStorage for tokens
- Update backend auth to read from cookies
- **Files:** `backend/app/routers/auth.py`, `backend/app/core/security.py`, `frontend/src/lib/auth.ts`, `frontend/src/lib/api.ts`
- **Effort:** 3-4 hrs

### 10. User-Facing Enrichment Status
**Why:** Enrichment runs silently in background. Users don't know if categorization succeeded, failed, or is still running. Budget exhaustion is also silent.
- Add enrichment status to transaction list (badge: "enriching...", "enriched", "failed")
- Notify user when enrichment budget is low/exhausted
- **Files:** `frontend/src/app/transactions/page.tsx`, `backend/app/routers/categorization.py`
- **Effort:** 2-3 hrs

### 11. Toast Notification System
**Why:** No global feedback mechanism. Success/error states only show as inline boxes in specific components.
- Add a lightweight toast library (react-hot-toast or sonner)
- Wire up to: bank sync, enrichment, settings actions, chat errors
- **Files:** `frontend/src/app/layout.tsx`, various components
- **Effort:** 1-2 hrs

### 12. Better Onboarding Copy
**Why:** Dashboard shows sandbox credentials ("username/password") even in production. Getting Started guide is minimal.
- Conditionally show sandbox info only when `TELLER_ENV=sandbox`
- Improve welcome state: explain what the app does, what to expect after connecting
- **Files:** `frontend/src/app/page.tsx`
- **Effort:** 1 hr

### 13. Add Security Headers to Backend
**Why:** Missing `X-Content-Type-Options`, `Strict-Transport-Security`, `X-Frame-Options` on API responses.
- Add middleware for security headers
- **Files:** `backend/app/main.py`
- **Effort:** 15 min

---

## Tier 3: Nice to Have (Post-Beta)

### 14. Automated Tests
- Auth flow integration tests (register, login, refresh, data isolation)
- Enrichment pipeline unit tests
- Dashboard query tests
- **Effort:** 2-3 days

### 15. CI/CD Pipeline
- GitHub Actions: lint, test, type-check on PR
- Auto-deploy to staging on `develop`, production on `main`
- **Effort:** half day

### 16. Rate Limiting on Expensive Endpoints
- Dashboard, chat, enrichment triggers — add per-user rate limits
- Not needed for 10 users but good hygiene
- **Effort:** 1-2 hrs

### 17. Tighten CSP Headers
- Remove `unsafe-inline` and `unsafe-eval` from frontend CSP
- Use nonces or hashes instead
- **Effort:** 2-3 hrs

### 18. Fix 49x `datetime.utcnow()` Deprecation
- Replace all with `datetime.now(timezone.utc)`
- **Effort:** 1 hr (mechanical)

### 19. Auto-Sync Scheduler
- Currently user must manually sync. Add periodic background sync (daily or on dashboard load if stale >24h).
- **Effort:** half day

### 20. Request Logging & Observability
- Add request ID middleware, structured logging, error tracking (Sentry)
- **Effort:** half day

---

## Effort Summary

| Tier | Items | Estimated Effort |
|------|-------|-----------------|
| **Tier 1 (Must Fix)** | 7 items | ~5-6 hours |
| **Tier 2 (Should Fix)** | 6 items | ~11-15 hours |
| **Tier 3 (Post-Beta)** | 7 items | ~5-6 days |

**Minimum viable beta: Tier 1 only = one focused day of work.**

---

## Launch Checklist

- [ ] Tier 1 items complete
- [ ] Test registration → bank connect → dashboard flow end-to-end
- [ ] Verify Teller is in `development` mode (not sandbox) for real bank connections
- [ ] Confirm all env vars set in Railway & Vercel
- [ ] Run `alembic upgrade head` on production DB
- [ ] Test on mobile (responsive layout)
- [ ] Send friends the landing page URL with brief instructions
- [ ] Monitor Railway logs for first 24 hours
