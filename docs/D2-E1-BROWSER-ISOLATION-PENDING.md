# D2-E1.3 — Real Chromium ten-account browser isolation

**Status: SCRIPT COMMITTED / NOT EXECUTED.** Do not claim browser acceptance until the operator supplies a passing log.

## Dependencies and scope

- Script: `scripts/d2e1_browser_isolation.py` (Playwright Python).
- Runs headless Chromium against React/Vite at `127.0.0.1:5173` and isolated FastAPI at `127.0.0.1:18081`.
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
D2E1_WEB_URL=http://127.0.0.1:5173 \
D2E1_API_URL=http://127.0.0.1:18081 \
python scripts/d2e1_browser_isolation.py
```

Stop at any failed assertion. Browser acceptance will be recorded only upon actual passing output and review. Rate limiting and recovery security remain separate public-launch gates.
