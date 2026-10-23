#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?Set DATABASE_URL to a disposable PostgreSQL database}"
case "$DATABASE_URL" in postgresql+psycopg://*) ;; *) echo 'Use postgresql+psycopg:// (PostgreSQL real)' >&2; exit 2;; esac
export APP_ENV=test
alembic upgrade head
python - <<'PY'
from sqlalchemy import create_engine, text
import os
engine=create_engine(os.environ['DATABASE_URL'],pool_pre_ping=True)
with engine.connect() as c:
    version=c.execute(text('select version()')).scalar()
    tables=c.execute(text("select tablename from pg_tables where schemaname='public' and tablename in ('career_facts','master_profile_items','evidence','users')")).scalars().all()
    print('PostgreSQL:',version)
    print('Required tables:',tables)
    assert len(tables)==4, 'Missing required tables'
print('Migration/schema smoke check PASS')
PY
pytest -q tests/test_v124.py tests/test_master_ledger_v123.py
