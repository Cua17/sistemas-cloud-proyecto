#!/usr/bin/env bash
# pruebas/conectividad.sh
#
# Prueba de comunicacion bidireccional estable entre las 3 VMs del centro de datos
# (requisito de la rubrica). Mide:
#   - Latencia y perdida de paquetes con ping (matriz completa, los 6 sentidos)
#   - Ancho de banda con iperf3 (TCP, ida y vuelta)
#   - Jitter con iperf3 (UDP)
#
# Se ejecuta DESDE EL HOST (Git Bash o WSL) con Vagrant en el PATH:
#   cd "<repo>" && bash pruebas/conectividad.sh
#
# Orquesta todo por "vagrant ssh"; no necesita SSH entre VMs.

set -uo pipefail

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../infra" && pwd)"
export VAGRANT_CWD="$INFRA_DIR"

NODES=(datacenter-control datacenter-worker datacenter-storage)
declare -A IP=(
  [datacenter-control]=192.168.56.11
  [datacenter-worker]=192.168.56.12
  [datacenter-storage]=192.168.56.13
)

OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/resultado-conectividad.txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================================="
echo " NubeUltima - Prueba de conectividad del centro de datos"
echo " Fecha: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=================================================================="

vssh() { vagrant ssh "$1" -c "$2" 2>/dev/null; }

# ---------------------------------------------------------------- PING
echo
echo "### 1. LATENCIA (ping, 10 paquetes por sentido) ###"
echo
printf "%-22s %-22s %-8s %-12s\n" "ORIGEN" "DESTINO" "PERDIDA" "RTT prom"
printf -- "-%.0s" {1..70}; echo
for src in "${NODES[@]}"; do
  for dst in "${NODES[@]}"; do
    [ "$src" = "$dst" ] && continue
    res="$(vssh "$src" "ping -c 10 -q ${dst}")"
    loss="$(echo "$res" | grep -oE '[0-9]+% packet loss' | head -1)"
    avg="$(echo "$res"  | awk -F'/' '/rtt|round-trip/ {print $5" ms"}')"
    printf "%-22s %-22s %-8s %-12s\n" "$src" "$dst" "${loss:-ERROR}" "${avg:-ERROR}"
  done
done

# ------------------------------------------------------------- IPERF3
echo
echo "### 2. ANCHO DE BANDA y JITTER (iperf3) ###"
echo
echo "-- Arrancando servidores iperf3 (daemon) en las 3 VMs --"
for n in "${NODES[@]}"; do vssh "$n" "pkill iperf3 2>/dev/null; iperf3 -s -D; sleep 1"; done

echo
printf "%-22s %-22s %-14s %-10s\n" "ORIGEN" "DESTINO" "TCP Bitrate" "UDP Jitter"
printf -- "-%.0s" {1..70}; echo
for src in "${NODES[@]}"; do
  for dst in "${NODES[@]}"; do
    [ "$src" = "$dst" ] && continue
    tcp="$(vssh "$src" "iperf3 -c ${dst} -t 5 -f g" | awk '/receiver/ {print $7" "$8}')"
    udp="$(vssh "$src" "iperf3 -c ${dst} -t 5 -u -b 200M" | awk '/receiver/ {print $9" "$10}')"
    printf "%-22s %-22s %-14s %-10s\n" "$src" "$dst" "${tcp:-ERROR}" "${udp:-ERROR}"
  done
done

echo
echo "-- Apagando servidores iperf3 --"
for n in "${NODES[@]}"; do vssh "$n" "pkill iperf3 2>/dev/null || true"; done

echo
echo "=================================================================="
echo " Fin. Resultado guardado en: $OUT"
echo "=================================================================="
