# D2-C — PostgreSQL React backend integration PASS
Date: 2026-10-31
Branch: `test/sec05-stripe-prebeta`

## Operator-reported evidence
After provisioning and validating the dedicated container `jobagent-react-test-db` with PostgreSQL `jobagent_react_test` on host loopback port 55435, operator ran the guarded `backend/tests/integration` suite:
```text
98 passed, 1 warning in 5.86s
D2-C: BACKEND INTEGRATION PASS
```
The preceding command checked container name, health, named volume `jobagent-react-test-pgdata`, exact loopback port, credential file and SQL-reported database identity before invoking pytest with `REQUIRE_TEST_DATABASE=1`. This checkpoint records the reported outcome, not an independently rerun execution by the assistant.

## Acceptance bounds
- D2-C PostgreSQL integration + migrations: **PASS**, 98/98 reported.
- `backend/tests/unit` + `tests/api`: previously 110 PASS.
- `production_api/tests`: previously 72 PASS, separate API/architecture.
- React frontend Vitest: previously 68 PASS, 5 skipped. Typecheck, lint, build PASS.
- Total unit/API/integration frontend/backend invocations passing to date: **348** (72+68+110+98), across separate suites. No unified journey or live React contract PASS claim.
- Stripe account unavailable; FC06B–D remain paused.
- Frontend `src/services/contract.live.test.ts` contains **5 skip-by-default live tests** awaiting dedicated-backend execution.

## Critical discovery
`frontend` calls `/api/v1` supported by `backend/app`, not the `production_api` endpoints `/api` with authentication, import and career intelligence. `backend/app/api/deps.py` currently assigns a local default user automatically (D1), not full authentication. Therefore contract PASS is a milestone, but **not** an end-to-end real-user login, resume-import or multi-user test.

## Next action: D2-D live React contract
1. Validate the dedicated container identity, healthy state, port 55435, volume, database name and Alembic migration status again; do not run any integration fixtures or migrations against original/SEC05 DB.
2. Start `backend/app.main:create_app` using `backend/.venv` on a free loopback port, with `APP_ENV=test` and only the dedicated React DB URL.
3. Verify `GET /ready` returns 200; run `frontend` `VITE_LIVE_CONTRACT=1 VITE_API_URL=http://127.0.0.1:<port> npm test -- contract`. These live tests WRITE test records; ensure exclusive disposable target.
4. Stop the test server after execution and capture pass/fail; do not assume PASS.
5. Then decide canonical integration architecture for resume/ledger and real authentication before first user pilot.

## Safety
Preserve main, PR #2, original worktrees, original PostgreSQL containers `jobagent-postgres-v2` and `jobagent-postgres-recovered`, and SEC05 `jobagent-sec05-db`. Credentials only in ignored /workspaces environment file; never print them or commit personal resumes.
