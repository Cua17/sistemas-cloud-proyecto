#!/usr/bin/env bash
# infra/pi-host/05-baas.sh
#
# Configura el BaaS en la Pi:
#   - restic (repos de Debian)
#   - credenciales (restic + MinIO) en /etc/nubeultima/  (NO en git)
#   - timers systemd: respaldo cada 30 min, prueba de restauracion cada 6 h
#
# Requiere que MinIO ya este corriendo en la VM storage (infra/ansible/minio.yml).
#
# Uso (en la Pi):
#   MINIO_ACCESS=nubeultima MINIO_SECRET='<clave>' RESTIC_PW='<clave>' bash infra/pi-host/05-baas.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

: "${MINIO_ACCESS:?falta MINIO_ACCESS}"
: "${MINIO_SECRET:?falta MINIO_SECRET}"
: "${RESTIC_PW:?falta RESTIC_PW}"

echo "== 1. Instalar restic + sqlite3 + mc =="
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install restic sqlite3
command -v mc >/dev/null || {
  sudo curl -fsSL https://dl.min.io/client/mc/release/linux-arm64/mc -o /usr/local/bin/mc
  sudo chmod +x /usr/local/bin/mc
}
mc alias set local http://192.168.100.13:9000 "$MINIO_ACCESS" "$MINIO_SECRET" >/dev/null

echo "== 2. Credenciales en /etc/nubeultima/ (permisos 600) =="
sudo mkdir -p /etc/nubeultima
printf '%s' "$RESTIC_PW"     | sudo tee /etc/nubeultima/restic-password >/dev/null
printf '%s' "$MINIO_ACCESS"  | sudo tee /etc/nubeultima/minio-access   >/dev/null
printf '%s' "$MINIO_SECRET"  | sudo tee /etc/nubeultima/minio-secret   >/dev/null
sudo chmod 600 /etc/nubeultima/*

echo "== 3. Scripts a /usr/local/bin =="
sudo install -m750 "$REPO/infra/baas/backup.sh"       /usr/local/bin/nubeultima-backup
sudo install -m750 "$REPO/infra/baas/restore-test.sh" /usr/local/bin/nubeultima-restore-test

echo "== 4. Timers systemd =="
sudo tee /etc/systemd/system/nubeultima-backup.service >/dev/null <<'EOF'
[Unit]
Description=NubeUltima - respaldo BaaS
[Service]
Type=oneshot
ExecStart=/usr/local/bin/nubeultima-backup
EOF
sudo tee /etc/systemd/system/nubeultima-backup.timer >/dev/null <<'EOF'
[Unit]
Description=NubeUltima - respaldo cada 30 min
[Timer]
OnBootSec=5min
OnUnitActiveSec=30min
Persistent=true
[Install]
WantedBy=timers.target
EOF
sudo tee /etc/systemd/system/nubeultima-restore-test.service >/dev/null <<'EOF'
[Unit]
Description=NubeUltima - verificacion de respaldos
[Service]
Type=oneshot
ExecStart=/usr/local/bin/nubeultima-restore-test
EOF
sudo tee /etc/systemd/system/nubeultima-restore-test.timer >/dev/null <<'EOF'
[Unit]
Description=NubeUltima - prueba de restauracion cada 6 h
[Timer]
OnBootSec=15min
OnUnitActiveSec=6h
Persistent=true
[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now nubeultima-backup.timer nubeultima-restore-test.timer

echo
echo ">>> BaaS configurado. Timers:"
systemctl list-timers 'nubeultima-*' --no-pager
