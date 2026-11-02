# Checkpoint D2-E2.D.1-D — Transactional and Chromium acceptance

**Date:** 2026-11-02 (Brazil).  
**Technical PASS commit:** `c9f99f681e82c042bd60e0de8c1e84c2ae95e2b5`.  
**PR:** https://github.com/Arthur-Levi/Job-Agent/pull/10 (DRAFT, unmerged; base PR #9).  
**Successful CI:** https://github.com/Arthur-Levi/Job-Agent/actions/runs/41447864092  
**Disposition:** **PASS CONDITIONAL** for synthetic test coverage. **NO-GO** for real resumes, beta and deployment.

## Verified in CI

- Backend: **301 passed, 3 xfailed, 1 warning** with disposable GitHub Actions PostgreSQL (`job_agent_test`).
- Frontend: **SUCCESS** lint/build/Vitest.
- Sandbox smoke: **SUCCESS** with synthetic-only container probe (not production certification).
- Audit job: **SUCCESS** but is configured `continue-on-error: true` (non-blocking advisory).
- New `browser-smoke`: **SUCCESS**, running Chromium on Ubuntu 24.04 with Playwright 1.56 and synthetic intercepted HTTP responses. Browser log: `D2-E2.D.1-D Chromium browser journey PASS (mock HTTP)`.
- Ruff, formatting, MyPy and migration round-trip on CI's disposable database passed.

## New acceptance cases

### PostgreSQL transactional suite
File: `backend/tests/integration/test_d2e2d1_d_transactional.py`

1. `test_import_survives_new_database_session`: a committed receipt, fact and Master Profile survive closing and reopening the SQLAlchemy session.
2. `test_failed_fact_insert_rolls_back_receipt_and_profile`: injected failure in fact insert rolls back import receipt, profile and ledger facts; verified from a separate session.
3. `test_correction_racing_reimport_never_resurrects_superseded_fact`: concurrent correction and reimport on independent sessions leave exactly one active revision, one superseded fact and no resurrection; both legal orderings accepted.

Committed synthetic fixtures are explicitly cleaned up; no customer data is used. Integration fixture can recreate `public` schema: **NEVER run against preserved database**, even if its name ends in `_test`.

### React UI correction
`frontend/src/pages/CareerPage.tsx`: the correction field now displays the structured fact's **description**, rather than the JSON string representing title, description, company and dates. Legacy plain-text facts stay editable.

### Chromium real-browser check
File: `scripts/d2e2d1d_browser_smoke.py`; job: `browser-smoke` in `.github/workflows/ci.yml`.

Uses a **real Chromium UI with mocked HTTP only**. Verifies access redirect, login, synthetic TXT upload, ATS preview, editing and rejecting an item, explicit human confirmation, Fact Ledger display, correction of description, superseded history and re-login after page refresh (bearer token is intentionally memory-only). Mock state persists within the Python test process. **This is not a real browser-to-PostgreSQL end-to-end test.** CI's backend verifies PostgreSQL separately.

## What is NOT approved yet

- Full browser-to-real-API-to-PostgreSQL journey using an isolated ephemeral environment.
- Tests of same-key simultaneous confirmation, multiple simultaneous corrections, cross-user concurrency and full recovery from DB/worker outage.
- Full structured corrections (role, institution, category, date ranges) and durable provenance contract for downstream consumers.
- Production broker socket permissions, independently limited runtime identity, distributed quotas, worker supervision, secure PII retention and deletion.
- The production preview upload gate must remain **503 `CV_SANDBOX_REQUIRED`**; not changed here.
- No merge to `main`, no deployments, no migrations in persisted Codespaces DB, no charging and no real resumes.

## Safe next steps

1. Test real browser + authenticated real backend + disposable PostgreSQL through an independent staging runner (no preserved data).
2. Extend concurrency to same-key simultaneous confirmation and competing corrections; assert consistent user isolation and facts history.
3. Finish structured edit API/UI and regression coverage.
4. Reconcile all D2-E2.D.1-C operational sandbox gates, LGPD obligations and safety approval before any external beta.
5. Then D2-E2.E (career diagnostic / ATS), D2-E2.F (CV tailoring / explainable job matching), and controlled beta acceptance.

## Recover the work

```bash
cd /workspaces/Job-Agent-D2-E2D-AUDIT
git status --short
git fetch origin
git worktree add --detach /workspaces/Job-Agent-D2-E2D1-D origin/audit/d2-e2d1-d-acceptance
cd /workspaces/Job-Agent-D2-E2D1-D
git log -1 --oneline
git status --short
```

If worktree already exists, use `cd /workspaces/Job-Agent-D2-E2D1-D`, check status and `git fetch origin`; do not overwrite local modifications. Use disposable PostgreSQL in CI only, and preserve the previous checkpoint branch.
