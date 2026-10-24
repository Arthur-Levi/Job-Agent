#!/usr/bin/env bash
set -Eeuo pipefail
FILE="${1:?Uso: bash scripts/verify-postgres-backup.sh arquivo.dump}"
[ -s "$FILE" ] || { echo "Backup inexistente ou vazio" >&2; exit 1; }
command -v docker >/dev/null
docker info >/dev/null
FILE="$(realpath "$FILE")"
docker run --rm --entrypoint pg_restore -v "$FILE:/backup.dump:ro" postgres:16-alpine --list /backup.dump >/dev/null
NAME="jobagent-restore-test-$$"
cleanup(){ docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run -d --name "$NAME" --network none --tmpfs /var/lib/postgresql/data:rw,size=512m \
  -e POSTGRES_PASSWORD=temporary_restore_test_only -e POSTGRES_DB=jobagent_test postgres:16-alpine >/dev/null
ready=0
for i in $(seq 1 60); do
  if docker exec "$NAME" pg_isready -U postgres -d jobagent_test >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[ "$ready" = 1 ] || { docker logs "$NAME" >&2; exit 1; }
docker cp "$FILE" "$NAME:/tmp/backup.dump" >/dev/null
docker exec -u postgres "$NAME" pg_restore --exit-on-error --no-owner --no-acl \
  -U postgres -d jobagent_test /tmp/backup.dump
TABLES="$(docker exec -u postgres "$NAME" psql -U postgres -d jobagent_test -Atqc \
  "SELECT count(*) FROM pg_class WHERE relkind IN ('r','p') AND relnamespace NOT IN (SELECT oid FROM pg_namespace WHERE nspname LIKE 'pg_%' OR nspname='information_schema');")"
[ "$TABLES" -gt 0 ] || { echo "Restauracao sem tabelas de usuario" >&2; exit 1; }
echo "RESTORE PASS: backup restaurado em banco isolado; tabelas=$TABLES"
