#!/usr/bin/env bash
# pruebas/conectividad.sh
#
# Prueba de comunicacion bidireccional estable entre las 3 VMs del centro de datos
# (requisito de la rubrica). Mide:
#   - Latencia y perdida de paquetes con ping (matriz completa, los 6 sentidos)
#   - Ancho de banda con iperf3 (TCP)
#   - Jitter con iperf3 (UDP)
#
# Se ejecuta DESDE LA RASPBERRY PI:
#   bash pruebas/conectividad.sh
#
# Orquesta todo por "ssh"; no necesita nada corriendo de antemano en las VMs.

set -uo pipefail

declare -A IP=(
  [control]=192.168.100.11
  [worker]=192.168.100.12
  [storage]=192.168.100.13
)
NODES=(control worker storage)
# Las VMs son infraestructura desechable (se recrean seguido -> cambian de llave SSH).
# En esta red privada interna no verificamos host keys.
SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
     -o LogLevel=ERROR -o ConnectTimeout=5 -i $HOME/.ssh/id_ed25519"

OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/resultado-conectividad.txt"
exec > >(tee "$OUT") 2>&1

echo "=================================================================="
echo " NubeUltima - Prueba de conectividad del centro de datos"
echo " Fecha: $(date -u '+%Y-%m-%d %H:%M:%S UTC')   (host: $(hostname))"
echo "=================================================================="

vssh() { $SSH pi@"${IP[$1]}" "$2"; }

# ---------------------------------------------------------------- PING
echo
echo "### 1. LATENCIA (ping, 10 paquetes por sentido) ###"
echo
printf "%-10s %-10s %-16s %-12s\n" "ORIGEN" "DESTINO" "PERDIDA" "RTT prom"
printf -- '-%.0s' {1..52}; echo
for src in "${NODES[@]}"; do
  for dst in "${NODES[@]}"; do
    [ "$src" = "$dst" ] && continue
    res="$(vssh "$src" "ping -c 10 -q ${IP[$dst]}")"
    loss="$(echo "$res" | grep -oE '[0-9]+% packet loss' | head -1)"
    avg="$(echo "$res"  | awk -F'/' '/rtt|round-trip/ {print $5" ms"}')"
    printf "%-10s %-10s %-16s %-12s\n" "$src" "$dst" "${loss:-ERROR}" "${avg:-ERROR}"
  done
done

# ------------------------------------------------------------- IPERF3
echo
echo "### 2. ANCHO DE BANDA y JITTER (iperf3) ###"
echo
echo "-- Arrancando servidores iperf3 (daemon) en las 3 VMs --"
for n in "${NODES[@]}"; do vssh "$n" "pkill iperf3 2>/dev/null; iperf3 -s -D; sleep 1"; done

echo
printf "%-10s %-10s %-16s %-12s\n" "ORIGEN" "DESTINO" "TCP Bitrate" "UDP Jitter"
printf -- '-%.0s' {1..52}; echo
for src in "${NODES[@]}"; do
  for dst in "${NODES[@]}"; do
    [ "$src" = "$dst" ] && continue
    tcp="$(vssh "$src" "iperf3 -c ${IP[$dst]} -t 5 -f m" | awk '/receiver/ {print $7" "$8}')"
    udp="$(vssh "$src" "iperf3 -c ${IP[$dst]} -t 5 -u -b 100M" | awk '/receiver/ {print $9" "$10}')"
    printf "%-10s %-10s %-16s %-12s\n" "$src" "$dst" "${tcp:-ERROR}" "${udp:-ERROR}"
  done
done

echo
echo "-- Apagando servidores iperf3 --"
for n in "${NODES[@]}"; do vssh "$n" "pkill iperf3 2>/dev/null || true"; done

echo
echo "=================================================================="
echo " Fin. Resultado guardado en: $OUT"
echo "=================================================================="
