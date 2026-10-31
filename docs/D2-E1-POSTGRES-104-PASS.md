# D2-E1 — PostgreSQL multiuser acceptance PASS (104/104)

**Date:** 2026-10-31  
**Branch:** `test/sec05-stripe-prebeta`  
**Evidence:** Operator-submitted output from guarded disposable PostgreSQL test execution.

## Verified by operator run

```text
104 passed, 1 warning in 15.06s
D2-E1: DATABASE ACCEPTANCE PASS
```

The test command executed `tests/integration` together with `tests/acceptance/test_d2e1_identity_red.py` after a safety guard checked the dedicated disposable React PostgreSQL container `jobagent-react-test-db`, volume `jobagent-react-test-pgdata`, localhost port 55435, database `jobagent_react_test` and user `react_test`. The suite's fixture recreates the `public` schema **only within the disposable test database**.

## Accepted scope
- Migration chain to Alembic revision `0002` applied through the migration-based integration fixtures.
- Ten synthetic account registration, login and distinct owner/profile checks.
- Ninety ordered cross-account foreign job lookups asserted to return 404; ownership-scoped job lists.
- Anonymous requests rejected; duplicate registrations and bad credentials rejected.
- Session logout and expired token rejection; another account's session remains valid.
- Existing backend PostgreSQL integration suite remains passing in the same run.
- Separate synthetic corpus tests were previously **6/6 PASS**; earlier unit/API regression was operator-confirmed passing after correction.
- **104** passed here; this is a combined test-run count, not proof of 104 distinct human scenarios.

## Still open: E1 full product/UI gate
1. React login/register/logout/me and bearer header transport with session lifecycle, logout cleanup, error handling and refresh/re-login usability.
2. Re-run five `frontend/src/services/contract.live.test.ts` live contract cases against authenticated accounts; prior D1 shared-user contract PASS no longer stands as strict-auth compatibility evidence.
3. Brute-force/rate limiting protection, email enumeration-resistant responses and credential/account lifecycle hardening before any public exposure.
4. Repeat full regression after any change and save evidence, test real browser flows and assess security.
5. E2 upload/review; E3 Master Profile + Fact Ledger; E4 grounded diagnostic; E5 grounded resume; E6 complete React journey are not yet integrated in the canonical React backend.

## Security and isolation
Do not expose the auth endpoints publicly without brute-force controls. No changes to `main`, PR #2, original worktree/DBs or the SEC05 billing DB. Credentials were not logged or committed. Stripe FC06B-D remains deferred.

**Checkpoint status:** `D2-E1 DATABASE ACCEPTANCE PASS`; `D2-E1 COMPLETE` **not** claimed.
