# Job Agent — Production API v2 (candidate, not certified)

A separate production-oriented API, NOT an in-place upgrade of D2.1 or the SQLite beta. Includes PostgreSQL ORM, Alembic, Argon2, user-scoped resources, evidence-led diagnostic, Stripe Checkout/portal/webhooks, health probes, audit events and Docker Compose.

## Start locally

1. `cp .env.example .env` and set a random PostgreSQL password; never commit secrets.
2. `docker compose -f docker-compose.production.yml --env-file .env up -d --build`
3. Apply schema: `docker compose -f docker-compose.production.yml --env-file .env run --rm api alembic upgrade head`
4. API health: `curl http://127.0.0.1:8000/health/ready`
5. Local OpenAPI is disabled when `APP_ENV=production`.

## Stripe configuration

- Create a recurring BRL price in your Stripe account and set `STRIPE_PRICE_ID`.
- Set `STRIPE_SECRET_KEY` from Stripe secrets manager; configure `STRIPE_WEBHOOK_SECRET` from a real endpoint on `https://YOUR_HOST/api/billing/webhook`.
- Subscribe to `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`.
- In Stripe Customer Portal configure cancellation, payment methods and invoices.
- `POST /api/billing/checkout` and `POST /api/billing/portal` require `Authorization: Bearer <token>`; return URLs to navigate to.
- **Never grant premium based on a checkout redirect.** Only signed subscription events update entitlements.
- Test failed payments, event retries, out-of-order events and cancellation with Stripe test mode before live mode.

## Critical production caveats

- A production reverse proxy with TLS, shared distributed rate limiting, WAF and security monitoring is REQUIRED; app-level rate limiting is only local to a process.
- Run Alembic as a one-off job before deploying new code, not on every replica startup.
- Configure database backup, point-in-time recovery, restoration drills and alerting outside this package.
- This service currently exposes a JSON API; the older HTML beta does not yet integrate with this API. Integration/migration of the D2.1 frontend and legacy beta data remains open.
- Stripe live credentials and public endpoint are not configured in this archive. No real payment was charged.
- Diagnostic evidence is DECLARED, not verified. Keyword matching is NOT skill verification or a hiring probability.
- Security audit, pentest, LGPD review, webhook reconciliation and end-to-end PostgreSQL deployment verification remain required before paid launch.
- Set retention, data export/deletion, consent and support processes before processing real candidate records at scale.

## Routes

`/api/auth/{register,login,logout}`, `/api/me`, `/api/profile`, `/api/evidence`, `/api/diagnostic`, `/api/jobs`, `/api/jobs/{id}/match`, `/api/resume`, `/api/jobs/{id}/interview`, `/api/applications`, `/api/tasks`, `/api/dashboard`, `/api/billing/{status,checkout,portal,webhook}`, `/health/{live,ready}`.

## Tests

`ALLOW_TEST_SQLITE=1 DATABASE_URL=sqlite:///./test.sqlite3 pytest -q` for isolated API logic tests. This does **not** substitute for PostgreSQL contract tests.

## Commercial gate and privacy

`/api/jobs/{id}/match`, `/api/resume`, `/api/jobs/{id}/interview` require active/trialing subscription and return HTTP 402 otherwise. `/api/diagnostic` remains free for registered users. `/api/account/export` exports account data and `/api/account/delete` deletes account after password confirmation (requires subscription cancellation first). The latter is not a substitute for a full LGPD retention and data-subject-request workflow.

## Observability

`/health/live` and `/health/ready` are probes. Structured log fields (method, path, status, latency) are emitted to stdout, without request body/token. Set up external metrics scraping, alerting, tracing, log retention and on-call response. No external monitoring account is connected by this archive.
