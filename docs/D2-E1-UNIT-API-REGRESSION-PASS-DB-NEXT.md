# D2-E1 — Unit/API regression PASS; PostgreSQL acceptance next
Date: 2026-10-31
Branch: test/sec05-stripe-prebeta

## Evidence
Operator explicitly confirmed the retest after fixing `test_auth_routes_are_versioned_and_bearer_header_allowed`: **"passou, tudo certo"**.
The previous run had 118 PASS / 1 FAIL. The assertion was replaced by verification of public OpenAPI endpoints in commit `6cbbd37`. The operator did not provide the exact summary of the newest passing run, so we **do not claim an independently verified exact count**.

## Approved scope
Unit/API and ten-persona corpus regression confirmed by operator. No DB integration of newly added E1 auth has been performed yet.

## Mandatory next step
Run `tests/integration` and `tests/acceptance/test_d2e1_identity_red.py` against ONLY the dedicated disposable PostgreSQL:
- container `jobagent-react-test-db`, healthy
- volume `jobagent-react-test-pgdata` mounted at `/var/lib/postgresql/data`
- host bind `127.0.0.1:55435`
- user `react_test`, database `jobagent_react_test`
- credentials held in `/workspaces/.jobagent-react-test.env`.

The fixture `tests/integration/conftest.py` executes `DROP SCHEMA public CASCADE`, so confirm container, volume, port and SQL identity BEFORE invoking pytest. This intentionally destroys old TEST data in the disposable React database only.

Execute both suites in a single pytest process after guard validation, with `TEST_DATABASE_URL` and `REQUIRE_TEST_DATABASE=1` set only on a subprocess environment. No `DATABASE_URL` inheritance and never echo credentials.

## Remaining gates
No E1 PostgreSQL PASS claim yet. Following DB test fixes: frontend bearer handling, strict-auth live contract, brute-force protection/rate limiting, password lifecycle, and final E1 acceptance. E2–E6 remain open. Keep main/PR#2, original worktrees and other databases untouched.
