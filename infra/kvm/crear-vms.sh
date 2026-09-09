#!/usr/bin/env bash
# infra/kvm/crear-vms.sh
#
# Crea las 3 VMs del centro de datos NubeUltima sobre KVM/libvirt, desde cero,
# usando la imagen "cloud" oficial de Debian 13 (ARM64) + cloud-init.
# Esto es "infraestructura como codigo": las VMs se describen en vms.conf y
# se construyen con un comando.
#
# Uso (en la Pi):  bash infra/kvm/crear-vms.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF="$HERE/vms.conf"
IMGDIR=/var/lib/libvirt/images
BASEDIR="$IMGDIR/base"
BASE_URL="https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-arm64.qcow2"
BASE_IMG="$BASEDIR/debian-13-genericcloud-arm64.qcow2"
VIRSH="virsh --connect qemu:///system"

# --- Clave SSH del usuario de la Pi (para que la Pi pueda administrar las VMs con Ansible)
[ -f ~/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C "pi@nubeultima"
PI_PUBKEY="$(cat ~/.ssh/id_ed25519.pub)"
# --- Clave SSH de la laptop (para poder entrar a las VMs desde afuera via la Pi)
LAPTOP_PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMbyiVrpiUwmvnzNoR5P+5uwxVNE8kXrewdihxJgFkSE nubeultima-20260909"

echo "== 1. Descargar la imagen base de Debian 13 ARM64 (una sola vez) =="
sudo mkdir -p "$BASEDIR"
if [ ! -f "$BASE_IMG" ]; then
  sudo curl -fL --progress-bar -o "$BASE_IMG" "$BASE_URL"
else
  echo "  -> ya esta: $BASE_IMG"
fi

# --- recorrer vms.conf ---
grep -vE '^\s*#|^\s*$' "$CONF" | while read -r NAME IP RAM VCPUS DISK; do
  echo
  echo "==================  $NAME  ($IP, ${RAM}MB, ${VCPUS} vCPU)  =================="

  if $VIRSH dominfo "$NAME" >/dev/null 2>&1; then
    echo "  ya existe, se omite (usa destruir-vms.sh primero para recrear)"
    continue
  fi

  DISKIMG="$IMGDIR/${NAME}.qcow2"
  SEEDIMG="$IMGDIR/${NAME}-seed.iso"
  WORK="$(mktemp -d)"

  echo "  -> disco de arranque (overlay sobre la imagen base, ${DISK}G)"
  sudo qemu-img create -f qcow2 -F qcow2 -b "$BASE_IMG" "$DISKIMG" "${DISK}G" >/dev/null

  echo "  -> cloud-init (hostname, IP estatica, llaves SSH)"
  cat > "$WORK/meta-data" <<EOF
instance-id: $NAME
local-hostname: $NAME
EOF

  cat > "$WORK/user-data" <<EOF
#cloud-config
hostname: $NAME
fqdn: $NAME
manage_etc_hosts: true
users:
  - name: pi
    sudo: "ALL=(ALL) NOPASSWD:ALL"
    shell: /bin/bash
    lock_passwd: true
    ssh_authorized_keys:
      - $PI_PUBKEY
      - $LAPTOP_PUBKEY
ssh_pwauth: false
package_update: false
package_upgrade: false
runcmd:
  - [ systemctl, disable, --now, systemd-networkd-wait-online.service ]
EOF

  cat > "$WORK/network-config" <<EOF
version: 2
ethernets:
  primary:
    match:
      name: "e*"
    dhcp4: false
    addresses: [ $IP/24 ]
    routes:
      - to: default
        via: 192.168.100.1
    nameservers:
      addresses: [ 192.168.100.1, 1.1.1.1 ]
EOF

  sudo cloud-localds -N "$WORK/network-config" "$SEEDIMG" "$WORK/user-data" "$WORK/meta-data"
  rm -rf "$WORK"

  echo "  -> creando la VM con virt-install"
  sudo virt-install \
    --connect qemu:///system \
    --name "$NAME" \
    --memory "$RAM" \
    --vcpus "$VCPUS" \
    --cpu host-passthrough \
    --os-variant debian12 \
    --import \
    --disk path="$DISKIMG",format=qcow2,bus=virtio \
    --disk path="$SEEDIMG",device=cdrom \
    --network network=nubeultima,model=virtio \
    --graphics none \
    --console pty,target_type=serial \
    --noautoconsole
  $VIRSH autostart "$NAME"
done

echo
echo "== 2. Esperando a que las 3 VMs respondan por SSH =="
for IP in 192.168.100.11 192.168.100.12 192.168.100.13; do
  printf "  %s " "$IP"
  for i in $(seq 1 60); do
    if ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=3 \
        pi@"$IP" true 2>/dev/null; then
      echo "OK"; break
    fi
    printf "."; sleep 5
    [ "$i" = 60 ] && echo " TIMEOUT"
  done
done

echo
$VIRSH list --all
echo
echo ">>> VMs creadas. Siguiente: configuracion base con Ansible."
