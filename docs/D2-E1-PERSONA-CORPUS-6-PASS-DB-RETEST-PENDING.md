# D2-E1 — Synthetic persona corpus 6/6 PASS; database retest pending

Date: 2026-10-31
Branch: `test/sec05-stripe-prebeta`

## Reported test evidence

The operator ran `tests/acceptance/test_d2e_persona_corpus.py` after correcting the 10 synthetic fixture emails from the `.test` TLD to `@example.com`.

```text
6 passed, 1 warning in 0.04s
```

Warning: `StarletteDeprecationWarning` (Starlette TestClient, httpx); not a failing test.

## Scope
All six data quality checks passed, including registration schema validation for synthetic email addresses. This does not establish successful database registration, real authentication or ownership isolation.

Prior database suite run: `99 passed, 5 failed, 1 warning in 7.32s`. One observed failure was HTTP 422 during registration; the fixture email TLD was a suspected common cause. We have not yet seen a rerun of those database-backed tests after the fix.

## Required next run

After syncing the branch, rerun `tests/integration` and `tests/acceptance/test_d2e1_identity_red.py` *only* via the previously used Python safety guard that verifies the disposable PostgreSQL container name `jobagent-react-test-db`, the volume `jobagent-react-test-pgdata`, local port 55435, user `react_test`, database `jobagent_react_test` and a credentials file outside the Git repository. That suite resets `public` with DROP SCHEMA; it must never touch main, the original worktree/DBs or the SEC05 financial database.

## Acceptance state
- Persona corpus: PASS 6/6.
- D2-E1 PostgreSQL registration/auth + ten-user isolation: PENDING RETEST.
- Frontend bearer auth, rate limiting, account recovery: OPEN.
- E2–E6: OPEN.
- No Stripe live changes.
