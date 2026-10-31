# D2-E1.4 — Auth security hardening (implementation checkpoint)

**Status: CODE COMMITTED — BACKEND REGRESSION NOT EXECUTED. DO NOT MARK PASS.**
**Branch:** `feature/d2-e1-react-auth-ui`; PR #3 remains draft.

## What is implemented

- Alembic revision `0003` creates `auth_rate_limits`, a persistent PostgreSQL table with an index for bounded cleanup. Migration has **not been run by the agent**; existing DBs remain unchanged.
- Atomic `INSERT ... ON CONFLICT DO UPDATE` increments a fixed-window counter using PostgreSQL statement time. Counters are shared across API processes and restarts if the same database and HMAC secret are used.
- IP-based pre-validation middleware counts each login and registration POST even if payload validation fails. Defaults: login 60/IP/15 minutes; registration 10/IP/15 minutes.
- Login account-based limiter counts normalized email 12/15 minutes; successful logins also consume capacity. No plaintext emails or IP addresses stored in the counter table: HMAC-SHA256 secret from environment.
- Exceeded limit yields HTTP 429 and Retry-After. Store failures fail closed as HTTP 503; no fallback to process memory.
- Production settings refuse startup if limiter disabled or secret shorter than 32 characters. Development/test default disabled to preserve the existing 104-test regression; explicit dedicated security tests enable it.
- Client IP originates from ASGI scope only. **Do not trust X-Forwarded-For from the client.** If behind a reverse proxy, Uvicorn must trust only specific proxy IPs using `--forwarded-allow-ips`. Never set `*` unless ingress is strictly isolated and guaranteed.
- React authentication forms display a safe temporary-block message for HTTP 429.
- New tests: `tests/acceptance/test_d2e14_rate_limit.py` (malformed-body IP limiting, per-account brute force, fail-closed, multi-worker shared counter) and `tests/acceptance/test_d2e14_idor.py` (direct foreign job/application UUID GET/PATCH/DELETE 404, foreign application creation 422 and anonymous 401).

## Verification: first read-only checks

From the isolated worktree after fast-forward (no database changes):

```bash
cd /workspaces/Job-Agent-D2-E1-UI/backend
/workspaces/Job-Agent-SEC05/backend/.venv/bin/python -m compileall -q app tests/acceptance
/workspaces/Job-Agent-SEC05/backend/.venv/bin/python -m ruff check app tests/acceptance
```

If Ruff is unavailable in the chosen backend venv, activate the existing backend dev venv that was already used for the prior 104-test acceptance; do not install a global Python package.

## Verification: integration tests WARNING — destructive only to disposable DB

The existing `tests/integration/conftest.py` intentionally runs `DROP SCHEMA public CASCADE` and applies `alembic upgrade head` during the pytest session. **This destroys every account, job and test artifact currently in the selected test database.** It must never be run with `jobagent-sec05-db` port 55434, `jobagent-postgres-v2` port 5432, any original database, or anything not explicitly disposable.

The operator must first:
1. Stop the isolated FastAPI process bound to the disposable DB so it has no active pool connections.
2. Verify the disposable container identity, database name, user, host port and exact `TEST_DATABASE_URL` destination without printing credentials.
3. Acknowledge reset of `jobagent_react_test` and its synthetic browser data; alternatively provision a separate dedicated disposable `*_test` DB for this test suite.
4. Run the existing guarded acceptance harness with `REQUIRE_TEST_DATABASE=1`, `TEST_DATABASE_URL` explicitly set to the verified disposable destination; record PostgreSQL revision `0003` afterward.
5. Repeat all backend regression, then React unit, build and five authenticated live contracts after restarting API against revision 0003, and Playwright 10-user test.
6. Do NOT upgrade, downgrade or reset any other database.

## Open risks / not launched

- Fixed-window per-email limits may cause temporary account lockout from malicious traffic; tune thresholds and monitor before public access.
- Duplicate registration still returns 409; account enumeration-resistant registration semantics and recovery/email verification are **not resolved**.
- MFA, password reset, token/session management, HTTPS/TLS, reverse proxy trust hardening and monitoring remain release gates.
- This implementation has not been compiled, linted, run or validated by Codespaces at the time of this document. Never claim security PASS until operator evidence is supplied.
