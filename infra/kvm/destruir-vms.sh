#!/usr/bin/env bash
# infra/kvm/destruir-vms.sh
#
# Apaga y borra las 3 VMs (dominios + discos). NO borra la imagen base descargada.
# Uso (en la Pi):  bash infra/kvm/destruir-vms.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$HERE/vms.conf"
IMGDIR=/var/lib/libvirt/images
VIRSH="virsh --connect qemu:///system"

grep -vE '^\s*#|^\s*$' "$CONF" | while read -r NAME IP RAM VCPUS DISK; do
  echo "== $NAME =="
  $VIRSH destroy "$NAME" 2>/dev/null || true          # apagar (forzado)
  $VIRSH undefine "$NAME" --nvram 2>/dev/null || true # borrar la definicion
  sudo rm -f "$IMGDIR/${NAME}.qcow2" "$IMGDIR/${NAME}-seed.iso"
  ssh-keygen -R "$IP" >/dev/null 2>&1 || true         # olvidar la llave SSH de esa VM
done

echo
$VIRSH list --all
echo ">>> VMs destruidas. (La imagen base queda en $IMGDIR/base para recrear rapido.)"
