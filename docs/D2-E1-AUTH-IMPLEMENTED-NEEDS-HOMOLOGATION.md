# D2-E1 — Auth implementation checkpoint (awaiting execution)
**Date:** 2026-10-31
**Branch:** `test/sec05-stripe-prebeta`
**Status:** CODE IMPLEMENTED, TEST EXECUTION AND E1 ACCEPTANCE PENDING.

## Implemented in this branch
- `backend/app/models/auth.py`: `auth_credentials` table by user UUID, Argon2 password hash; `auth_sessions` with only SHA-256 token digest, expiry, revocation and user FK.
- `backend/migrations/versions/0002_d2e1_auth.py`: explicit Alembic revision `0002`, parent `0001` confirmed from `backend/migrations/versions/0001_initial_schema.py`.
- `backend/app/services/auth.py`: opaque random bearer tokens; register/login/lookup/logout, TTL 12 hours, commit/rollback handling, uniqueness enforced by existing users email index.
- `backend/app/api/v1/auth.py` routes `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`.
- `backend/app/api/deps.py`: user identity from bearer token. Shared local D1 user fallback is disabled by default and only permitted with explicit `ALLOW_LEGACY_LOCAL_USER=1` in nonproduction.
- `backend/app/core/config.py`: forbids legacy fallback in production.
- `backend/app/main.py`: allows Authorization CORS request header.
- `backend/pyproject.toml`: `argon2-cffi` and `email-validator`.
- Legacy D1 tests explicitly set `allow_legacy_local_user=True` in their isolated FastAPI fixtures. Browser contract live test previously passed in D1 default-user mode; after this change it must be rerun explicitly in isolated compatibility mode until React auth is wired.
- `backend/tests/acceptance/conftest.py`: strict-auth DB fixture.
- `backend/tests/acceptance/test_d2e1_identity_red.py`: all 10 synthetic accounts, 90 cross-account foreign job reads, no anonymous access, independent sessions, duplicates, incorrect password, expiry and logout.
- `backend/tests/unit/test_auth_basics.py`: fail-closed settings, Argon2, bearer digest, auth route/CORS tests.
- `backend/tests/unit/test_models_metadata.py`: updated table expectations and PK/FK index checks.

## What is NOT yet proved
**None of the changed-code tests or migrations have been executed by the operator yet.** Prior 353 existing PASS and corpus 5 PASS are historical baseline on older code.
- New auth API may have integration or migration errors discovered by tests.
- Rate limiting of credential attempts is not implemented yet: **blocker before exposing public auth endpoint**.
- Password reset, account recovery, front-end login UX and complete React bearer authorization remain to be designed/implemented.
- D2-E1 only PASS once all new strict-auth integration checks pass with actual PostgreSQL, old suites regress cleanly, and security requirements (including brute-force protection) are met.
- E2–E6 NOT IMPLEMENTED on unified API; Stripe remains deferred.

## First safe execution (NO PostgreSQL or migrations)
```bash
cd /workspaces/Job-Agent-SEC05
git fetch origin test/sec05-stripe-prebeta
git merge --ff-only origin/test/sec05-stripe-prebeta
cd backend
.venv/bin/python -m pip install -e ".[dev]"
unset TEST_DATABASE_URL REQUIRE_TEST_DATABASE
.venv/bin/python -m pytest tests/unit tests/api tests/acceptance/test_d2e_persona_corpus.py -q --tb=short
```

## Subsequent database gate (requires separate guarded run)
`tests/integration` and `tests/acceptance/test_d2e1_identity_red.py` use a fixture that `DROP SCHEMA public CASCADE` and rebuilds it. Only on dedicated, explicitly verified `jobagent-react-test-db`, DB `jobagent_react_test`, loopback `127.0.0.1:55435`, volume `jobagent-react-test-pgdata`, user `react_test`, and local-only credentials. Never run them with original, SEC05, shared or production DATABASE_URL.

## Follow-up implementation
- Run migration+DB integration, resolve any test issues.
- Add centralized rate limiting and prevent account enumeration.
- Wire frontend auth and revalidate the five live frontend contracts.
- E2: import resume/review -> E3 ledger -> E4 diagnosis -> E5 grounded draft -> E6 full UI journey for P01–P10.
- Record actual logs and PASS only after rerun.

## Isolation
Only `test/sec05-stripe-prebeta`, never main or PR #2. Preserve original worktree, DBs, and SEC05 volume. No real user data, secrets, or hardcoded actual passwords checked in.
