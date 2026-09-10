#!/usr/bin/env bash
# infra/baas/restore-test.sh
#
# Verificacion de los respaldos (rubrica): restaura el ultimo snapshot de restic
# a un directorio temporal y comprueba que la base de datos es valida y tiene datos.
# Escribe el resultado (OK/FALLO + fecha) en un archivo de estado y en MinIO.
set -uo pipefail

export KUBECONFIG=/home/pi/.kube/config
export RESTIC_REPOSITORY="s3:http://192.168.100.13:9000/nubeultima-backups"
export RESTIC_PASSWORD_FILE=/etc/nubeultima/restic-password
export AWS_ACCESS_KEY_ID="$(cat /etc/nubeultima/minio-access)"
export AWS_SECRET_ACCESS_KEY="$(cat /etc/nubeultima/minio-secret)"

SCRATCH=$(mktemp -d)
ESTADO=/var/lib/nubeultima/restore-test.json
sudo mkdir -p "$(dirname "$ESTADO")"

fin() { rm -rf "$SCRATCH"; }
trap fin EXIT

echo "[$(date -u +%FT%TZ)] restaurando ultimo snapshot a $SCRATCH ..."
if ! restic restore latest --target "$SCRATCH" ; then
  RES="FALLO"; DETALLE="restic restore fallo"; FILAS=0
else
  DB=$(find "$SCRATCH" -name nubeultima.db | head -1)
  if [ -z "$DB" ]; then
    RES="FALLO"; DETALLE="no se encontro nubeultima.db en el backup"; FILAS=0
  else
    FILAS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM readings" 2>/dev/null || echo 0)
    INTEG=$(sqlite3 "$DB" "PRAGMA integrity_check" 2>/dev/null || echo error)
    if [ "$INTEG" = "ok" ] && [ "$FILAS" -gt 0 ]; then
      RES="OK"; DETALLE="base integra, $FILAS lecturas restauradas"
    else
      RES="FALLO"; DETALLE="integridad=$INTEG filas=$FILAS"
    fi
  fi
fi

JSON="{\"resultado\":\"$RES\",\"detalle\":\"$DETALLE\",\"filas_restauradas\":$FILAS,\"fecha\":\"$(date -u +%FT%TZ)\"}"
echo "$JSON" | sudo tee "$ESTADO"
kubectl -n nubeultima exec deploy/ingestion-api -- python -c "
import sqlite3; c=sqlite3.connect('/data/nubeultima.db')
c.execute('INSERT OR REPLACE INTO baas_status(k,v) VALUES(?,?)', ('restore_test', '''$JSON'''))
c.commit()" 2>/dev/null || true

echo "[$(date -u +%FT%TZ)] restore-test: $RES - $DETALLE"
[ "$RES" = "OK" ]
