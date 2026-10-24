#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${JOBAGENT_BACKUP_REMOTE:-jobagent-crypt:}"
NAME="${1:?Uso: bash scripts/verify-remote-backup.sh jobagent-AAAAMMDDTHHMMSSZ.dump}"
[[ "$NAME" =~ ^jobagent-[0-9]{8}T[0-9]{6}Z\.dump$ ]] || { echo "Nome de backup invalido" >&2; exit 1; }
command -v rclone >/dev/null
TYPE="$(rclone config show "${REMOTE%%:*}" | sed -n 's/^[[:space:]]*type[[:space:]]*=[[:space:]]*//p' | head -1)"
[ "$TYPE" = crypt ] || { echo "Destino nao e um remote crypt. Recusando acesso." >&2; exit 1; }
TMP="$(mktemp -d)"
chmod 700 "$TMP"
trap 'rm -rf "$TMP"' EXIT
echo "Baixando backup criptografado do Google Drive..."
rclone copyto "${REMOTE%/}/$NAME" "$TMP/$NAME"
rclone copyto "${REMOTE%/}/$NAME.sha256" "$TMP/$NAME.sha256"
(cd "$TMP" && sha256sum -c "$NAME.sha256")
echo "Restaurando copia obtida do Google Drive em banco isolado..."
bash "$ROOT/scripts/verify-postgres-backup.sh" "$TMP/$NAME"
echo "REMOTE RESTORE PASS: $NAME"
