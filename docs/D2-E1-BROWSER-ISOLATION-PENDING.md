# D2-E1.3 — Real Chromium ten-account browser isolation

**Status: SCRIPT COMMITTED / NOT EXECUTED.** Do not claim browser acceptance until the operator supplies a passing log.

## Dependencies and scope

- Script: `scripts/d2e1_browser_isolation.py` (Playwright Python).
- Runs headless Chromium against React/Vite at `localhost:5173` and isolated FastAPI at `127.0.0.1:18081`.
- Requires 10 synthetic account registrations and 10 synthetic jobs; it **writes data** to the API DB. It never drops or recreates a schema.
- Each identity uses its own browser context. Every account sees its own synthetic job and not the other nine (90 negative list checks). Same-context logout/account switch and refresh requiring login are also asserted.
- No real emails, users, credentials, tokens or screenshots included in commits.

## Critical isolation gate (operator performs BEFORE running)

1. Confirm `jobagent-react-test-db`, `jobagent_react_test`, `react_test`, loopback 55435 are the actual DB target.
2. Verify the running API process on loopback port 18081 is *still* configured to this DB. A `/ready` response alone only proves its configured DB is reachable, not which one it is. Inspect launch method/environment without printing passwords.
3. Keep `jobagent-sec05-db` (55434), `jobagent-postgres-v2` (5432), other worktrees and PR #2 untouched.
4. If the API is not confirmed isolated, **do not run** the script.
5. `D2E1_BROWSER_DISPOSABLE_ACK` is an operator acknowledgement, not a cryptographic or automatic proof of DB binding.
6. Ensure Python Playwright is available in a disposable tooling environment; `python -m pip install playwright` / `python -m playwright install chromium` may download dependencies and do not alter the repository lockfile.
7. Start React with `VITE_API_URL=http://127.0.0.1:18081 npm run dev -- --host 127.0.0.1` in a separate terminal (from `frontend`).

## Run (from repository root)

```bash
D2E1_BROWSER_DISPOSABLE_ACK=jobagent_react_test \
D2E1_WEB_URL=http://localhost:5173 \
D2E1_API_URL=http://127.0.0.1:18081 \
python scripts/d2e1_browser_isolation.py
```

Stop at any failed assertion. Browser acceptance will be recorded only upon actual passing output and review. Rate limiting and recovery security remain separate public-launch gates.

## Browser preflight gate / first failure

The first Playwright run filled the registration form but the UI displayed a generic registration error before account creation. Suspected mismatch: backend `CORS_ORIGINS=http://localhost:5173` vs browser `http://127.0.0.1:5173`; exact cause must be confirmed by OPTIONS preflight. The script now defaults to `http://localhost:5173` and runs a browser-origin CORS preflight before creating any accounts. This change is not yet executed/accepted. If preflight fails, inspect the API CORS configuration rather than weakening backend security or changing the database.

## Second operator run — memory-only bearer navigation correction

The CORS-aligned browser run reached registration and authenticated navigation, then failed while waiting for the Jobs heading. The browser showed the login screen after `page.goto(web + "/jobs")`. The cause is a full document navigation: React's intentionally memory-only bearer token is cleared whenever the app reloads. This is a test navigation bug, not evidence that login failed or cross-account isolation broke.

Commit `6e32caf` updates authenticated navigation to click the React Router `Main` navigation's `Jobs` link; the explicit `page.goto` after logout is retained as the deliberate unauthenticated redirect test. The account-switch scenario now expects the Jobs page because its requested destination is preserved across login. **Not executed since this correction; browser PASS not yet claimed.**

## Operator acceptance — D2-E1.3 BROWSER ISOLATION PASS (2026-10-31)

**Status: PASS (operator-reported Playwright run).** The operator fast-forwarded this worktree to commit `fb8fd3d` and ran `scripts/d2e1_browser_isolation.py` against local React `http://localhost:5173` and the isolated API `http://127.0.0.1:18081` with the `jobagent_react_test` acknowledgement. Synthetic run identifier `4bceaebcfd`.

Observed output:
- All ten synthetic accounts: register, login, create job **PASS (10/10)**.
- Each account's browser job list showed its own item and did not show the other nine synthetic job titles: **10/10 account isolation passes; 90 foreign-job absence assertions**.
- Same-context logout and login as a different account, with corresponding job list isolation: **PASS**.
- Full browser refresh discards memory-only bearer and requires login: **PASS**.
- Final: `D2-E1.3 BROWSER ISOLATION PASS — 10 accounts, 90 foreign-job absences`.

Evidence scope: real Chromium browser UI, opt-in synthetic write operations against an operator-confirmed disposable database. This does **not** establish full coverage of direct object-level authorization across every endpoint or production security.

**Still open before D2-E1 COMPLETE:** rate limiting / brute force mitigation, credential/account security review, production-like deployment hardening and any further multiuser direct-object API checks. PR #3 remains draft; `main`, PR #2, original databases remain unchanged.
