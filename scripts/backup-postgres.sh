#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${JOBAGENT_DB_CONTAINER:-jobagent-postgres-v2}"
DEST="${JOBAGENT_BACKUP_DIR:-$ROOT/db-recovery/automatic}"
mkdir -p "$DEST"
chmod 700 "$DEST"
command -v docker >/dev/null
docker info >/dev/null
docker exec "$CONTAINER" pg_isready -U jobagent -d jobagent_test >/dev/null
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$DEST/jobagent-$STAMP.dump"
TMP="$TARGET.partial"
trap 'rm -f "$TMP"' EXIT
echo "Criando backup consistente..."
docker exec -u postgres "$CONTAINER" pg_dump -U jobagent -d jobagent_test \
  --format=custom --no-owner --no-acl > "$TMP"
[ -s "$TMP" ] || { echo "Dump vazio" >&2; exit 1; }
chmod 600 "$TMP"
echo "Testando restauracao isolada..."
bash "$ROOT/scripts/verify-postgres-backup.sh" "$TMP"
mv "$TMP" "$TARGET"
trap - EXIT
sha256sum "$TARGET" > "$TARGET.sha256"
chmod 600 "$TARGET.sha256"
echo "BACKUP PASS: $TARGET"
if [ -n "${JOBAGENT_BACKUP_REMOTE:-}" ]; then
  command -v rclone >/dev/null || { echo "rclone nao instalado; backup local salvo, copia remota falhou" >&2; exit 1; }
  rclone copyto "$TARGET" "${JOBAGENT_BACKUP_REMOTE%/}/$(basename "$TARGET")"
  rclone copyto "$TARGET.sha256" "${JOBAGENT_BACKUP_REMOTE%/}/$(basename "$TARGET.sha256")"
  echo "COPIA REMOTA PASS"
else
  echo "AVISO: sem JOBAGENT_BACKUP_REMOTE, backup somente local; nao protege contra exclusao do Codespaces."
fi
