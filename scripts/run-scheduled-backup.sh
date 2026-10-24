#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONF="$HOME/.config/jobagent/backup.env"
[ -f "$CONF" ] || { echo "Falta $CONF" >&2; exit 1; }
set -a
source "$CONF"
set +a
[ -n "${JOBAGENT_BACKUP_REMOTE:-}" ] || { echo "Remote nao configurado" >&2; exit 1; }
mkdir -p "$ROOT/db-recovery"
exec 9>"$ROOT/db-recovery/backup.lock"
flock -n 9 || { echo "Backup ja em andamento"; exit 0; }
bash "$ROOT/scripts/backup-postgres.sh"
