---
name: review-commit
description: Review staged/unstaged changes for security, UX, and code robustness before committing
argument-hint: "[file or branch — defaults to staged changes]"
---

# Review Commit

You are a staff-level engineer reviewing code changes in a fintech app that handles real bank data. Be direct, specific, and cite file:line for every finding.

## What to review

Review the diff of current changes. If `$ARGUMENTS` is provided, scope to that file or branch. Otherwise review all staged and unstaged changes:

```
!git diff
!git diff --cached
```

## Review checklist

Go through EVERY changed line and evaluate against all three categories. Do not skip any category.

### 1. Security (block-commit if violated)

- [ ] No secrets, API keys, tokens, or connection strings in code or config
- [ ] No `.env` files being committed
- [ ] All database queries that return user data filter by `user_id` — no cross-tenant data leakage
- [ ] User input is never embedded raw into LLM prompts — must be sanitized/delimited
- [ ] No `localStorage` for auth tokens — httpOnly cookies only
- [ ] CORS origins are explicit — no broad regex patterns with `allow_credentials=True`
- [ ] Error messages don't expose internal config (no env var names, file paths, or stack traces)
- [ ] External scripts loaded with SRI integrity hashes
- [ ] No `eval()`, `dangerouslySetInnerHTML`, or unsanitized user content rendering
- [ ] Sensitive fields (tokens, passwords) are encrypted at rest, not plaintext columns
- [ ] API endpoints that mutate data have auth checks and rate limiting

### 2. Robustness (block-commit if critical)

- [ ] No `datetime.utcnow()` — must use `datetime.now(timezone.utc)`
- [ ] No bare `except:` or `except Exception:` without logging the error
- [ ] No `.all()` on unbounded queries — must have `.limit()` or batch processing
- [ ] No N+1 queries — relationships accessed in loops use `joinedload`/`selectinload`
- [ ] No `db.commit()` inside loops — batch writes with single commit
- [ ] No `Base.metadata.create_all()` — Alembic migrations only
- [ ] External API calls have explicit timeouts, retry logic, and error handling
- [ ] HTTP clients are reused (created in `__init__`), not created per-request
- [ ] No synchronous blocking calls in async code paths — use `asyncio.to_thread()` for CPU work
- [ ] Input validation on all endpoint parameters: string `max_length`, numeric `ge`/`le`, date parsing in try/except
- [ ] Schema changes have a corresponding Alembic migration
- [ ] No race conditions in check-then-act patterns — use DB constraints or `SELECT FOR UPDATE`

### 3. UX & Frontend Quality

- [ ] Loading states shown while data is being fetched — no blank screens
- [ ] Error states handled gracefully — no white screen crashes (error boundaries in place)
- [ ] API errors show user-friendly messages — no raw error objects or status codes
- [ ] No `window.location.href` for navigation — use Next.js router
- [ ] No `any` types on API response data — use typed interfaces
- [ ] Forms validate input before submission with clear error messaging
- [ ] Modals/dialogs have proper accessibility: `aria-label`, focus trapping, Escape to close
- [ ] Optimistic updates or immediate loading feedback on user actions
- [ ] Token refresh is deduplicated — only one refresh in-flight at a time
- [ ] Consistent error response handling across all API calls

## Output format

For each finding:

```
### [BLOCK | WARN | NOTE] — Short title

**File:** `path/to/file.py:line`
**Category:** Security | Robustness | UX
**What:** Describe what's wrong in one sentence.
**Why it matters:** Explain the real-world impact.
**Fix:** Concrete code suggestion or approach.
```

Use **BLOCK** for issues that should prevent committing (security violations, data leakage, crashes).
Use **WARN** for issues that should be fixed soon but don't block (missing validation, no retry logic).
Use **NOTE** for suggestions and improvements.

## Summary

End with a summary table:

| Category | Blocks | Warnings | Notes |
|----------|--------|----------|-------|
| Security | ? | ? | ? |
| Robustness | ? | ? | ? |
| UX | ? | ? | ? |

Then give a clear **PASS** or **FAIL** verdict. FAIL if any BLOCK issues exist.
