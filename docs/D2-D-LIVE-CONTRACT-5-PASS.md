# D2-D — LIVE React ↔ FastAPI ↔ PostgreSQL contract PASS
**Date:** 2026-10-31
**Branch:** `test/sec05-stripe-prebeta`
**Status:** PASS from operator-submitted terminal output; no independent rerun.

## Setup validated by the operator script
- Dedicated disposable PostgreSQL `jobagent-react-test-db`, database `jobagent_react_test`, 127.0.0.1:55435, existing migrations.
- `PASS: banco React isolado e migrado`
- `PASS: FastAPI /ready = 200`
- `backend/app.main:create_app` started with `APP_ENV=test` on 127.0.0.1:18080.
- Frontend live contract enabled only for this run: `VITE_LIVE_CONTRACT=1 VITE_API_URL=http://127.0.0.1:18080 npm run test -- contract`.

## Test evidence
```text
✓ src/services/contract.live.test.ts (5 tests)
Test Files  1 passed (1)
Tests       5 passed (5)
Duration    2.06s
D2-D: LIVE CONTRACT PASS
Servidor temporário encerrado
```

Five scenarios passed:
1. Frontend enum declarations equal live backend OpenAPI.
2. Profile: get/create/update and response field shape.
3. Jobs: monetary strings, nullable updates, pagination and error envelope.
4. Applications: permitted status transitions, history, forced transitions and protected deletion.
5. Job deletion without applications returns HTTP 204.

## Cumulative regression counts (separate runs)
- `production_api`: 72 PASS.
- React frontend isolated: 68 PASS and 5 previously SKIPPED (now tested live separately).
- `backend` unit/API: 110 PASS.
- `backend` PostgreSQL integration: 98 PASS.
- React/FastAPI/PostgreSQL live contract: 5 PASS.
- **353 passing test cases reported across distinct executions**, not a single end-to-end suite. No claim of release or customer-value validation.

## Outstanding product architecture gate
- `frontend/src/services/` targets `backend/app` routes `/api/v1/*`.
- `backend/app/api/deps.py` currently uses `get_current_user` -> `UserService.get_or_create_default()`, a **single default local identity**. No evidence of true register/login/multi-user isolation through the React UI; NOT safe to expose publicly as a multi-user SaaS.
- `production_api/main.py` has session authentication, resume upload/preview/confirm, Master Profile and Fact Ledger, grounded diagnostic and resume, billing.
- These are **two distinct data models and API contracts**. A passing contract suite for profiles/jobs/applications does not imply resume import/grounded career functions exist in the React backend.
- Stripe real test mode FC06B–D deferred due to no account.
- npm audit production-only 0 advisories at the time; full dev-tree audit 14 advisories, remediation open.

## Recommended D2-E plan
1. Decide and document canonical unified user/auth/data model and API shape BEFORE porting functionality.
2. First priority: secure real account registration, login, token/session lifecycle and ownership, with isolated PostgreSQL tests; never ship the D1 default-user path in a public beta.
3. Bring resume preview/confirm and deduplication into the unified API with explicit user review, data ownership and provenance.
4. Add Master Profile + Fact Ledger, grounded diagnostic, job comparison, and grounded resume under the same authenticated user.
5. Implement React screens for the path: register/login -> upload/review -> confirmed profile -> job -> diagnostic -> resume/action.
6. Run deterministic E2E synthetic user corpus, security/isolation, real browser usability, then 5–10-person consenting free pilot.
7. Track metrics for time to first value, fact accuracy, invented claims (zero), help required and actionable outcomes.

## Isolation
No changes to main, PR #2, original worktree, original DBs or SEC05 database. D2-D writes only to dedicated disposable React DB. No secrets in Git. No Stripe Live.
