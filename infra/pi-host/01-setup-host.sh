#!/usr/bin/env bash
# infra/pi-host/01-setup-host.sh
#
# Preparacion del host: la Raspberry Pi que sera el "centro de datos" fisico.
# Idempotente: se puede correr varias veces.
#
# Uso (en la Pi):  bash 01-setup-host.sh
set -euo pipefail

echo "== 1. Habilitar el controlador de memoria de cgroups (Docker lo necesita) =="
# Raspberry Pi OS (Trixie) desactiva 'memory' por defecto para ahorrar recursos.
# Lo re-activamos agregando parametros al final de cmdline.txt (una sola linea).
CMDLINE=/boot/firmware/cmdline.txt
if ! grep -q 'cgroup_enable=memory' "$CMDLINE"; then
  sudo sed -i 's/$/ cgroup_enable=memory cgroup_memory=1/' "$CMDLINE"
  echo "  -> agregado. Requiere reinicio."
  NEEDS_REBOOT=1
else
  echo "  -> ya estaba."
fi

echo "== 2. Logs del sistema a RAM (proteger la microSD) =="
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=volatile\nRuntimeMaxUse=64M\n' \
  | sudo tee /etc/systemd/journald.conf.d/00-volatile.conf >/dev/null
sudo systemctl restart systemd-journald || true

echo "== 3. Quitar swapfile viejo en la tarjeta (si existe) =="
# La Pi ya usa zram (swap comprimido en RAM) por defecto; el archivo en disco sobra.
sudo rm -f /var/swap && echo "  -> /var/swap borrado" || true

echo "== 4. Actualizar el sistema e instalar utilidades =="
sudo apt-get update -q
sudo DEBIAN_FRONTEND=noninteractive apt-get -y full-upgrade
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install \
  git curl jq htop iperf3 ca-certificates gnupg
sudo apt-get -y autoremove --purge
sudo apt-get clean

echo
if [ "${NEEDS_REBOOT:-0}" = "1" ]; then
  echo ">>> REINICIAR la Pi ahora:  sudo reboot"
else
  echo ">>> Host listo."
fi
