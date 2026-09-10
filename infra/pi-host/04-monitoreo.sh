#!/usr/bin/env bash
# infra/pi-host/04-monitoreo.sh
#
# Monitoreo del hardware (rubrica: "monitorizar el HW utilizado"):
#   - node_exporter en la Pi (metricas: CPU, RAM, disco, red, temperatura)
#   - Prometheus en la Pi, retencion corta (6h), scrapea la Pi + las 3 VMs
#   - Grafana en la Pi con el dashboard "Node Exporter Full"
#
# Uso (en la Pi):  bash infra/pi-host/04-monitoreo.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== 1. node_exporter + Prometheus (repos de Debian) =="
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install \
  prometheus-node-exporter prometheus

echo "== 2. Config de Prometheus: retencion 6h, scrape Pi + 3 VMs =="
sudo tee /etc/prometheus/prometheus.yml >/dev/null <<'EOF'
global:
  scrape_interval: 15s
  external_labels: { proyecto: nubeultima }

scrape_configs:
  - job_name: raspberry-pi
    static_configs:
      - targets: ["localhost:9100"]
        labels: { maquina: "raspberry-pi" }
  - job_name: vms
    static_configs:
      - targets: ["192.168.100.11:9100"]
        labels: { maquina: "vm-control" }
      - targets: ["192.168.100.12:9100"]
        labels: { maquina: "vm-worker" }
      - targets: ["192.168.100.13:9100"]
        labels: { maquina: "vm-storage" }
EOF
# retencion corta para cuidar la RAM y la microSD
sudo sed -i 's|^ARGS=.*|ARGS="--storage.tsdb.retention.time=6h --storage.tsdb.retention.size=256MB"|' /etc/default/prometheus
sudo systemctl enable --now prometheus prometheus-node-exporter
sudo systemctl restart prometheus

echo "== 3. Grafana (repo oficial de Grafana Labs) =="
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://apt.grafana.com/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/grafana.gpg
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" \
  | sudo tee /etc/apt/sources.list.d/grafana.list >/dev/null
sudo apt-get update -q
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install grafana

echo "== 4. Grafana: fuente de datos Prometheus + dashboard Node Exporter Full =="
sudo tee /etc/grafana/provisioning/datasources/prometheus.yml >/dev/null <<'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
EOF
sudo mkdir -p /var/lib/grafana/dashboards
# Dashboard "Node Exporter Full" (grafana.com id 1860), adaptado para provisioning:
# se fija la fuente de datos a "Prometheus" y se quitan los __inputs.
TMP="$(mktemp)"
curl -fsSL "https://grafana.com/api/dashboards/1860/revisions/latest/download" -o "$TMP" || true
if [ -s "$TMP" ]; then
  jq 'walk(if type=="object" and has("datasource") and (.datasource|type)=="string"
           then .datasource="Prometheus" else . end)
      | walk(if type=="object" and (.datasource.type=="prometheus")
             then .datasource="Prometheus" else . end)
      | del(.__inputs, .__requires) | .id=null | .uid="node-exporter-full"' \
    "$TMP" | sudo tee /var/lib/grafana/dashboards/node-exporter-full.json >/dev/null
fi
rm -f "$TMP"
sudo tee /etc/grafana/provisioning/dashboards/nubeultima.yml >/dev/null <<'EOF'
apiVersion: 1
providers:
  - name: NubeUltima
    folder: NubeUltima
    type: file
    options: { path: /var/lib/grafana/dashboards }
EOF
sudo systemctl enable --now grafana-server

echo
echo ">>> Monitoreo listo:"
echo "    Prometheus:  http://$(hostname -I | awk '{print $1}'):9090"
echo "    Grafana:     http://$(hostname -I | awk '{print $1}'):3000   (admin / admin)"
free -h | head -2
