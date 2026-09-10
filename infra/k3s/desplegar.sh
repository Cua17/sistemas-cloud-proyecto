#!/usr/bin/env bash
# infra/k3s/desplegar.sh
#
# Despliega toda la plataforma en el clúster K3s y espera a que este lista.
# Uso (en la Pi):  bash infra/k3s/desplegar.sh
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "== Aplicando manifiestos =="
kubectl apply -f "$REPO/plataforma/k8s/"
kubectl apply -f "$REPO/saas/dashboard/k8s/"

echo
echo "== Esperando a que los pods esten listos =="
kubectl -n nubeultima rollout status deploy/mqtt-broker     --timeout=120s
kubectl -n nubeultima rollout status deploy/ingestion-api   --timeout=180s
kubectl -n nubeultima rollout status deploy/dashboard       --timeout=120s
kubectl -n nubeultima rollout status deploy/device-simulator --timeout=120s

echo
kubectl -n nubeultima get pods -o wide
echo
echo ">>> Panel SaaS (NodePort): http://192.168.100.11:30080/  y  http://192.168.100.12:30080/"
