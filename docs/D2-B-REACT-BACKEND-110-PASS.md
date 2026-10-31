# D2-B — Backend React unit/API regression: 110 PASS
Date: 2026-10-31
Branch: `test/sec05-stripe-prebeta`

## Operator-reported execution
```bash
unset TEST_DATABASE_URL
unset REQUIRE_TEST_DATABASE
.venv/bin/python -m pytest tests/unit tests/api -q --tb=short
```

```text
.............................................................................................................. [100%]
110 passed, 1 warning in 1.57s
```

The warning was `StarletteDeprecationWarning` from FastAPI TestClient recommending `httpx2`. No integration tests with a live PostgreSQL database were included.

This followed installing the backend's separately declared Python dependencies into its own `backend/.venv`. A prior attempt using `production_api/.venv` did not collect tests because `pydantic_settings` was missing.

## Verified checkpoint boundaries
- `production_api/tests`: 72 PASS previously (SQLite/temp environment).
- React frontend: 68 PASS, 5 SKIPPED in Vitest, TypeScript/lint/build PASS previously.
- `backend/tests/unit` and `backend/tests/api`: 110 PASS as reported here.
- Total 250 passing test invocations in separate suites; this does NOT constitute end-to-end acceptance nor production readiness.
- `backend/tests/integration/conftest.py` calls `DROP SCHEMA public CASCADE` for a test DB whose name ends with `_test`. Do **NOT** point these tests to original DBs, SEC05 database, or a shared DB. A dedicated disposable PostgreSQL container/database is mandatory.
- Live frontend contract skipped; frontend currently calls `backend/app` versioned `/api/v1` endpoints. `production_api` is architecturally separate and contains the resume/Fact Ledger/diagnostic functionality that must be integrated deliberately.
- `npm audit --omit=dev`: 0 vulnerabilities; full audit: 14 dev-tree alerts (12 moderate, 2 high) affecting minimatch, undici, zod; remediate deliberately.
- Stripe Test Mode still pending due to no Stripe account.

## Next checkpoint
1. Dedicated, explicitly disposable PostgreSQL for `backend/` (not SEC05 DB), migrations and integration tests, then frontend live contract.
2. Design canonical path for user journey and integrate resume import, Master Profile/Fact Ledger, grounded diagnosis into versioned API.
3. E2E journey with synthetic profiles and user validation.

**Isolation:** preserve main, PR #2, original worktree, original PostgreSQL instances, and SEC05 Postgres volume. No destructive operations on unverified targets.
