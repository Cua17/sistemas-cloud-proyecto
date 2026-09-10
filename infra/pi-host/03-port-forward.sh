#!/usr/bin/env bash
# infra/pi-host/03-port-forward.sh
#
# Publica el panel SaaS (que vive en una VM, 192.168.100.11:30080) hacia la red
# de casa: quien entre a  http://<IP-de-la-Pi>:8080  llega al panel.
#
# Usa nftables (NAT/DNAT) en la Pi. Se instala como servicio systemd para que
# sobreviva reinicios.
#
# Uso (en la Pi):  bash infra/pi-host/03-port-forward.sh
set -euo pipefail

DEST_IP=192.168.100.11
DEST_PORT=30080
PUB_PORT=8080

sudo tee /etc/nftables-nubeultima-portfwd.nft >/dev/null <<EOF
#!/usr/sbin/nft -f
# Reenvio de puerto del panel SaaS de NubeUltima.
table ip nubeultima_portfwd
delete table ip nubeultima_portfwd
table ip nubeultima_portfwd {
  chain prerouting {
    type nat hook prerouting priority dstnat - 5; policy accept;
    tcp dport $PUB_PORT dnat to $DEST_IP:$DEST_PORT
  }
  chain postrouting {
    type nat hook postrouting priority srcnat - 5; policy accept;
    ip daddr $DEST_IP tcp dport $DEST_PORT masquerade
  }
}
EOF

sudo tee /etc/systemd/system/nubeultima-portfwd.service >/dev/null <<'EOF'
[Unit]
Description=NubeUltima - reenvio del puerto del panel SaaS
After=network-online.target libvirtd.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/nftables-nubeultima-portfwd.nft
ExecStop=/usr/sbin/nft delete table ip nubeultima_portfwd

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now nubeultima-portfwd.service

echo ">>> Panel accesible en:  http://$(hostname -I | awk '{print $1}'):$PUB_PORT/"
echo "    (o  http://nubeultima.local:$PUB_PORT/  )"
sudo nft list table ip nubeultima_portfwd
