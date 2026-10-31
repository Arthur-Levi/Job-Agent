# SEC-05 FC01 — SQLite / Stripe mock regression

Date: 2026-10-31
Status: **PASS for the selected simulated test suite only**.
Branch: `test/sec05-stripe-prebeta`; code tested at commit `f119d61` (per update instructions from prior turn; operator's log does not separately print git SHA, so this commit attribution is expected, not independently verified).

Operator command:
```
/workspaces/Job-Agent/production_api/.venv/bin/python -m pytest tests/test_homologation.py tests/test_v3.py tests/test_production.py -v
```
Result reported:
```
collected 18 items
18 passed, 2 warnings in 9.31s
```

The three FC01 scenarios passed: foreign Stripe price cannot grant premium, authorized price grants premium, and absent price denies premium. Other selected API/UI/access regression tests passed. Two third-party API deprecation warnings remain (FastAPI/Starlette/httpx, and HTTPX `data` argument).

**Not yet proven:** Alembic revision `0006_subscription_price_guard` in disposable real PostgreSQL, real Stripe test-mode interactions, concurrency/webhook replays, cancellation/refunds, invoice reconciliation, production readiness. Do not mark SEC-05 complete.

**Safety:** PostgreSQL test instance only `ux_test@127.0.0.1:55433/jobagent_ux`; verify live database identity before migration. Never modify original databases, main, or PR #2. Do not commit secrets or `sec04-env.sh`.
