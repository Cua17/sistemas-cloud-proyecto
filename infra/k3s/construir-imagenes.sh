#!/usr/bin/env bash
# infra/k3s/construir-imagenes.sh
#
# Construye las 3 imagenes propias (ARM64) EN LA PI y las importa directo al
# containerd de K3s en los dos nodos. No usa ningun registro externo (Docker Hub):
# el homelab queda autocontenido y la demo no depende de internet.
#
# Uso (en la Pi):  bash infra/k3s/construir-imagenes.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TAG=0.1.0
NODES=(192.168.100.11 192.168.100.12)
SSH="ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i $HOME/.ssh/id_ed25519"

declare -A CTX=(
  [nubeultima/device-simulator]="$REPO/plataforma/device-simulator"
  [nubeultima/ingestion-api]="$REPO/plataforma/ingestion-api"
  [nubeultima/dashboard]="$REPO/saas/dashboard"
)

command -v docker >/dev/null || { echo "Falta docker. Instalar con: sudo apt-get install -y docker.io && sudo usermod -aG docker $USER"; exit 1; }

for IMG in "${!CTX[@]}"; do
  echo "== construyendo $IMG:$TAG =="
  docker build -q -t "$IMG:$TAG" "${CTX[$IMG]}"

  echo "   exportando e importando en los nodos de K3s..."
  TAR="/tmp/$(basename "$IMG").tar"
  docker save "$IMG:$TAG" -o "$TAR"
  for N in "${NODES[@]}"; do
    $SSH pi@"$N" "sudo k3s ctr images import -" < "$TAR"
    echo "   -> $N OK"
  done
  rm -f "$TAR"
done

echo
echo ">>> Imagenes listas en los dos nodos:"
$SSH pi@192.168.100.11 "sudo k3s ctr images ls | grep nubeultima || true"
