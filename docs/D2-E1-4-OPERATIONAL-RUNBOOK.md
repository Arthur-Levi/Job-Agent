# D2-E1.4 — Operational 429 and recovery (guarded, not yet operator-executed)

**Current checkpoint:** operational script implemented; Codespaces execution and PASS evidence pending. GitHub CI previously accepted 229 backend tests + 83 frontend tests.

## Strict scope

Only the already identified disposable database:
- Docker container: `jobagent-react-test-db`
- Database: `jobagent_react_test`; user: `react_test`
- PostgreSQL host: `127.0.0.1:55435`
- API: `127.0.0.1:18081`
- Worktree: `/workspaces/Job-Agent-D2-E1-UI`
- Version expected before migration: `0002`; after: `0003`

The script `scripts/d2e14_operational_gate.py` obtains the database credentials directly from the verified Docker container without displaying them, verifies the SQL-connected database identity, and refuses unexpected destinations or revisions. It does NOT reset/drop schema and does NOT use the destructive `pytest` integration fixtures. Existing browser-generated synthetic accounts and jobs are preserved by the additive migration.

**Never use the script on SEC05 port 55434, original Postgres port 5432, or on a shared/production DB.**

## Runbook

First fast-forward the independent worktree:
```bash
cd /workspaces/Job-Agent-D2-E1-UI
git status --short --branch
git fetch origin feature/d2-e1-react-auth-ui
git merge --ff-only origin/feature/d2-e1-react-auth-ui
```

Run with the backend Python venv that already has SQLAlchemy, Alembic, psycopg and Uvicorn installed:
```bash
PY=/workspaces/Job-Agent-SEC05/backend/.venv/bin/python
"$PY" scripts/d2e14_operational_gate.py inspect
```
Require output: `TARGET VERIFIED: jobagent_react_test / react_test / 127.0.0.1:55435 / alembic=0002` (or `0003` on a previously migrated disposable DB).

The old D2-E1 API on port 18081 must be stopped before migration. This command checks its own PID file, the actual process command/cwd, and its environment's database host/user/name/port before sending SIGTERM. If the process is different, it refuses to stop it:
```bash
"$PY" scripts/d2e14_operational_gate.py stop-previous-api
```

Explicit, additive migration with a hard-coded disposable database acknowledgement:
```bash
"$PY" scripts/d2e14_operational_gate.py migrate --ack MIGRATE_ONLY_jobagent_react_test
```
Require: `MIGRATION 0003 PASS` and a repeat `inspect` showing `alembic=0003`.

Start an **independent non-proxy-aware** FastAPI process on loopback:
```bash
"$PY" scripts/d2e14_operational_gate.py start
```
This starts Uvicorn `--no-proxy-headers` with `APP_ENV=test`, legacy local identity disabled, a randomly generated HMAC key, registration max 2 per 60s, login max 8 per IP per 60s, and login max 2 per account per 60s. All settings are verified via its actual process environment without printing secrets. PID and logs live in `/tmp/jobagent-d2e14-security-api.*`.

Run HTTP acceptance (this writes only HMAC counters to the disposable DB; registration payloads are deliberately invalid and login uses nonexistent synthetic emails):
```bash
"$PY" scripts/d2e14_operational_gate.py probe
```

The test asserts:
1. Two invalid registration bodies return 422 with differing forged X-Forwarded-For; third attempt is blocked with 429 and positive Retry-After.
2. Two bad logins to one random synthetic email return 401; third (email uppercase variant) returns 429 with positive Retry-After.
3. A different random email remains eligible and returns 401, not 429.
4. The script **actually waits** for the longest Retry-After plus 2 seconds (maximum 62 seconds under the 60-second window).
5. Registration recovers to 422 and login recovers to 401 after the window, proving 429 is temporary.

A successful run ends with `D2-E1.4 LIVE RATE-LIMIT OPERATIONAL PASS`.

This proves loopback direct-peer behavior, **not** safe trusted reverse-proxy operation. A separate production ingress / proxy trust test remains mandatory before public exposure.

## Important interpretation

- `429` on the account limit uses generic HTTP exception code `HTTP_429`, while the middleware IP limit uses `RATE_LIMITED`; both preserve the same standard error envelope and a valid Retry-After.
- The script uses no real credentials, creates no real users, and does not alter existing schemas except the additive `0003` table and index.
- No `DROP SCHEMA`, `alembic downgrade`, `docker compose down -v`, or production migration is authorized.
- A successful CI run alone does **not** claim Codespaces operational PASS. Wait for operator output.

## Operational harness CI check (2026-10-31)

GitHub Actions run **41239950616**: backend PASS, frontend PASS, audit PASS. Backend pipeline included `python -m py_compile ../scripts/d2e14_operational_gate.py` and CLI `--help`, then Ruff, format, MyPy, migration cycle against disposable CI Postgres and pytest. This validates the harness can import/compile but **does not execute** its Docker guard, migration or real-time 429 recovery against Codespaces. Operational acceptance remains **PENDING** until operator logs are supplied.

https://github.com/Arthur-Levi/Job-Agent/actions/runs/41239950616
