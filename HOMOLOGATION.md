# PostgreSQL homologation gate

**Status: PENDING** — no real PostgreSQL server has been tested in this environment.

1. Import the reviewed v12.5 source archive into this branch without committing secrets or real customer data.
2. Provision a disposable PostgreSQL 16 staging database.
3. Install `production_api/requirements.txt` and set `DATABASE_URL` to `postgresql+psycopg://...` for staging.
4. Run `cd production_api && bash run-release-gate.sh`.
5. Verify Alembic `upgrade head`, model tables, test suite, persistence, account isolation and backup/restore.
6. Run browser E2E separately and verify checkout before paid launch.

Do not merge until checks are recorded with logs and no critical failures.
