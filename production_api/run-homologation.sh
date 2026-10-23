#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo '[1/4] Python compilation'
python -m compileall -q main.py models.py tests alembic
 echo '[2/4] Backend tests'
python -m pytest -q tests
 echo '[3/4] Frontend JS syntax'
if command -v node >/dev/null 2>&1; then node --check web/app.js; else echo 'SKIP: node unavailable'; fi
 echo '[4/4] External environment readiness'
if command -v docker >/dev/null 2>&1; then echo 'Docker available (real stack NOT automatically launched)'; else echo 'BLOCKED: Docker unavailable'; fi
if command -v psql >/dev/null 2>&1; then echo 'psql available (PostgreSQL connectivity NOT automatically verified)'; else echo 'BLOCKED: psql unavailable'; fi
 echo 'See HOMOLOGATION-REPORT.md before commercial launch.'
