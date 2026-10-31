# D2-E1.5.1 — Verifiable identity and password recovery

**Status: IMPLEMENTATION + CI PASS, isolated operational acceptance PENDING.** Not authorized for real-user launch.
Branch `feature/d2-e1-react-auth-ui`; PR #3 remains draft.

## Architecture

- Alembic revision `0004` adds nullable `users.email_verified_at` and `auth_action_tokens` (SHA-256 token digest primary key, user ID, purpose, expiration, consumption timestamp). Adds FK and cleanup indexes. Existing users are NOT auto-verified, and existing account data is not removed.
- Raw random 48-byte-entropy-equivalent URL-safe tokens are never stored in SQL or in application logs. The disposable test mailer receives the token as a URL fragment; links do not use query parameters, reducing server-side token leakage.
- Verification token TTL: 1 hour. Password reset token TTL: 20 minutes. Old unconsumed tokens for the same purpose become invalid when replacements are issued.
- Redemption acquires a PostgreSQL user row lock, verifies purpose/expiration/reuse, then consumes the token. Password reset writes a new Argon2 password hash and revokes *all* existing bearer sessions in the same database transaction.
- With `IDENTITY_LIFECYCLE_ENABLED=true`, login is rejected with the same generic 401 until email verification is complete; no account-existence signal is returned.
- Endpoints: `POST /api/v1/auth/request-verification`, `/verify-email`, `/request-password-reset`, `/reset-password`. Request endpoints return generic HTTP 202 for unknown/ineligible identities, no outbound action for nonexistent addresses. Action endpoints return 204 or generic invalid/expired 400.
- All lifecycle POSTs share the PostgreSQL-backed per-IP middleware throttling; account requests also have per-email HMAC counter limits when `AUTH_RATE_LIMIT_ENABLED=true`.
- React routes: `/request-verification`, `/verify-email`, `/request-password-reset`, `/reset-password`. Form tokens are submitted in POST bodies and fragments are stripped from browser history after mounting.

## Test-only transport and production safety

The provider `MemoryMailer` stores synthetic outbox messages in application memory exclusively; it does not send real mail. Tests use `APP_ENV=test`, `IDENTITY_LIFECYCLE_ENABLED=true`, `EMAIL_DELIVERY_MODE=memory`, optional privacy and disposable test PostgreSQL.

**Production refuses `EMAIL_DELIVERY_MODE=memory`.** The feature cannot be turned on in production with the current provider set: `EMAIL_DELIVERY_MODE=disabled` also fails validation when the lifecycle feature is enabled. This is deliberate fail-closed behavior until a real transactional email provider is implemented and tested. Legacy production-config tests can still create an app with the feature disabled, but **this is NOT a public-launch authorization**. Implement and verify a real mail transport before enabling public registration.

Email verification and recovery do not substitute for TLS, monitoring, trusted-proxy checks, SPF/DKIM/DMARC, verified sender domains, limits against mass mail sending, incident response, and support recovery procedures.

## Test evidence

GitHub CI run `41243109554` for commit `39313d2`:
- Backend Ruff lint + format PASS, strict MyPy PASS (100 files), migrations including `0004` upgrade/downgrade PASS, **235 passed / 1 warning** on isolated CI PostgreSQL.
- Frontend lint/build/tests PASS (existing 83 passing test set).
- Audit job PASS (workflow audit is informational).
- Acceptance `test_d2e151_identity_lifecycle.py` verifies unverified login rejection, verification/replay, reset token replay, multiple-session revocation, old/new password behavior, expired tokens, and generic responses for unknown addresses.
- Later commits add React recovery routing assertions; see latest CI before considering them accepted.

## Codespaces safety gate (not yet executed)

The user has the disposable DB `jobagent_react_test` in container `jobagent-react-test-db` on `127.0.0.1:55435`, previously at Alembic `0003`. **Do not use the shared test fixture on this DB**: it runs `DROP SCHEMA public CASCADE`. No Code Mode operation has upgraded the user's DB to `0004`, started an email server, or touched SEC05, production, PR #2 or main.

To conduct operational acceptance later:
1. Confirm exact Docker container name/port, SQL-connected database/user, and current Alembic revision.
2. Stop only the verified isolated API and preserve synthetic data.
3. Apply **only** additive migration `0003 → 0004` with an explicit disposable acknowledgement. Never reset schema or downgrade.
4. Start isolated API with test-only memory transport, confirm its actual DB binding, then test verification/reset and session revocation with fresh synthetic accounts, without extracting real user data.
5. Record operational PASS evidence; enable real delivery only in a separately approved staging environment.

## Release blockers

- Verified transactional SMTP/API email provider, tested retries and failure semantics; no message links in logs.
- Existing user migration policy (do not silently mark all old emails verified).
- Production deploy with HTTPS, trusted proxy, account abuse observation and privacy compliance.
- Dedicated review of concurrency, time/side-channel differences, and token lifecycle under multiple workers.
- PR #3 remains draft; DO NOT declare `D2-E1 COMPLETE` or publicly launch.

## Latest complete GitHub Actions regression — PASS

Run **41243282845**, with all three jobs concluded successfully:

- Backend: Ruff lint/format PASS (105 files formatted), MyPy PASS (100 source files), Alembic upgrade/downgrade cycle including revision `0004` PASS, pytest **235 passed / 1 warning**.
- Frontend: ESLint PASS, Vite production build PASS, Vitest **85 passed / 5 live tests skipped**. The additional tests exercise the generic recovery request UX and absence of a verification link token.
- Audit job: PASS (the audit remains informational and not a security certification).

Accepted: `D2-E1.5.1 IMPLEMENTATION + CI PASS`. Codespaces `0004` migration, real email transport and delivery, and public deployment remain unapproved/pending. GitHub PR #3 stays Draft.

https://github.com/Arthur-Levi/Job-Agent/actions/runs/41243282845

## Operational checkpoint — Codespaces migration 0004 PASS, lifecycle probe pending

Operator reported on 2026-10-31:

```text
GUARDED TARGET: jobagent_react_test / react_test / 127.0.0.1:55435 / 0003
VERIFIED ISOLATED API STOP PASS: 140573
Port 18081 listening: False
GUARDED TARGET: jobagent_react_test / react_test / 127.0.0.1:55435 / 0004
D2-E1.5.1 MIGRATION 0004 PASS: additive upgrade, disposable DB only
Port 18081 listening: False
```

**Migration operational acceptance: PASS**, with exact database identity verified and the old isolated FastAPI process stopped. No other DB was in scope, and migration is already applied; do **not** re-run.

The guarded `scripts/d2e151_operational_probe.py` now provides an end-to-end FastAPI ASGI + real PostgreSQL exercise, **without launching a web listener or using destructive integration fixtures**. It requires `0004`, confirms the exact disposable Docker database, refuses if the old API is listening, creates random synthetic credentials, uses the in-memory outbox, asserts account verification, token replay and expiry, generic recovery, multi-session revocation and new/old password behavior, and uses an **outer SQL transaction with unconditional rollback**. An independent SQL read verifies zero synthetic test accounts persisted.

Run only after the branch has the probe and its CLI compile check passes:

```bash
cd /workspaces/Job-Agent-D2-E1-UI
git status --short --branch
git fetch origin feature/d2-e1-react-auth-ui
git merge --ff-only origin/feature/d2-e1-react-auth-ui
PY=/workspaces/Job-Agent-SEC05/backend/.venv/bin/python
"$PY" scripts/d2e151_migration_gate.py inspect
"$PY" scripts/d2e151_operational_probe.py --ack PROBE_ONLY_jobagent_react_test_REV0004
```

Expected acceptance marker: `D2-E1.5.1 OPERATIONAL IDENTITY LIFECYCLE PASS`. Do not claim it until the operator provides the actual output. This ASGI test does not prove external SMTP delivery, HTTPS or an actual Uvicorn network deployment.

## D2-E1.5.1 OPERATIONAL IDENTITY LIFECYCLE PASS (operator) — 2026-10-31

The operator executed the guarded ASGI + real PostgreSQL probe on Codespaces against the explicitly verified disposable target `jobagent_react_test`, user `react_test`, loopback `127.0.0.1:55435`, with Alembic revision `0004`. The isolated API listener on port 18081 had previously been stopped safely; the probe did not restart it.

Operator-provided evidence:

```text
GUARDED TARGET: jobagent_react_test / react_test / 127.0.0.1:55435 / 0004
REGISTER / HASHED OUTBOX TOKEN PASS
UNVERIFIED LOGIN / ONE-USE VERIFICATION PASS
GENERIC ACCOUNT RECOVERY / TWO SESSIONS PASS
RESET REPLAY / TWO SESSION REVOCATIONS / NEW PASSWORD PASS
EXPIRED TOKEN / INELIGIBLE VERIFICATION PASS
ROLLBACK VERIFIED: zero synthetic test accounts persisted
D2-E1.5.1 OPERATIONAL IDENTITY LIFECYCLE PASS
```

**Acceptance: PASS for isolated operational identity-lifecycle scenarios** including hashed one-time tokens, email-verification gate, generic recovery, password reset, replay/expiry resistance, revocation of two bearer sessions, and verification that synthetic rows were rolled back. A `StarletteDeprecationWarning` about httpx vs httpx2 was emitted by the test environment; the operator's test completed successfully, but dependency compatibility should be assessed separately.

**Scope limitations:** in-memory fake mail transport only, no real email delivery; single-process ASGI TestClient not an externally exposed Uvicorn reverse-proxy test; no actual production TLS or SMTP. Real delivery, deployment hardening, staging review and public-launch signoff are still PENDING. Do not mark PR #3 ready for merge solely from this result. The main branch, PR #2 and preserved DBs were not part of this probe.
