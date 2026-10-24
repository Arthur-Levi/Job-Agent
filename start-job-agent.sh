#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API="$ROOT/production_api"
DB_CONTAINER="jobagent-postgres-v2"
DB_VOLUME="jobagent-postgres-recovered"
fail(){ echo "ERRO: $*" >&2; exit 1; }
command -v docker >/dev/null || fail "Docker nao encontrado"
docker info >/dev/null 2>&1 || fail "Docker daemon indisponivel"
docker volume inspect "$DB_VOLUME" >/dev/null 2>&1 || fail "Volume $DB_VOLUME ausente. Nao criarei um banco vazio."
[ -x "$API/.venv/bin/python" ] || fail "Ambiente Python ausente em $API/.venv"
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi
[ -n "${DATABASE_URL:-}" ] || fail "Configure DATABASE_URL em $ROOT/.env (arquivo ignorado pelo Git)."
export DATABASE_URL
unset ALLOW_TEST_SQLITE
if ! docker container inspect "$DB_CONTAINER" >/dev/null 2>&1; then
  echo "Criando container PostgreSQL com volume existente..."
  docker run -d --name "$DB_CONTAINER" --restart unless-stopped \
    -p 127.0.0.1:5432:5432 \
    -v "$DB_VOLUME:/var/lib/postgresql/data" \
    postgres:16-alpine >/dev/null || fail "Falha ao criar container PostgreSQL"
fi
if [ "$(docker inspect -f '{{.State.Running}}' "$DB_CONTAINER")" != "true" ]; then
  docker start "$DB_CONTAINER" >/dev/null || fail "Falha ao iniciar PostgreSQL. Veja docker logs $DB_CONTAINER"
fi
echo "Aguardando PostgreSQL..."
ready=0
for i in $(seq 1 45); do
  if docker exec "$DB_CONTAINER" pg_isready -U jobagent -d jobagent_test >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[ "$ready" = 1 ] || fail "PostgreSQL nao ficou pronto. Veja docker logs $DB_CONTAINER"
cd "$API"
echo "PostgreSQL pronto. Iniciando Job Agent na porta 8001..."
exec "$API/.venv/bin/python" -m uvicorn main:app --host 0.0.0.0 --port 8001
