#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${DATABASE_URL:?DATABASE_URL required}"
if [[ "$DATABASE_URL" != postgresql+psycopg://* ]]; then
  echo 'RELEASE BLOCKED: production gate requires real PostgreSQL' >&2
  exit 2
fi
if [[ "${APP_ENV:-}" == production ]]; then
  echo 'RELEASE BLOCKED: run gate on a disposable staging database, never production' >&2
  exit 2
fi
if [[ "${ALLOW_TEST_SQLITE:-}" == 1 ]]; then
  echo 'RELEASE BLOCKED: ALLOW_TEST_SQLITE must be unset' >&2
  exit 2
fi
python - <<'PY'
import psycopg
print('PostgreSQL driver:',psycopg.__version__)
PY
alembic upgrade head
alembic current
python - <<'PY'
from main import engine
from models import Base
from sqlalchemy import inspect,text
with engine.connect() as conn:
    version=conn.execute(text('SELECT version()')).scalar()
    assert 'PostgreSQL' in version,version
    actual=set(inspect(conn).get_table_names())
    missing=set(Base.metadata.tables)-actual
    assert not missing, f'Missing migrated tables: {missing}'
    print('POSTGRES_SCHEMA_PASS:',len(Base.metadata.tables),'model tables')
PY
pytest -q tests
printf '\nPostgreSQL migrations, schema and API regression tests passed.\n'
printf 'Browser E2E must be run separately on an environment allowing Chromium HTTP navigation.\n'
