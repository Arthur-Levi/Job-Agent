# SEC05-FC06A — Real Stripe SDK signed-webhook acceptance

Date: 2026-10-31
Branch: `test/sec05-stripe-prebeta`
Status: **PASS (operator-run)**.

## Result and scope

Operator executed `tests/test_sec05_stripe_sdk_signed.py` in the isolated persistent PostgreSQL environment, using `SEC05_PG_INTEGRATION=1`, local PG credentials file, and the Python venv. Reported:

```text
tests/test_sec05_stripe_sdk_signed.py::test_sec05_fc06a_real_sdk_signed_webhook
PASS: real Stripe SDK rejects altered signed payload
PASS: real SDK signature authorizes matching active Stripe subscription
PASS: signed replay is idempotent
PASS: canceled remote subscription revokes premium
PASS: valid but stale signed event cannot reactivate premium
SEC05-FC06A: REAL SDK SIGNATURE PASS
PASS: FC06A test-only records cleaned
PASSED
1 passed, 1 warning in 2.53s
```

- **Cryptographic verification is genuine**: `stripe.Webhook.construct_event` from the installed Stripe SDK checks signatures over a locally crafted payload.
- FastAPI TestClient and real disposable PostgreSQL with schema `0006_subscription_price_guard` exercised.
- Stripe SDK network calls `Subscription.retrieve` and `Customer.retrieve` were **mocked**. The test uses a synthetic `sk_test_` value and random local `whsec_` string. Thus **no real Stripe API call, real checkout, real invoice, or Test Mode transaction has yet been demonstrated**.
- Reported deprecation warning from Starlette TestClient.
- No changes to `main`, original DBs, or original worktree.

## Next acceptance gates

**FC06B** — Stripe TEST MODE account, test-mode recurring product and `price_...`, `sk_test_...` only via local secrets, HTTPS sandbox route and Stripe CLI or Dashboard-delivered signed webhooks. Verify real checkout session, completed checkout, matching subscription and Premium grant. Never print secrets or commit `.env`.

**FC06C** — Define and implement authoritative invoice/payment lifecycle rules and durable invoice ledger; current webhook records `invoice.*` event IDs without reconciling invoice or payment state. Cover `invoice.paid`, `invoice.payment_failed`, `invoice.payment_action_required`, cancellation, unpaid/grace period, refunds and dispute policy.

**FC06D** — Reconcile subscriptions, invoices, payments and internal entitlements with Stripe; retries, failure recovery and audit, proper event-level deduplication. Avoid false financial "paid" declarations.

**FC06E** — Full backend regression, frontend build, API contract against real isolated PG, security review, immutable migrations, secret hygiene and launch readiness.

Only branch `test/sec05-stripe-prebeta` and the disposable `jobagent-sec05-db` PG with port 55434 and volume `jobagent-sec05-pgdata`; no touching original PostgreSQL instances, `main`, or PR #2.
