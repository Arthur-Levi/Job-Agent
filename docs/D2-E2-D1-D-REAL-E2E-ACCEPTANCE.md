# D2-E2.D.1-D — Real browser to API to disposable PostgreSQL acceptance

Date: 2026-11-02. Technical commit: `04f2230dbe72cf187640cccfe8c98944128709ae`.

Evidence: https://github.com/Arthur-Levi/Job-Agent/actions/runs/41452154277

**Result: TECHNICAL PASS / BETA AND PRODUCTION NO-GO.**

## Evidenced, not inferred

- GitHub Actions jobs `backend`, `frontend`, `browser-smoke`, `sandbox-smoke`, `audit`, and **`real-browser-postgres-e2e`**: success.
- Backend: **302 passed, 3 xfailed, 1 warning**.
- Explicit disposable connection guard checked `CI=true`, `APP_ENV=test`, `E2E_DISPOSABLE_DATABASE=1`, and the exact `127.0.0.1:5432/job_agent_e2e_test` database identity **before** Alembic.
- Runner provisioned a fresh `postgres:16-alpine` service. The application and frontend ran only on localhost. Parser mode was `subprocess` **only for synthetic test data in APP_ENV=test**, not production.
- Chromium interacted with the **real** React frontend and **real** FastAPI endpoints. Register 201, login 200, current user 200, resume preview 200, confirm 201, ledger reads 200, revision 201, history 200, login 200 and persisted read 200. Browser ended with `real browser/API/PostgreSQL PASS (synthetic only)`.
- This is a real-HTTP, real-database test; unlike `browser-smoke`, API responses are NOT mocked.
- `backend/app/main.py` now admits `Idempotency-Key` in CORS preflight. New `test_resume_import_cors.py` guards the actual browser header.

## New guarded files

- `.github/workflows/ci.yml`: `real-browser-postgres-e2e` CI job with standalone ephemeral PostgreSQL.
- `scripts/d2e2d1d_real_e2e.py`: browser integration; immediately refuses execution without all disposable CI gates.
- `backend/tests/unit/test_resume_import_cors.py`: cross-origin confirmation preflight.

## Independent earlier gates

- Concurrent import/correction, injected rollback and reopen-persistence, plus Chromium with mocked HTTP all passed in the D2-E2.D.1-D series.
- Earlier checkpoint: `docs/CHECKPOINT-D2-E2-D1-D-2026-11-02.md`.

## Limitations and mandatory next gates

- **Do not release production CV upload.** `CV_SANDBOX_REQUIRED` remains deliberately active. Production container execution identity, broker isolation, shared admission control, lifecycle/cancellation and hostile-file testing remain unresolved.
- Browser E2E has real authentication and real DB; it does not fully exercise user separation between two browser sessions, all recovery/timeout cases, same-key parallel confirmation, or all category/field revisions. Add them independently.
- Structured role, organization, dates, and category correction contract is still incomplete.
- Ticket stores signed but unencrypted CV source excerpts; enforce retention, secrecy and LGPD commitments before beta.
- `audit` job is advisory and non-blocking; SUCCESS here is not a claim of zero vulnerabilities.
- No real resumes, client records, deployment, charges, persistent DB migrations or merge to `main` authorized.

## Next stage

D2-E2.E: evidence-grounded Career Diagnostic read-only MVP with transparent limitations, reproducible deterministic decisions, user declared provenance, no invented experience, then D2-E2.F CV tailoring/matching and Beta Acceptance only after security gates.

State reference is the branch `audit/d2-e2d1-d-acceptance`. Keep checkpoint branch immutable after creation.
