# SEC05-FC03 — Adversarial simulated billing regression

Date: 2026-10-31
Status: **PASS only for the selected SQLite/Stripe-mock test suite**, reported by operator.
Branch: `test/sec05-stripe-prebeta`
Expected checked-out code revision before operator run: `2bba4f9` (operator confirmed fast-forward to this commit range, but exact `git log -1` not included).

## Command
```sh
/workspaces/Job-Agent/production_api/.venv/bin/python -m pytest tests/test_homologation.py tests/test_v3.py tests/test_production.py -v
```

## Operator result
```
collected 21 items
21 passed, 2 warnings in 10.27s
```

SEC05-specific passed: wrong price blocks entitlement; allowed price grants entitlement; missing price blocks; duplicate webhook is idempotent; canceled remote state prevents reactivation from stale event; switching to unrelated price revokes entitlement.

Earlier SEC05-FC02B operator evidence: PostgreSQL transactional insert/read of `stripe_price_id` and rollback PASS; Alembic `0006_subscription_price_guard (head)` PASS.

## Interpretation and remaining release blockers
- These 21 tests run against temporary SQLite and use mocked Stripe. They are NOT real Stripe Test Mode nor real PostgreSQL webhook end-to-end tests.
- Concurrency/races, replay across processes, Stripe signature verification using the real SDK, invoice events, refunds, payment failures, grace windows, reauthorization, reconciliation and observability remain open.
- Dynamic `0001_initial` schema construction from mutable Base.metadata is a known migration debt. 0006 compatibility guard addresses only this observed duplicate-column issue.
- Disposable Docker DB has repeatedly appeared empty after environmental interruption; data persistence/root cause must be fixed before broader launch.
- Do not modify `main`, PR #2, original PostgreSQL containers or existing user data.
