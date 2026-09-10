#!/usr/bin/env bash
# infra/pi-host/03-port-forward.sh
#
# Publica el panel SaaS (que vive en la VM control, 192.168.100.11:30080) hacia la
# red de casa: quien entre a  http://<IP-de-la-Pi>:8080  llega al panel.
#
# Usa 'socat' como proxy TCP en la Pi: escucha en el 8080 y abre una conexion
# nueva hacia la VM. Simple y no pelea con el firewall de libvirt.
# Se instala como servicio systemd para que sobreviva reinicios.
#
# Uso (en la Pi):  bash infra/pi-host/03-port-forward.sh
set -euo pipefail

DEST=192.168.100.11:30080
PUB_PORT=8080

# limpiar el intento anterior con nftables si quedo
sudo systemctl disable --now nubeultima-portfwd.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/nubeultima-portfwd.service /etc/nftables-nubeultima-portfwd.nft
sudo nft delete table ip nubeultima_portfwd 2>/dev/null || true

sudo DEBIAN_FRONTEND=noninteractive apt-get -y install socat >/dev/null

sudo tee /etc/systemd/system/nubeultima-saas.service >/dev/null <<EOF
[Unit]
Description=NubeUltima - proxy del panel SaaS (8080 -> VM control)
After=network-online.target libvirtd.service
Wants=network-online.target

[Service]
ExecStart=/usr/bin/socat -d TCP-LISTEN:${PUB_PORT},fork,reuseaddr TCP:${DEST}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now nubeultima-saas.service
sleep 2
systemctl is-active nubeultima-saas.service

echo ">>> Panel accesible en:  http://$(hostname -I | awk '{print $1}'):${PUB_PORT}/"
echo "    (o  http://nubeultima.local:${PUB_PORT}/  )"
