#!/usr/bin/env bash
# E2.2-D.2 opt-in acceptance. Creates and destroys ONLY its own temporary DB.
# Run: bash backend/scripts/secops_disposable_recovery.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Working tree has tracked changes; inspect before running." >&2
  exit 2
fi

python_cmd="${SECOPS_PYTHON:-$repo_root/.venv-secops/bin/python}"
if [[ ! -x "$python_cmd" ]]; then
  echo "Missing SEC/OPS virtualenv. Create .venv-secops first." >&2
  exit 2
fi

docker info >/dev/null
docker image inspect postgres:16-alpine >/dev/null
cid=""
cleanup() {
  unset SECOPS_DISPOSABLE_DSN SECOPS_DISPOSABLE_ACK
  if [[ -n "$cid" ]]; then
    echo "=== STOPPING OWN DISPOSABLE DATABASE ==="
    docker stop "$cid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

password="$("$python_cmd" -c 'import secrets; print(secrets.token_hex(24))')"
cid="$(docker run -d --rm --pull=never \
  --network=bridge \
  -p 127.0.0.1::5432 \
  --tmpfs /var/lib/postgresql/data:rw,nosuid,nodev,size=256m \
  -e POSTGRES_USER=secops_user \
  -e POSTGRES_PASSWORD="$password" \
  -e POSTGRES_DB=secops_disposable_test \
  postgres:16-alpine)"
binding="$(docker port "$cid" 5432/tcp)"
port="${binding##*:}"
export SECOPS_DISPOSABLE_DSN="postgresql://secops_user:${password}@127.0.0.1:${port}/secops_disposable_test"
export SECOPS_DISPOSABLE_ACK=I_OWN_THIS_DISPOSABLE_DB
unset DATABASE_URL

echo "=== WAIT FOR AUTHENTICATED TCP READINESS ==="
ready=0
for attempt in $(seq 1 60); do
  if "$python_cmd" - <<'PY'
import os
import psycopg
try:
    with psycopg.connect(os.environ["SECOPS_DISPOSABLE_DSN"], connect_timeout=1) as conn:
        conn.execute("SELECT 1")
except psycopg.Error:
    raise SystemExit(1)
PY
  then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  echo "Disposable PostgreSQL did not become ready." >&2
  exit 1
fi
echo "=== APPLY ISOLATED SCHEMA ==="
docker exec -i -e PGPASSWORD="$password" "$cid" \
  psql -h 127.0.0.1 -U secops_user -d secops_disposable_test \
  -v ON_ERROR_STOP=1 < backend/scripts/secops_admission_schema.sql

echo "=== RUN CROSS-INSTANCE AND MULTIPROCESS ACCEPTANCE ==="
cd backend
"$python_cmd" -m pytest \
  tests/integration/test_distributed_admission.py \
  tests/integration/test_distributed_recovery.py \
  tests/integration/test_worker_lease.py -v

echo "=== DISPOSABLE E2.2-D.2 ACCEPTANCE: TESTS FINISHED ==="
