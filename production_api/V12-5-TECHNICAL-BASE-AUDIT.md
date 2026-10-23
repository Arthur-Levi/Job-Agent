# Job Agent v12.5 — Technical base audit (2026-10-22)

## Scope
This build is derived from v12.4, preserving the application and migrations. It adds authorization regression tests, a Chromium offline DOM experiment, and a strict PostgreSQL staging release gate. It does not claim a production deployment or a successful PostgreSQL runtime test.

## Verified in this environment
- `pytest -q tests`: **66 passed, 1 warning** using disposable SQLite. Four newly added checks cover cross-tenant Master Profile source references, cross-tenant job/fact references, logout token revocation and HTTP security headers.
- `alembic upgrade head` against a **fresh SQLite database**: reaches `0005_master_profile_fact_ledger`; all **17** application model tables are present.
- Chromium successfully renders the initial HTML using `page.set_content`: login section visible, 13 navigation buttons present. This is a **static DOM check**, not an authenticated browser E2E.
- The Chromium network E2E attempt failed with `net::ERR_BLOCKED_BY_ADMINISTRATOR` even when requests were intercepted by Playwright. The failure is environmental; the user journey has **not** been validated in-browser.

## Not verified / release blockers
1. Real PostgreSQL runtime: this environment has no PostgreSQL server, Docker or psycopg driver. Network package installation was unavailable. The `run-release-gate.sh` script intentionally refuses SQLite and production DBs.
2. Real browser E2E: run `tests/browser_smoke_v9.py` (and expand to import/confirm/ledger/resume) on CI or staging with HTTP access. `tests/browser_e2e_offline.py` is experimental and cannot bypass this environment's navigation policy.
3. Stripe sandbox checkout, webhook replay, cancellation and customer portal not end-to-end tested.
4. Backups and restore drills, deployment secrets, gateway rate limiting, monitoring, load tests, and independent security review remain open.
5. PDF/DOCX extraction accuracy and diagnosis quality still require representative real-user cases and manual review.

## Recommended next staging procedure
1. Provision a disposable PostgreSQL 16 database with a non-production user and password. Install `production_api/requirements.txt` in a virtual environment.
2. Set `DATABASE_URL=postgresql+psycopg://...` and `APP_ENV=staging`; ensure `ALLOW_TEST_SQLITE` is unset. Run `./run-release-gate.sh`.
3. Launch API behind a staging HTTPS origin; run a Playwright journey: register, login, upload a non-sensitive sample CV, review and confirm, import twice, inspect Master Profile and Fact Ledger, run diagnostic, generate grounded resume, logout and login, confirm persistence. Repeat with a second account and assert isolation.
4. Perform backup and restore, Stripe sandbox, operational monitoring and security tests. Do not accept paying customers until blockers are closed.

## Release decision
**NO-GO** for public paid release; **GO** for waitlist acquisition without collecting sensitive resume data. Controlled beta only after basic privacy, auth and database/browser checks pass.
