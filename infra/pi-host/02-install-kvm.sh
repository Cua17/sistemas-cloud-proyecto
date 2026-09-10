#!/usr/bin/env bash
# infra/pi-host/02-install-kvm.sh
#
# Instala el hipervisor (KVM) y las herramientas de gestion de VMs (libvirt) en la Pi,
# y define la red virtual del centro de datos.
#
# Uso (en la Pi):  bash 02-install-kvm.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== 1. Instalar QEMU + KVM + libvirt + herramientas =="
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install \
  qemu-system-arm qemu-utils \
  libvirt-daemon-system libvirt-clients \
  virtinst cloud-image-utils \
  dnsmasq-base bridge-utils

echo "== 2. Agregar el usuario '$USER' a los grupos libvirt y kvm =="
sudo usermod -aG libvirt,kvm "$USER"

echo "== 3. Verificar que la virtualizacion por hardware funciona =="
if [ -e /dev/kvm ]; then
  echo "  -> /dev/kvm existe  (aceleracion KVM disponible)"
else
  echo "  !! /dev/kvm NO existe - las VMs irian por emulacion pura (lentisimo)"
  echo "     Revisar: dmesg | grep -i kvm"
fi
sudo systemctl enable --now libvirtd
virsh --connect qemu:///system version

echo "== 4. Definir y arrancar la red virtual 'nubeultima' (192.168.100.0/24) =="
if ! virsh --connect qemu:///system net-info nubeultima >/dev/null 2>&1; then
  virsh --connect qemu:///system net-define "$HERE/nubeultima-net.xml"
fi
virsh --connect qemu:///system net-autostart nubeultima
virsh --connect qemu:///system net-start nubeultima 2>/dev/null || true
virsh --connect qemu:///system net-list --all

echo
echo ">>> KVM listo. Cerra y volve a abrir la sesion SSH para tomar los grupos nuevos."
