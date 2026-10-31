# D2-E1 — PostgreSQL acceptance: 99 PASS / 5 FAIL, email fixture fix
Date: 2026-10-31
Branch: `test/sec05-stripe-prebeta`
Status: FIX COMMITTED; RETEST REQUIRED, not E1 PASS

## Operator evidence
```text
FAILED tests/acceptance/test_d2e1_identity_red.py::test_e1_session_expiry_revokes_access - AssertionError: assert 422 == 201
5 failed, 99 passed, 1 warning in 7.32s
D2-E1: DATABASE ACCEPTANCE NOT APPROVED
```
The full set of five failure tracebacks was not supplied; only the session-expiry failure is directly observed to be an HTTP 422 during registration. This strongly suggests an invalid fixture email address in all registration scenarios, but the retest is needed to confirm.

## Root-cause reproduction
Python `email_validator.validate_email("d2e-p01@example.test", check_deliverability=False)` rejects the reserved special-use `.test` TLD with `EmailSyntaxError`. The FastAPI RegisterIn schema uses Pydantic `EmailStr`, which rejects that fixture before entering the service (HTTP 422).

## Corrective changes
- `backend/tests/acceptance/d2e_personas.json`: all 10 fixture email addresses now end in `@example.com` (reserved for examples but accepted by `EmailStr`).
- `backend/tests/acceptance/test_d2e_persona_corpus.py`: expected domain updated and added `test_all_synthetic_email_addresses_are_accepted_by_registration_schema` to prevent regression.
- Authentication service remains unchanged; do not weaken email validation.
- No real personal data or credentials added.

## Retest instructions
1. Sync branch.
2. `cd backend && .venv/bin/python -m pytest tests/acceptance/test_d2e_persona_corpus.py -q --tb=short` (expect 6 corpus tests).
3. For PostgreSQL tests, **do not simply set TEST_DATABASE_URL from memory**. Re-run the previously used guard that asserts the exact dedicated container `jobagent-react-test-db`, volume `jobagent-react-test-pgdata`, loopback `127.0.0.1:55435`, PostgreSQL user `react_test`, DB `jobagent_react_test` and only then runs pytest with `REQUIRE_TEST_DATABASE=1`. It resets the dedicated test schema.
4. Capture full failure summary if any fail; never label E1 PASS until verified.

## Out of scope
Frontend authentication integration, request rate limiting, multiuser pilot, and E2-E6. No changes to main, original DBs or SEC05 billing DB.
