# D2-E1 — Red-first acceptance test checkpoint (2026-10-31)

Branch: `test/sec05-stripe-prebeta`

## Status
- Ten synthetic persona dataset: **5/5 PASS** in latest operator execution.
- `backend/tests/acceptance/test_d2e1_identity_red.py`: **auth and multi-tenancy acceptance tests AUTHORED, NOT YET EXECUTED**.
- E1 implementation: **NOT COMPLETE / NOT APPROVED**.
- Existing `backend/app/api/deps.py` currently chooses D1 default local user, so unauthenticated requests are permitted; auth endpoints required in tests do not exist yet. Expected-red tests are intentionally designed to expose this.
- Prior separate regression evidence preserved: 72 + 68 + 110 + 98 + 5 = 353 passing tests; plus 5 fixture quality tests = 358 distinct passing test invocations across different scopes.

## New acceptance scenarios
1. Unauthenticated access to /api/v1/profile, jobs and applications MUST return 401 and cannot silently create a default user.
2. Register/login/me for all 10 distinct identities, unique owner IDs, separate profiles.
3. Cross-tenant jobs: each of 10 accounts sees only their own job; 90 directed foreign job reads return 404.
4. Logout revokes only one session, not another account's session.

Tests are criteria, not product functionality. They are currently RED by design until a migration-backed authentication service, route family, and frontend authorization are implemented.

## Safety
The integration fixture used by `api_client` performs `DROP SCHEMA public CASCADE` in TEST_DATABASE_URL. Running these tests MUST be limited to the already verified, dedicated, expendable `jobagent-react-test-db` / `jobagent_react_test` (port 55435). NEVER run them against original, financial SEC05, or shared databases. A deliberate choice may be to run only the no-DB corpus tests while auth implementation is pending.
No secret values or real user data committed. No merges to main or PR #2.
Stripe FC06B–D paused.

## Required work before PASS
- Design session/password tables and Alembic migration preserving existing React schema and no hidden mixing with production_api tables.
- Implement argon2 hashed passwords or equivalent vetted password hashing, securely random token only hash stored, TTL/logout and brute-force rate limiter, validation.
- Implement /api/v1/auth/register, login, logout, me with correct per-user identity.
- Disable default user on all public/non-test endpoints and revise tests that relied on D1 identity using isolated test overrides.
- Adapt React frontend to send and revoke authorized credentials, and verify CORS and error handling.
- Run migrations/black-box test suite on guarded dedicated React DB and maintain prior 110+98+5 regression results.
- Only then mark E1 PASS. E2–E6 remain pending.

## Synchronization
```bash
cd /workspaces/Job-Agent-SEC05
git fetch origin test/sec05-stripe-prebeta
git merge --ff-only origin/test/sec05-stripe-prebeta
```

## Next developer task
Implement identity schema and auth routes in the existing `backend/app` using the explicit red-first tests as acceptance criteria. Do not attempt to satisfy tests by enabling default identity for every request.
