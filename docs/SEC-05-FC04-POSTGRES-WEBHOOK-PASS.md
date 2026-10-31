# SEC05-FC04 — PostgreSQL-backed webhook lifecycle acceptance

**Date:** 2026-10-31
**Branch:** `test/sec05-stripe-prebeta`
**Status:** PASS for this one explicitly opted-in integration test only.

## Command reported by operator

```bash
source /workspaces/Job-Agent-SEC04-Redis/sec04-env.sh
SEC05_PG_INTEGRATION=1 /workspaces/Job-Agent/production_api/.venv/bin/python -m pytest tests/test_sec05_postgres_live.py -v -s
```

## Operator evidence

```text
tests/test_sec05_postgres_live.py::test_sec05_fc04_webhook_lifecycle_postgres
PASS: signed-mock webhook persisted subscription on PostgreSQL
PASS: duplicate webhook ignored after PostgreSQL commit
PASS: canceled authoritative state revokes premium
PASS: stale active event cannot reactivate premium
PASS: price mismatch revokes premium on PostgreSQL
PASS: test-only data cleaned from PostgreSQL
PASSED
1 passed, 1 warning in 1.30s
```

## Scope confirmed
- Real disposable PostgreSQL database `ux_test@127.0.0.1:55433/jobagent_ux`, revision `0006_subscription_price_guard`.
- FastAPI TestClient and simulated Stripe verification / subscription retrieval; **no network requests or real Stripe Test Mode**.
- Sequential webhook duplicate delivery is idempotent; remote authoritative canceled state revokes premium; stale active event cannot reenable while remote status remains canceled; unauthorized price revokes premium.
- Test-specific user, session, subscription and webhook entries removed, verified by final assertions.

## Still open before public charging
- Multiple simultaneous webhooks / races (transaction-level dedup), signature verification with actual Stripe SDK and test secret, real Stripe Test Mode checkout, invoice/payment events, refunds/disputes, billing reconciliation and recovery, customer ownership edge cases, monitoring.
- Fixed-value initial migrations instead of mutable model import; durable Docker environment.
- Do not merge to main, touch PR #2, touch original PostgreSQL databases, or use live Stripe keys.
