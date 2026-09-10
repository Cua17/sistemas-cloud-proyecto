#!/usr/bin/env bash
# infra/baas/backup.sh
#
# Respaldo automatico de NubeUltima hacia MinIO (BaaS), con restic:
#   - la base de datos SQLite (telemetria + alertas)
#   - la configuracion del clusterK3s (manifiestos, /etc/rancher)
#   - snapshot de la base de datos interna de K3s
# restic hace copias CIFRADAS, DEDUPLICADAS e INCREMENTALES.
#
# Corre en la Pi (tiene kubectl + acceso a la VM control). Lo dispara un timer systemd.
set -euo pipefail

export RESTIC_REPOSITORY="s3:http://192.168.100.13:9000/nubeultima-backups"
export RESTIC_PASSWORD_FILE=/etc/nubeultima/restic-password
export AWS_ACCESS_KEY_ID_FILE=/etc/nubeultima/minio-access
export AWS_SECRET_ACCESS_KEY_FILE=/etc/nubeultima/minio-secret
export AWS_ACCESS_KEY_ID="$(cat $AWS_ACCESS_KEY_ID_FILE)"
export AWS_SECRET_ACCESS_KEY="$(cat $AWS_SECRET_ACCESS_KEY_FILE)"

STAGING=/var/tmp/nubeultima-backup
REPO=/home/pi/nubeultima
KEY="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i /home/pi/.ssh/id_ed25519"
mkdir -p "$STAGING"

echo "[$(date -u +%FT%TZ)] === respaldo NubeUltima ==="

# 1. Base de datos SQLite (backup consistente con .backup, no copia en caliente)
kubectl -n nubeultima exec deploy/ingestion-api -- \
  sh -c 'sqlite3 /data/nubeultima.db ".backup /tmp/nubeultima.db"' 2>/dev/null || \
kubectl -n nubeultima exec deploy/ingestion-api -- \
  sh -c 'apk add --no-cache sqlite >/dev/null 2>&1; python -c "import sqlite3,shutil; c=sqlite3.connect(\"/data/nubeultima.db\"); b=sqlite3.connect(\"/tmp/nubeultima.db\"); c.backup(b); b.close(); c.close()"'
POD=$(kubectl -n nubeultima get pod -l app=ingestion-api -o jsonpath='{.items[0].metadata.name}')
kubectl -n nubeultima cp "$POD:/tmp/nubeultima.db" "$STAGING/nubeultima.db"

# 2. Configuracion del cluster (manifiestos del repo + config de K3s de la VM control)
cp -r "$REPO/plataforma/k8s" "$REPO/saas/dashboard/k8s" "$STAGING/" 2>/dev/null || true
ssh $KEY pi@192.168.100.11 "sudo tar czf - /etc/rancher /var/lib/rancher/k3s/server/token 2>/dev/null" \
  > "$STAGING/k3s-config.tar.gz" || true

# 3. Snapshot de la base de datos interna de K3s (kine/sqlite)
ssh $KEY pi@192.168.100.11 "sudo sqlite3 /var/lib/rancher/k3s/server/db/state.db '.backup /tmp/k3s-state.db' && sudo cat /tmp/k3s-state.db" \
  > "$STAGING/k3s-state.db" 2>/dev/null || true

# 4. restic
restic snapshots >/dev/null 2>&1 || restic init
restic backup --tag auto --host nubeultima-pi "$STAGING"
restic forget --tag auto --keep-last 8 --keep-daily 5 --prune

# 5. Estado para el panel (se guarda en la base del ingestion-api, tabla baas_status)
LAST=$(restic snapshots --json --last | python3 -c 'import sys,json;s=json.load(sys.stdin);print(s[-1]["time"] if s else "nunca")')
SIZE=$(restic stats --mode raw-data --json | python3 -c 'import sys,json;print(round(json.load(sys.stdin)["total_size"]/1e6,1))')
N=$(restic snapshots --json | python3 -c 'import sys,json;print(len(json.load(sys.stdin)))')
JSON="{\"ultimo\":\"$LAST\",\"tamano_mb\":$SIZE,\"snapshots\":$N,\"generado\":\"$(date -u +%FT%TZ)\"}"
kubectl -n nubeultima exec deploy/ingestion-api -- \
  sqlite3 /data/nubeultima.db "INSERT OR REPLACE INTO baas_status(k,v) VALUES('backup', '$JSON')" 2>/dev/null || true

echo "[$(date -u +%FT%TZ)] === respaldo OK (ultimo: $LAST, ${SIZE} MB, $N snapshots) ==="
