# NubeÚltima — Plan de Implementación (Fase 1)

> **Para quien ejecuta:** este plan se trabaja tarea por tarea. Cada tarea termina con
> una verificación concreta y un commit. Las casillas `- [ ]` sirven para llevar el avance.
> Trabajo colaborativo: varias fases se pueden avanzar en paralelo (ver reparto en el
> documento de diseño), pero dentro de una fase las tareas van en orden.

**Meta:** construir en una laptop una plataforma cloud de telemetría IoT para municipio
inteligente que demuestre IaaS, PaaS, SaaS y BaaS, cumpliendo la rúbrica de la Fase 1.

**Arquitectura:** 3 VMs Linux en VirtualBox (IaaS) con IPs estáticas y red host-only;
sobre VM1+VM2 corre un clúster K3s (PaaS) con microservicios propios en Python + Mosquitto
+ InfluxDB; un panel web es el SaaS; VM3 (fuera del clúster) hospeda MinIO y es el destino
de los respaldos de Velero + restic (BaaS). Monitoreo de hardware con Prometheus + Grafana.

**Stack:** VirtualBox 7.2, Vagrant 2.4.9, Ansible (modo `ansible_local`), Ubuntu Server 24.04 LTS,
K3s, Helm, Eclipse Mosquitto, InfluxDB 2.x OSS, Python 3.12 + FastAPI + paho-mqtt,
kube-prometheus-stack, Velero, restic, MinIO.

## Restricciones globales (aplican a TODAS las tareas)

- **IPs estáticas obligatorias** (lo pide la rúbrica): VM1 `192.168.56.11`, VM2
  `192.168.56.12`, VM3 `192.168.56.13`. Red host-only `192.168.56.0/24`, gateway `.1`.
  **No usar DHCP** para el direccionamiento del centro de datos.
- Cada VM tiene además una segunda interfaz NAT solo para salida a internet (apt, imágenes).
- Las 3 VMs se definen de forma independiente en el `Vagrantfile`.
- **Gotcha de K3s con 2 interfaces:** hay que pasarle siempre `--node-ip` y
  `--flannel-iface <interfaz host-only>`, si no K3s toma la IP de la NAT (`10.0.2.15`,
  igual en las 3 VMs) y el clúster se rompe.
- Todo el software es libre / gratuito para uso educativo. Costo: USD 0.
- Imágenes de contenedor solo desde fuentes oficiales (Docker Hub *Official Images*,
  Quay.io, o los proyectos oficiales).
- SSH solo por llave, sin contraseña.
- Host: Windows 11 Home, Ryzen 7 7840HS, 16 GB RAM. Las 3 VMs juntas usan ~7–8 GB.
- **Confirmar con el catedrático** qué son "los 4 tipos de servicio que deben correr"
  (este plan asume: panel SaaS, API de ingestión, Grafana, portal BaaS).
- Idioma del código e identificadores: inglés. Comentarios y documentación: español.

---

## Mapa de archivos

```
Sistemas Cloud/
├── infra/
│   ├── Vagrantfile                      # define las 3 VMs, red host-only, IPs estáticas
│   ├── ansible/
│   │   ├── common.yml                   # hostname, paquetes base, SSH hardening, node_exporter
│   │   ├── k3s-server.yml               # instala K3s server en VM1
│   │   ├── k3s-agent.yml                # instala K3s agent en VM2
│   │   └── storage.yml                  # instala MinIO en VM3
│   └── kubeconfig/                      # k3s.yaml copiado para usar kubectl desde el host
├── plataforma/
│   ├── device-simulator/                # PROPIO: genera telemetría y la publica por MQTT
│   │   ├── simulator.py
│   │   ├── patterns.py                  # curvas de consumo, inyección de anomalías
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── tests/test_patterns.py
│   ├── ingestion-api/                   # PROPIO: MQTT -> validación -> InfluxDB + API REST
│   │   ├── app/main.py                  # FastAPI
│   │   ├── app/models.py                # esquemas Pydantic
│   │   ├── app/mqtt_consumer.py
│   │   ├── app/influx.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── tests/test_models.py, tests/test_api.py
│   ├── anomaly-service/                 # PROPIO: reglas de umbral -> alertas
│   │   ├── rules.py
│   │   ├── service.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── tests/test_rules.py
│   ├── docker-compose.yml               # entorno de desarrollo local (mosquitto+influx+servicios)
│   └── k8s/
│       ├── 00-namespaces.yaml
│       ├── 01-networkpolicies.yaml
│       ├── 10-mosquitto.yaml
│       ├── 11-influxdb.yaml
│       ├── 20-ingestion-api.yaml
│       ├── 21-anomaly-service.yaml
│       ├── 22-device-simulator.yaml
│       └── 30-ingress.yaml
├── saas/
│   └── dashboard/                       # PROPIO: panel del operador (el SaaS)
│       ├── app/main.py
│       ├── app/templates/
│       ├── app/static/
│       ├── Dockerfile
│       └── k8s/40-dashboard.yaml
├── monitoreo/
│   ├── values-kube-prometheus.yaml
│   └── dashboards/hw-3vms.json
├── backup/
│   ├── minio/                           # config de MinIO (buckets, políticas)
│   ├── velero/install.md, velero/schedule.yaml
│   ├── restic/restic-etcd.timer, restic/restic-etcd.service, restic/backup.sh
│   └── restore-test/restore-test-cronjob.yaml
├── pruebas/
│   ├── conectividad.sh                  # matriz ping + iperf3 entre las 3 VMs
│   ├── carga-mqtt.py                    # inunda telemetría para probar bajo carga
│   └── restore-drill.md                 # simulacro de desastre documentado
├── scripts/
│   ├── deploy-all.sh                    # despliega toda la plataforma sobre el clúster
│   └── screenshots.md                   # checklist de capturas para el informe
└── docs/
    ├── superpowers/specs/               # documento de diseño
    ├── superpowers/plans/               # este plan
    └── informe/                         # el documento escrito de entrega
```

---

# FASE 0 — Preparación del entorno

### Tarea 0.1: Instalar herramientas en la laptop host

**Objetivo:** tener VirtualBox, Vagrant, Git y un editor listos en Windows.

- [x] **Paso 1:** Instalar **VirtualBox** — `winget install --id Oracle.VirtualBox -e`. NO instalar el Extension Pack. (Instalado: 7.2.16)
- [x] **Paso 2:** Instalar **Vagrant** — `winget install --id Hashicorp.Vagrant -e`. (Instalado: 2.4.9)
- [x] **Paso 3:** Git ya estaba (2.50.1). Instalar **VS Code** si se quiere: `winget install --id Microsoft.VisualStudioCode -e`.
- [x] **Paso 4:** Instalar **kubectl** y **helm** — `winget install --id Kubernetes.kubectl -e` y `winget install --id Helm.Helm -e`. (Instalados: kubectl 1.37.0, helm 4.2.4)

**Verificación (hecha 2026-09-01):** todas devuelven versión —
`VBoxManage 7.2.16r174877`, `Vagrant 2.4.9`, `git 2.50.1`, `kubectl v1.37.0`, `helm v4.2.4`.

> **Nota de versiones:** salieron más nuevas que las del plan original (VirtualBox 7.2 en
> vez de 7.1, Helm 4.x en vez de 3.15). Sin impacto esperado; si Vagrant avisa que la
> versión de VirtualBox es "untested", igual funciona. Se confirma en la Tarea 1.1.

**Para entender y explicar:** VirtualBox es el **hipervisor tipo 2** (corre sobre Windows,
no sobre el hardware directo). Vagrant no virtualiza nada: es un "control remoto" que le
dice a VirtualBox qué VMs crear, a partir de un archivo de texto. Esto es *Infraestructura
como Código*: la infraestructura se describe en archivos versionados, no se arma a mano.

- [ ] **Paso 5: Commit** (el repo ya está iniciado en la carpeta del curso):
```bash
git add docs/ && git commit -m "docs: plan de implementacion Fase 1"
```

---

### Tarea 0.2: Estructura del repositorio y cuenta de Docker Hub

**Objetivo:** carpetas creadas y una cuenta gratuita para descargar imágenes sin límite.

- [x] **Paso 1:** Estructura de carpetas creada con `.gitkeep`. Hecho.
- [x] **Paso 2:** Cuenta de Docker Hub creada por el usuario. _(Pendiente: anotar el nombre de usuario acá.)_
- [x] **Paso 3:** `README.md` creado.
- [x] **Paso 4: Commit** — hecho.

**Para entender y explicar:** Docker Hub es un **registro de imágenes**: un repositorio
público de "plantillas" de contenedores. Sin cuenta, limita las descargas por hora; con
cuenta gratuita, alcanza de sobra. Las imágenes propias (las que construimos nosotros) las
vamos a subir ahí para que el clúster K3s las pueda bajar.

---

### Tarea 0.3: Descargar la imagen base de Ubuntu

**Objetivo:** tener la "box" de Vagrant lista localmente.

- [x] **Paso 1:** `vagrant box add bento/ubuntu-24.04 --provider virtualbox` — hecho.
- [x] **Paso 2:** box `bento/ubuntu-24.04` v202510.26.0 añadida.

**Verificación:** ✅ `vagrant box list` incluye la box.

**Para entender y explicar:** una *box* es una plantilla de VM ya instalada (Ubuntu Server
mínimo). En vez de instalar el SO a mano cada vez, Vagrant clona esta plantilla. Las boxes
`bento/*` las mantiene el equipo de Chef y son el estándar comunitario confiable.

---

# FASE 1 — IaaS: el centro de datos (3 VMs)

> ## ⚠️ REESCRITA 2026-09-09 para Raspberry Pi + KVM
>
> El proyecto pasó de "laptop + VirtualBox" a "Raspberry Pi 4 (4 GB) + KVM". Las tareas
> 1.1–1.4 de abajo (Vagrant/VirtualBox) quedan **archivadas como referencia**. La Fase 1
> real es esta:
>
> | Paso | Qué | Script / archivo | Estado |
> |---|---|---|---|
> | **1a** | Preparar el host: cgroups memory, `journald`→RAM, quitar swap de disco, `apt full-upgrade`, utilidades | `infra/pi-host/01-setup-host.sh` | ✅ 2026-09-09 |
> | **1b** | Instalar KVM + QEMU + libvirt; verificar `/dev/kvm`; crear la red virtual `nubeultima` 192.168.100.0/24 | `infra/pi-host/02-install-kvm.sh` + `nubeultima-net.xml` | ✅ 2026-09-09 |
> | **1c** | Crear las 3 VMs Debian 13 ARM64 con `virt-install` + cloud-init, IPs estáticas `.11/.12/.13` | `infra/kvm/crear-vms.sh` + `vms.conf` | ✅ 2026-09-10 |
> | **1d** | Configuración base de las 3 VMs (paquetes, hora, `/etc/hosts`, SSH) | `infra/ansible/common.yml` + `inventory.ini` | ✅ `ok=6 changed=4 failed=0` |
> | **1e** | Prueba de conectividad bidireccional (ping + iperf3) entre las 3 VMs | `pruebas/conectividad.sh` | ✅ 0% pérdida, ~2 Gbit/s, jitter <0.1 ms |
> | **1f** | Reconstrucción limpia: `destruir-vms.sh && crear-vms.sh` reproduce todo | `infra/kvm/destruir-vms.sh` | ✅ ciclo completo en ~6 min (crear-vms 85 s) |
>
> **✅ FASE 1 COMPLETA (2026-09-10).** Evidencia en `docs/informe/evidencias/`.
> RAM de la Pi con las 3 VMs: ~3.0 GB usados / ~0.6 GB libres + 2 GB zram. Temp ~54 °C.
> **Aviso:** en 4 GB la Fase 2 (Docker + Swarm + contenedores en las VMs) va a estar al límite.
>
> **Acceso:** la Pi es `nubeultima` (`192.168.0.51` en la red de casa, `nubeultima.local`).
> Se administra por SSH desde la laptop con `~/.ssh/id_ed25519_nubeultima`. Las VMs
> (192.168.100.x) se alcanzan desde la laptop con `ssh -J nubeultima pi@192.168.100.11`,
> y desde la Pi directamente. El repo está clonado en la Pi en `~/nubeultima` (deploy key).

<details>
<summary>Tareas 1.1–1.4 originales (laptop + Vagrant/VirtualBox) — archivadas</summary>

### Tarea 1.1: Vagrantfile con las 3 VMs e IPs estáticas

**Objetivo:** `vagrant up` construye 3 VMs Ubuntu con IPs estáticas en la red host-only.

**Archivos:** crear `infra/Vagrantfile`.

- [ ] **Paso 1:** Escribir el `Vagrantfile`:

```ruby
# infra/Vagrantfile
# Define el "centro de datos": 3 VMs independientes en una red host-only con IPs estáticas.
Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-24.04"
  config.vm.boot_timeout = 600

  nodes = {
    "datacenter-control" => { ip: "192.168.56.11", cpus: 2, mem: 3072 },
    "datacenter-worker"  => { ip: "192.168.56.12", cpus: 2, mem: 3072 },
    "datacenter-storage" => { ip: "192.168.56.13", cpus: 2, mem: 2048 },
  }

  nodes.each do |name, opts|
    config.vm.define name do |node|
      node.vm.hostname = name
      # Interfaz 2: red host-only con IP ESTÁTICA (lo exige la rúbrica)
      node.vm.network "private_network", ip: opts[:ip], netmask: "255.255.255.0"
      node.vm.provider "virtualbox" do |vb|
        vb.name   = name
        vb.cpus   = opts[:cpus]
        vb.memory = opts[:mem]
        vb.customize ["modifyvm", :id, "--groups", "/NubeUltima"]
      end
    end
  end
end
```

- [x] **Paso 2:** Verificado: VirtualBox 7.2 permite `192.168.56.0/24` por defecto (rango
  `192.168.56.0/21`), no hizo falta tocar `networks.conf`.
- [x] **Paso 3:** `vagrant up`. **Bloqueo encontrado y resuelto** — ver recuadro abajo.

> ⚠️ **Gotcha resuelto (2026-09-01): el hipervisor de Windows bloqueaba a VirtualBox.**
> El primer `vagrant up` creó las VMs pero **no booteaban** (kernel congelado a los ~8 s).
> Causa raíz en `VBox.log`: `AMD-V is not available` → VirtualBox caía al backend lento NEM.
> Windows 11 tenía activados **Integridad de memoria** (Aislamiento del núcleo) + el
> hipervisor (VBS), que se quedan con AMD-V. Solución (como Administrador, requiere reinicio):
> 1. Seguridad de Windows → Aislamiento del núcleo → **Integridad de memoria: Desactivado**
> 2. `bcdedit /set hypervisorlaunchtype off`
> 3. `dism /online /disable-feature /featurename:VirtualMachinePlatform /norestart`
> 4. `dism /online /disable-feature /featurename:HypervisorPlatform /norestart`
> 5. Reiniciar. Verificar: `Get-CimInstance Win32_ComputerSystem` → `HypervisorPresent: False`
>
> **Costo:** WSL2, Docker Desktop y Windows Sandbox dejan de funcionar hasta revertirlo.
> Para el proyecto no importa (Docker corre dentro de las VMs). Va a la sección de
> Implementación/Limitaciones del informe.

**Verificación (hecha 2026-09-01, tras el fix):**
```
vagrant status  ->  las 3 en "running"
control:  eth1 = 192.168.56.11    worker: eth1 = 192.168.56.12    storage: eth1 = 192.168.56.13
hostnames correctos; ping bidireccional entre las 3, 0% pérdida, <1 ms
La interfaz host-only se llama eth1 (importante para --flannel-iface en la Tarea 2.1).
```

**Para entender y explicar:** cada VM tiene 2 tarjetas de red virtuales. La primera (NAT) le
da internet de salida. La segunda (host-only) es una red privada entre las VMs y la laptop,
como un switch aislado; ahí les ponemos las IPs fijas. `private_network ip:` hace que
Vagrant escriba la configuración estática dentro del Ubuntu (en netplan), no por DHCP.

- [x] **Paso 4: Commit** — hecho (`feat(infra): 3 VMs con IPs estaticas...`, commit en `main`).

---

### Tarea 1.2: Playbook `common` — hostnames, paquetes, SSH por llave

**Objetivo:** configuración base idéntica y reproducible en las 3 VMs vía Ansible.

**Archivos:** crear `infra/ansible/common.yml`; modificar `infra/Vagrantfile` (añadir provisioner).

- [ ] **Paso 1:** Añadir al `Vagrantfile`, dentro del bloque `config.vm.define`:

```ruby
      node.vm.provision "ansible_local" do |a|
        a.playbook = "ansible/common.yml"
        a.install  = true
      end
```

- [ ] **Paso 2:** Escribir `infra/ansible/common.yml`:

```yaml
---
# Configuración base de las 3 VMs del centro de datos.
- hosts: all
  become: true
  tasks:
    - name: Instalar utilidades de red y diagnóstico
      apt:
        name: [iperf3, net-tools, curl, jq, chrony]
        update_cache: true

    - name: Registrar los nombres de las VMs en /etc/hosts (resolución interna)
      blockinfile:
        path: /etc/hosts
        block: |
          192.168.56.11 datacenter-control
          192.168.56.12 datacenter-worker
          192.168.56.13 datacenter-storage

    - name: SSH solo por llave (deshabilitar contraseña)
      lineinfile:
        path: /etc/ssh/sshd_config
        regexp: '^#?PasswordAuthentication'
        line: 'PasswordAuthentication no'
      notify: reiniciar ssh

  handlers:
    - name: reiniciar ssh
      service: { name: ssh, state: restarted }
```

- [x] **Paso 3:** `vagrant provision` — hecho. `ok=7 changed=3 failed=0` en las 3 VMs.

> **Gotcha resuelto (SSH):** `PasswordAuthentication no` en un `99-*.conf` NO tomaba efecto.
> `sshd` usa el **primer** valor que encuentra por opción, y `50-cloud-init.conf` (con
> `PasswordAuthentication yes`) se lee antes. Solución: nombrar nuestro drop-in
> `00-nubeultima-hardening.conf` para que gane. El `common.yml` real refleja esto y también
> añade `chrony` (sincronización de hora, necesaria para TLS y K8s).

**Verificación (hecha 2026-09-01):**
```
getent hosts datacenter-worker          -> 192.168.56.12   (resolucion por nombre OK)
sudo sshd -T | grep passwordauth        -> passwordauthentication no   (en las 3)
                                           permitrootlogin no
command -v iperf3 jq htop                -> instalados
timedatectl / systemctl is-active chrony -> NTPSynchronized=yes, chrony active
```
Nota didáctica: al re-correr `vagrant provision`, las tareas de paquetes/hora/hosts
salieron `ok` (no `changed`) — eso es **idempotencia**: Ansible solo cambia lo que falta.

**Para entender y explicar:** Ansible es **automatización declarativa**: describís el
*estado deseado* ("el paquete iperf3 debe estar instalado") y Ansible lo hace realidad, sin
importar el estado previo. `ansible_local` lo corre *dentro* de cada VM, así no hay que
instalar Ansible en Windows. El archivo `/etc/hosts` nos deja usar nombres en vez de IPs en
comandos, aunque el direccionamiento sigue siendo 100% estático.

- [x] **Paso 4: Commit** — hecho (`feat(infra): playbook common.yml...` en `main`).

---

### Tarea 1.3: Prueba de conectividad bidireccional (ping + iperf3)

**Objetivo:** un script que demuestra comunicación estable entre las 3 VMs y produce una
tabla para el informe.

**Archivos:** crear `pruebas/conectividad.sh`.

- [ ] **Paso 1:** Escribir `pruebas/conectividad.sh`:

```bash
#!/usr/bin/env bash
# Matriz de conectividad del centro de datos: latencia (ping) y ancho de banda/jitter (iperf3).
set -euo pipefail
NODES=("192.168.56.11" "192.168.56.12" "192.168.56.13")
NAMES=("control" "worker" "storage")

echo "=== PING (10 paquetes, ida y vuelta) ==="
for i in "${!NODES[@]}"; do
  for j in "${!NODES[@]}"; do
    [ "$i" = "$j" ] && continue
    avg=$(ping -c 10 -q "${NODES[$j]}" | awk -F'/' '/rtt|round-trip/ {print $5" ms"}')
    echo "${NAMES[$i]} -> ${NAMES[$j]}: ${avg:-SIN RESPUESTA}"
  done
done

echo; echo "=== IPERF3 (TCP 10s + UDP para jitter) ==="
# Requiere: en cada destino, 'iperf3 -s -D' corriendo (lo lanza este script por ssh).
```

- [x] **Paso 2:** Implementación real: el script corre **desde el host** (Git Bash) y orquesta
  todo por `vagrant ssh` — arranca/apaga los `iperf3 -s -D` él mismo, no hace falta un
  servicio systemd ni SSH entre VMs.
- [x] **Paso 3:** `bash pruebas/conectividad.sh` desde la raíz del repo. Guarda la salida en
  `pruebas/resultado-conectividad.txt`.

**Verificación (hecha 2026-09-01):** matriz completa de los 6 sentidos —
```
ping:        0% packet loss,  RTT ~0.38-0.44 ms   (los 6)
iperf3 TCP:  ~3.2-3.4 Gbits/sec                    (los 6)
iperf3 UDP:  jitter 0.017-0.048 ms, sin perdida    (los 6)
```
Muy por encima del umbral (<5 ms, >500 Mbps). Sin errores.

**Para entender y explicar:** "comunicación bidireccional estable" (rúbrica) significa que
cualquier VM alcanza a cualquier otra, en los dos sentidos, de forma consistente. `ping`
mide **latencia**; `iperf3` mide **ancho de banda** y **jitter** (variación de latencia).
Presentamos esta tabla como un mini-**SLA interno** del centro de datos, que enlaza con la
semana de QoS/SLA del curso.

- [x] **Paso 4: Commit** — hecho (`test(infra): script de conectividad...` en `main`).
  Además se agregó `.gitattributes` para forzar LF en scripts/config (si no, fallan al
  clonar en otra máquina: `bad interpreter: /bin/bash^M`).

---

### Tarea 1.4: Hito 1 — reconstrucción limpia

**Objetivo:** demostrar que todo el centro de datos se reconstruye desde cero sin tocar nada
a mano.

- [x] **Paso 1:** `vagrant destroy -f && vagrant up` — hecho 2026-09-01. Tiempos:
  destruir 20 s · crear+bootear+provisionar las 3 = **8 min 16 s**. `failed=0` en las 3.
- [x] **Paso 2:** `pruebas/conectividad.sh` re-ejecutado → mismo resultado: 0% pérdida en los
  6 sentidos, RTT ~0.3 ms, iperf3 TCP ~4.6-5.5 Gbits/s, jitter <0.03 ms.
- [ ] **Paso 3:** _(Video pendiente — el usuario lo grabará si el profe lo pide.)_

**Verificación:** ✅ el ciclo `destroy` + `up` + prueba de conectividad pasó sin intervención
manual. **FASE 1 (IaaS) COMPLETA.**

**Para entender y explicar:** esta es la prueba de fuego de la Infraestructura como Código:
si se puede destruir y recrear con un comando, la infraestructura es *reproducible* y
*desechable* (como los contenedores de la presentación 3: "un contenedor nace para morir").
Cualquiera del grupo puede levantar el proyecto idéntico en su máquina.

</details>

---

# FASE 2 — PaaS + Aplicación + SaaS

> ## Reescrita 2026-09-09 para Raspberry Pi + K3s + ARM64
>
> Orquestador confirmado: **K3s** (Kubernetes ligero). Las tareas 2.1–2.4 de abajo
> (K3s sobre Vagrant/x86) son referencia. La Fase 2 real:
>
> | Paso | Qué | Archivo | Nota |
> |---|---|---|---|
> | **2a** | Re-dimensionar las VMs para K3s (control 1400 MB, worker 1200 MB, storage 512 MB) y recrear | `infra/kvm/vms.conf` | Ajuste a 4 GB. Vigilar RAM/zram de cerca |
> | **2b** | Instalar **K3s server** en `nubeultima-control` (`--disable traefik --disable metrics-server --flannel-iface enp1s0 --node-ip 192.168.100.11`) | `infra/ansible/k3s-server.yml` | El "cerebro" del clúster |
> | **2c** | Unir `nubeultima-worker` como **K3s agent** | `infra/ansible/k3s-agent.yml` | El "músculo" |
> | **2d** | `kubectl` desde la Pi (kubeconfig con `server: https://192.168.100.11:6443`) · namespaces | `infra/k3s/` | `kubectl get nodes` → 2 Ready |
> | **2e** | Escribir los 3 microservicios en Python: `device-simulator`, `ingestion-api` (FastAPI + SQLite + reglas de anomalía), `dashboard` (SaaS) | `plataforma/`, `saas/` | Probar en local con `docker compose` primero |
> | **2f** | Broker MQTT (Mosquitto). Base de datos = **SQLite** dentro del `ingestion-api` (no InfluxDB) | `plataforma/k8s/` | |
> | **2g** | Construir las imágenes **ARM64** en la Pi · publicarlas en Docker Hub (cuenta del grupo) | `plataforma/*/Dockerfile` | `docker buildx` o build nativo en la Pi |
> | **2h** | Desplegar todo en K3s (`kubectl apply -f plataforma/k8s/`) · Ingress simple (nginx o NodePort) | `plataforma/k8s/` | |
> | **2i** | Reenvío de puertos en la Pi (`nftables`): laptop → `nubeultima:8080` → panel SaaS de la VM | `infra/pi-host/` | Para ver el panel desde el navegador de la laptop |
> | **2j** | Verificar de punta a punta: simulador → MQTT → ingestión → SQLite → panel con datos y alertas | | |
>
> **Plan B (si la Pi de 4 GB no aguanta K3s en la demo):** cambiar a **Docker Swarm** — los
> Dockerfiles y el `docker-compose.yml` de desarrollo se reutilizan, solo cambian los
> manifiestos por un `docker-stack.yml`.
>
> **Recordatorio:** preguntar al profe si se puede usar una Pi de 8 GB (haría K3s cómodo).

<details>
<summary>Tareas 2.1–2.4 originales (K3s sobre Vagrant/x86) — referencia</summary>

### Tarea 2.1: Instalar K3s server en VM1

**Objetivo:** el plano de control de Kubernetes corriendo en `datacenter-control`.

**Archivos:** crear `infra/ansible/k3s-server.yml`; modificar `Vagrantfile` (provisioner solo para esa VM).

- [ ] **Paso 1:** Escribir `infra/ansible/k3s-server.yml`:

```yaml
---
- hosts: all
  become: true
  vars:
    host_only_iface: eth1   # verificar con 'ip a'; puede ser enp0s8
  tasks:
    - name: Instalar K3s server (fijado a la interfaz host-only)
      shell: |
        curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
          --node-ip 192.168.56.11 \
          --flannel-iface {{ host_only_iface }} \
          --tls-san 192.168.56.11 \
          --write-kubeconfig-mode 644 \
          --disable traefik=false" sh -
      args: { creates: /usr/local/bin/k3s }

    - name: Copiar kubeconfig al synced folder para usarlo desde el host
      copy:
        src: /etc/rancher/k3s/k3s.yaml
        dest: /vagrant/kubeconfig/k3s.yaml
        remote_src: true
```

- [ ] **Paso 2:** En el `Vagrantfile`, añadir este provisioner **solo** al nodo `datacenter-control`.
- [ ] **Paso 3:** `vagrant provision datacenter-control`
- [ ] **Paso 4:** En el host: copiar `infra/kubeconfig/k3s.yaml`, editar la línea `server:`
  para que diga `https://192.168.56.11:6443`, y exportar `KUBECONFIG` a esa ruta.

**Verificación:**
```bash
kubectl get nodes          # datacenter-control  Ready  control-plane,master
kubectl get pods -A        # coredns, metrics-server, traefik, local-path en Running
```

**Para entender y explicar:** K3s es Kubernetes **certificado por la CNCF** pero empaquetado
en un solo binario liviano, pensado para el borde (edge) y sitios con pocos recursos. El
*server* es el "cerebro" (plano de control) de la presentación 4: guarda el estado deseado
del clúster y toma decisiones. `--flannel-iface eth1` es crítico: le dice a la red del
clúster que use la interfaz host-only y no la NAT.

- [ ] **Paso 5: Commit:**
```bash
git add infra/ && git commit -m "feat(paas): K3s server en VM control"
```

---

### Tarea 2.2: Unir VM2 como agente del clúster

**Objetivo:** `datacenter-worker` ejecutando cargas de trabajo dentro del clúster.

**Archivos:** crear `infra/ansible/k3s-agent.yml`.

- [ ] **Paso 1:** Obtener el token: `vagrant ssh datacenter-control -c "sudo cat /var/lib/rancher/k3s/server/node-token"`.
- [ ] **Paso 2:** Escribir `infra/ansible/k3s-agent.yml` (pasando `K3S_URL=https://192.168.56.11:6443`, `K3S_TOKEN`, `--node-ip 192.168.56.12`, `--flannel-iface eth1`). El token se puede leer por SSH desde la VM control dentro del playbook.
- [ ] **Paso 3:** Añadir el provisioner solo al nodo `datacenter-worker`. `vagrant provision datacenter-worker`.

**Verificación:**
```bash
kubectl get nodes -o wide    # 2 nodos Ready; INTERNAL-IP = .11 y .12 (NO 10.0.2.15)
```

**Para entender y explicar:** el *agent* (o worker) es el "músculo": no toma decisiones,
solo ejecuta los contenedores que el server le asigna. Que las INTERNAL-IP sean las de la
red host-only confirma que el gotcha de las 2 interfaces está resuelto.

- [ ] **Paso 4: Commit:**
```bash
git add infra/ && git commit -m "feat(paas): VM worker unida al clúster K3s"
```

---

### Tarea 2.3: Namespaces, Helm y una carga de prueba

**Objetivo:** separar el clúster en zonas lógicas y confirmar que el ingress publica
servicios al navegador del host.

**Archivos:** crear `plataforma/k8s/00-namespaces.yaml`.

- [ ] **Paso 1:** Escribir `00-namespaces.yaml` con los namespaces `plataforma`, `monitoreo`, `backup`. `kubectl apply -f`.
- [ ] **Paso 2:** Desplegar una prueba: `kubectl create deploy web --image=nginx -n plataforma`
  + un `Service` + un `Ingress` de Traefik con host `datacenter-control`.
- [ ] **Paso 3:** En el host, editar `C:\Windows\System32\drivers\etc\hosts` añadiendo
  `192.168.56.11 datacenter-control nubeultima.local`.

**Verificación:** abrir `http://datacenter-control/` en el navegador del host → página de nginx.

**Para entender y explicar:** los **namespaces** son divisiones lógicas del clúster (como
carpetas), útiles para aplicar seguridad y límites por separado. El **Ingress** + **Traefik**
es la "puerta de entrada" HTTP: enruta según el nombre/ruta hacia el servicio interno
correcto. Que se vea desde el navegador del host demuestra el camino completo host → red
host-only → ingress → pod.

- [ ] **Paso 4:** Borrar la carga de prueba. **Commit:**
```bash
git add plataforma/k8s/ && git commit -m "feat(paas): namespaces + verificacion de ingress"
```

---

### Tarea 2.4: Hito 2

**Verificación combinada:** `vagrant destroy -f && vagrant up` reconstruye el clúster de 2
nodos automáticamente y el ingress responde desde el host. Capturas de `kubectl get nodes`
y del navegador.

</details>

---

# FASE 3 (vieja) — La aplicación (microservicios propios)

> Fusionada dentro de la nueva Fase 2 (pasos 2e–2j). Se mantiene abajo como referencia
> del código de los microservicios.

*Responsable principal: integrante 3 (Aplicación). Se desarrolla y prueba localmente con
`docker-compose` antes de llevarlo al clúster.*

### Tarea 3.1: `device-simulator` — patrones de telemetría (TDD)

**Objetivo:** una función pura que genera lecturas realistas, con tests.

**Archivos:** crear `plataforma/device-simulator/patterns.py`, `tests/test_patterns.py`, `requirements.txt`.

- [ ] **Paso 1: Test que falla** — `tests/test_patterns.py`:

```python
from datetime import datetime
from patterns import daily_consumption, inject_anomaly

def test_consumo_mayor_de_dia_que_de_noche():
    dia   = daily_consumption(base=1.0, hour=14)
    noche = daily_consumption(base=1.0, hour=3)
    assert dia > noche

def test_fuga_de_agua_mantiene_flujo_en_madrugada():
    normal = inject_anomaly({"tipo": "agua", "valor": 0.0, "hour": 3}, kind="fuga")
    assert normal["valor"] > 0.0
```

- [ ] **Paso 2:** `cd plataforma/device-simulator && python -m pytest -v` → FALLA (no existe `patterns`).
- [ ] **Paso 3:** Implementar `patterns.py`: `daily_consumption` (curva senoidal centrada en
  las 14 h + ruido gaussiano), `inject_anomaly` (para `fuga`: fuerza `valor` a un flujo bajo
  constante; para `pico`: multiplica; para `contaminacion`: sube PM2.5/CO2).
- [ ] **Paso 4:** `python -m pytest -v` → PASA.
- [ ] **Paso 5: Commit:**
```bash
git add plataforma/device-simulator/ && git commit -m "feat(app): patrones de telemetria del simulador con tests"
```

**Para entender y explicar:** *TDD* (desarrollo guiado por pruebas): primero se escribe la
prueba de lo que debe pasar, se la ve fallar, y recién entonces se escribe el código mínimo
para que pase. Da confianza de que cada pieza hace lo que dice. El simulador representa los
dispositivos NB-IoT/LoRaWAN de la última milla que no tenemos físicamente.

---

### Tarea 3.2: `device-simulator` — publicación MQTT

**Objetivo:** el simulador publica lecturas en el broker.

**Archivos:** crear `plataforma/device-simulator/simulator.py`, `Dockerfile`.

- [ ] **Paso 1:** `simulator.py`: lee config de variables de entorno (`MQTT_HOST`, `ZONAS`,
  `DEVICES_POR_ZONA`, `INTERVALO_SEG`), y en bucle publica JSON en
  `ciudad/{zona}/{tipo}/{device_id}` con `{ "ts", "device_id", "zona", "tipo", "valor", "unidad" }`.
- [ ] **Paso 2:** `Dockerfile` (base `python:3.12-slim`, copia, `pip install -r requirements.txt`, `CMD ["python", "simulator.py"]`).
- [ ] **Paso 3:** Prueba local rápida: `docker run --rm eclipse-mosquitto` en una terminal;
  en otra, `mosquitto_sub -h localhost -t 'ciudad/#' -v`; correr el simulador apuntando ahí.

**Verificación:** `mosquitto_sub` muestra un flujo de mensajes JSON con timestamps y valores
que varían de forma realista.

**Para entender y explicar:** **MQTT** es un protocolo de mensajería *publicar/suscribir*
muy liviano, diseñado para redes con poco ancho de banda y dispositivos con poca batería —
por eso es el estándar de facto en IoT. El **broker** (Mosquitto) es el intermediario: los
dispositivos publican en "temas" (topics) y los consumidores se suscriben a los que les
interesan, sin conocerse entre sí.

- [ ] **Paso 4: Commit:**
```bash
git add plataforma/device-simulator/ && git commit -m "feat(app): simulador publica telemetria por MQTT"
```

---

### Tarea 3.3: `ingestion-api` — validación de datos (TDD)

**Objetivo:** esquemas Pydantic que rechazan lecturas malformadas.

**Archivos:** crear `plataforma/ingestion-api/app/models.py`, `tests/test_models.py`.

- [ ] **Paso 1: Test que falla** — `tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError
from app.models import Reading

def test_lectura_valida():
    r = Reading(ts="2026-09-01T14:00:00Z", device_id="luz-z1-001",
                zona="zona-1", tipo="luz", valor=2.4, unidad="kWh")
    assert r.tipo == "luz"

def test_rechaza_tipo_desconocido():
    with pytest.raises(ValidationError):
        Reading(ts="2026-09-01T14:00:00Z", device_id="x", zona="zona-1",
                tipo="plasma", valor=1, unidad="kWh")

def test_rechaza_valor_negativo():
    with pytest.raises(ValidationError):
        Reading(ts="2026-09-01T14:00:00Z", device_id="x", zona="zona-1",
                tipo="agua", valor=-5, unidad="L/min")
```

- [ ] **Paso 2:** `python -m pytest -v` → FALLA.
- [ ] **Paso 3:** Implementar `models.py`: `Reading` con `tipo` como `Literal["luz","agua","aire"]`, `valor >= 0`, `ts` como datetime.
- [ ] **Paso 4:** `python -m pytest -v` → PASA.
- [ ] **Paso 5: Commit:**
```bash
git add plataforma/ingestion-api/ && git commit -m "feat(app): validacion de lecturas con Pydantic"
```

**Para entender y explicar:** la **validación en el borde de entrada** es un principio de
seguridad y robustez: nada entra a la base de datos sin verificarse primero. Pydantic
convierte y valida el JSON en objetos Python tipados; si algo no cuadra, lo rechaza con un
error claro.

---

### Tarea 3.4: `ingestion-api` — consumidor MQTT + escritura en InfluxDB

**Objetivo:** el servicio se suscribe al broker y persiste las lecturas.

**Archivos:** crear `app/mqtt_consumer.py`, `app/influx.py`, `app/main.py`.

- [ ] **Paso 1:** `app/influx.py`: cliente de InfluxDB 2.x (`influxdb-client`), función `write_reading(r: Reading)` que escribe un *point* en el bucket `telemetria` con tags `zona`, `tipo`, `device_id` y field `valor`.
- [ ] **Paso 2:** `app/mqtt_consumer.py`: cliente `paho-mqtt` suscrito a `ciudad/#`; on_message → `Reading(**json)` → `write_reading`. Manejo de reconexión.
- [ ] **Paso 3:** `app/main.py`: app FastAPI que lanza el consumidor MQTT como tarea de fondo en el evento `startup`.
- [ ] **Paso 4:** Añadir InfluxDB y este servicio al `docker-compose.yml`.

**Verificación:** con `docker-compose up`, tras un minuto:
```bash
docker compose exec influxdb influx query 'from(bucket:"telemetria") |> range(start:-5m) |> count()'
```
devuelve filas > 0.

**Para entender y explicar:** **InfluxDB** es una *base de datos de series de tiempo*:
optimizada para datos que son "valor + marca de tiempo" y que se consultan por rangos
("dame el consumo de la última hora"). Es la herramienta natural para telemetría. Un
microservicio con **una sola responsabilidad** (ingerir) es más fácil de entender, probar y
escalar que un monolito que hace todo.

- [ ] **Paso 5: Commit:**
```bash
git add plataforma/ && git commit -m "feat(app): ingestion-api consume MQTT y escribe en InfluxDB"
```

---

### Tarea 3.5: `ingestion-api` — API REST de consulta

**Objetivo:** endpoints para que el panel SaaS lea datos.

**Archivos:** modificar `app/main.py`; crear `tests/test_api.py`.

- [ ] **Paso 1: Tests que fallan** (con `TestClient` de FastAPI) para:
  `GET /health` → 200; `GET /devices` → lista; `GET /readings?zona=zona-1&tipo=luz&since=1h` → serie; `GET /alerts` → lista.
- [ ] **Paso 2:** `python -m pytest -v` → FALLA.
- [ ] **Paso 3:** Implementar los endpoints (consultas Flux a InfluxDB, o datos de prueba si InfluxDB no está en el entorno de test — usar dependency injection para poder mockear).
- [ ] **Paso 4:** `python -m pytest -v` → PASA.
- [ ] **Paso 5: Commit:**
```bash
git add plataforma/ingestion-api/ && git commit -m "feat(app): API REST de consulta de telemetria y alertas"
```

**Para entender y explicar:** una **API REST** es un contrato: el frontend pide datos por
URLs (`GET /readings?...`) y recibe JSON, sin saber nada de la base de datos por debajo.
Esto desacopla el panel (SaaS) de la implementación interna — se puede cambiar InfluxDB por
otra cosa sin tocar el frontend.

---

### Tarea 3.6: `anomaly-service` — reglas de detección (TDD)

**Objetivo:** funciones puras que, dada una serie de lecturas, devuelven alertas.

**Archivos:** crear `plataforma/anomaly-service/rules.py`, `tests/test_rules.py`, `service.py`.

- [ ] **Paso 1: Tests que fallan** para:
  - `device_silent(readings, now, max_gap_min=15)` → alerta si el último dato es viejo.
  - `night_water_flow(readings)` → alerta si hay flujo de agua > 0 sostenido entre las 00 h y 05 h (posible fuga).
  - `consumption_spike(readings, history_p95)` → alerta si `valor > history_p95 * 1.5`.
  - `bad_air(readings, pm25_max=35)` → alerta si PM2.5 supera el umbral.
- [ ] **Paso 2:** `python -m pytest -v` → FALLA.
- [ ] **Paso 3:** Implementar `rules.py` (funciones puras: reciben datos, devuelven `list[Alert]`).
- [ ] **Paso 4:** `python -m pytest -v` → PASA.
- [ ] **Paso 5:** `service.py`: cada N minutos consulta `ingestion-api`, aplica las reglas,
  y `POST /alerts` (o escribe directo en InfluxDB measurement `alerts`).
- [ ] **Paso 6: Commit:**
```bash
git add plataforma/anomaly-service/ && git commit -m "feat(app): anomaly-service con reglas de umbral y tests"
```

**Para entender y explicar:** separar las **reglas** (funciones puras, fáciles de probar) del
**servicio** (el bucle que consulta y actúa) es buen diseño: la lógica de negocio se prueba
sin red ni base de datos. Estas reglas son el "valor agregado" de la plataforma: convierten
datos crudos en información accionable para el operador.

---

### Tarea 3.7: Entorno local completo con docker-compose

**Objetivo:** toda la tubería corriendo en la laptop de quien desarrolla, sin K3s.

**Archivos:** completar `plataforma/docker-compose.yml`.

- [ ] **Paso 1:** `docker-compose.yml` con: `mosquitto` (imagen `eclipse-mosquitto`, con
  `mosquitto.conf` y `passwordfile`), `influxdb` (imagen `influxdb:2.7`), `ingestion-api`,
  `anomaly-service`, `device-simulator` (build local).
- [ ] **Paso 2:** `docker compose up --build`.

**Verificación:** tras 5 min: `curl localhost:8000/readings?zona=zona-1&tipo=luz&since=10m`
devuelve una serie; `curl localhost:8000/alerts` devuelve alguna alerta si el simulador
inyectó una anomalía.

**Para entender y explicar:** `docker-compose` levanta varios contenedores conectados entre
sí con un archivo. Es el "ensayo general" antes de Kubernetes: si la tubería funciona acá,
llevarla al clúster es sobre todo traducir el compose a manifiestos.

- [ ] **Paso 3: Commit:**
```bash
git add plataforma/docker-compose.yml plataforma/ && git commit -m "feat(app): entorno local completo con docker-compose"
```

---

### Tarea 3.8: Construir y publicar las imágenes

**Objetivo:** las 3 imágenes propias en Docker Hub, listas para el clúster.

- [ ] **Paso 1:** `docker login` con la cuenta del grupo.
- [ ] **Paso 2:** Para cada servicio: `docker build -t <grupo>/nubeultima-<servicio>:0.1.0 .` y `docker push ...`.
- [ ] **Paso 3:** Anotar los nombres exactos de las imágenes en `plataforma/k8s/README.md`.

**Verificación:** las 3 imágenes aparecen en `https://hub.docker.com/u/<grupo>`.

- [ ] **Paso 4: Commit:**
```bash
git add plataforma/ && git commit -m "build(app): imagenes 0.1.0 publicadas en Docker Hub"
```

---

### Tarea 3.9: Desplegar la plataforma en K3s

**Objetivo:** los microservicios corriendo como pods en el namespace `plataforma`.

**Archivos:** crear `plataforma/k8s/10-mosquitto.yaml`, `11-influxdb.yaml`, `20-ingestion-api.yaml`, `21-anomaly-service.yaml`, `22-device-simulator.yaml`.

- [ ] **Paso 1:** `11-influxdb.yaml`: Deployment + Service + `PersistentVolumeClaim` (usa el `local-path` provisioner que trae K3s) + Secret con token/org/bucket.
- [ ] **Paso 2:** `10-mosquitto.yaml`: Deployment + Service + ConfigMap (`mosquitto.conf`) + Secret (`passwordfile`).
- [ ] **Paso 3:** `20/21/22-*.yaml`: Deployment + Service para cada microservicio propio, con las variables de entorno apuntando a los Services internos (`mqtt-broker`, `influxdb`).
- [ ] **Paso 4:** `kubectl apply -f plataforma/k8s/`.

**Verificación:**
```bash
kubectl -n plataforma get pods           # todos Running
kubectl -n plataforma logs deploy/ingestion-api | grep -i "written"
kubectl -n plataforma exec deploy/influxdb -- influx query 'from(bucket:"telemetria")|>range(start:-5m)|>count()'
```

**Para entender y explicar:** un **Deployment** le dice a Kubernetes "quiero N copias de este
contenedor corriendo siempre"; si una se cae, el clúster la reemplaza sola (*self-healing*,
presentación 3). Un **Service** es un nombre y una IP estable interna para llegar a esos
pods aunque cambien. El **PVC** es almacenamiento que sobrevive aunque el pod muera —
esencial para la base de datos.

- [ ] **Paso 5: Commit:**
```bash
git add plataforma/k8s/ && git commit -m "feat(paas): plataforma de microservicios desplegada en K3s"
```

---

### Tarea 3.10: Hito 3

**Verificación:** telemetría fluyendo de punta a punta *dentro del clúster*; InfluxDB
acumulando datos; alertas generándose. Capturas de `kubectl get pods` y de una consulta con
datos.

---

# FASE 4 — SaaS: el panel del operador

*Responsable principal: integrante 3, con apoyo del 2 para el ingress.*

### Tarea 4.1: Frontend del panel

**Objetivo:** una web simple que muestra estado de zonas, dispositivos y alertas en vivo.

**Archivos:** crear `saas/dashboard/app/main.py`, `templates/index.html`, `static/app.js`.

- [ ] **Paso 1:** `main.py`: FastAPI que sirve `index.html` y hace de *proxy* a `ingestion-api` (para evitar problemas de CORS): `/api/readings`, `/api/alerts`, `/api/devices`.
- [ ] **Paso 2:** `index.html` + `app.js`: 
  - una grilla SVG de 4 zonas que cambia de color según haya alertas,
  - tabla de dispositivos con última lectura y estado (online/silencioso),
  - lista de alertas activas,
  - refresco cada 10 s con `fetch`.
- [ ] **Paso 3:** Probar local: `uvicorn app.main:app` apuntando al `ingestion-api` del compose.

**Verificación:** en el navegador se ve el mapa de zonas y los datos se actualizan solos;
al inyectar una anomalía en el simulador, aparece la alerta y la zona cambia de color.

**Para entender y explicar:** esto es el **SaaS**: el operador municipal abre una URL y usa
la aplicación, sin instalar nada, sin saber que debajo hay VMs, Kubernetes, un broker MQTT
y una base de series de tiempo. "Consumo directo y cero mantenimiento" (presentación 2).

- [ ] **Paso 4: Commit:**
```bash
git add saas/ && git commit -m "feat(saas): panel del operador con estado de zonas y alertas"
```

---

### Tarea 4.2: Contenerizar y publicar el panel vía Ingress

**Objetivo:** el panel accesible desde el navegador del host en la raíz del sitio.

**Archivos:** crear `saas/dashboard/Dockerfile`, `saas/dashboard/k8s/40-dashboard.yaml`, `plataforma/k8s/30-ingress.yaml`.

- [ ] **Paso 1:** `Dockerfile`, build y push como `<grupo>/nubeultima-dashboard:0.1.0`.
- [ ] **Paso 2:** `40-dashboard.yaml`: Deployment + Service.
- [ ] **Paso 3:** `30-ingress.yaml`: reglas de Traefik →
  `/` → dashboard, `/api` → ingestion-api, `/grafana` → grafana (se añade en Fase 5).
- [ ] **Paso 4:** `kubectl apply -f`.

**Verificación:** `http://datacenter-control/` desde el host muestra el panel con datos en
vivo. Que otro integrante lo abra desde su navegador (con la entrada en su archivo `hosts`).

- [ ] **Paso 5: Commit:**
```bash
git add saas/ plataforma/k8s/30-ingress.yaml && git commit -m "feat(saas): panel publicado via Ingress"
```

---

### Tarea 4.3: Hito 4

**Verificación:** una persona ajena al desarrollo abre el navegador y usa el panel:
ve zonas, dispositivos, consumo y alertas en tiempo real. Capturas + video corto.

---

# FASE 5 — Monitoreo del hardware

*Responsable principal: integrante 4.*

### Tarea 5.1: `node_exporter` en las 3 VMs

**Objetivo:** exponer métricas de CPU/RAM/disco/red de cada VM.

**Archivos:** modificar `infra/ansible/common.yml`.

- [ ] **Paso 1:** Añadir a `common.yml` una tarea que descargue `node_exporter` (release
  oficial de `https://github.com/prometheus/node_exporter/releases`), lo instale como
  servicio systemd y lo deje escuchando en `:9100`.
- [ ] **Paso 2:** `vagrant provision`.

**Verificación:** `curl http://192.168.56.13:9100/metrics` desde otra VM devuelve métricas.

**Para entender y explicar:** `node_exporter` es un pequeño agente que traduce el estado del
sistema operativo (uso de CPU, memoria libre, I/O de disco…) a un formato que Prometheus
entiende. Lo ponemos también en VM3 aunque no esté en el clúster, porque la rúbrica pide
monitorear **el HW de las 3 VMs**.

- [ ] **Paso 3: Commit:**
```bash
git add infra/ansible/common.yml && git commit -m "feat(monitoreo): node_exporter en las 3 VMs"
```

---

### Tarea 5.2: kube-prometheus-stack vía Helm

**Objetivo:** Prometheus + Grafana + Alertmanager corriendo en el namespace `monitoreo`.

**Archivos:** crear `monitoreo/values-kube-prometheus.yaml`.

- [ ] **Paso 1:** `helm repo add prometheus-community https://prometheus-community.github.io/helm-charts && helm repo update`.
- [ ] **Paso 2:** `values-kube-prometheus.yaml`: 
  - `grafana.grafana.ini.server.root_url` y `serve_from_sub_path` para servir bajo `/grafana`,
  - `prometheus.prometheusSpec.additionalScrapeConfigs` con un job `nodes-vm` que scrapea
    `192.168.56.11:9100`, `.12:9100`, `.13:9100`,
  - recursos recortados (esto corre en 16 GB de RAM).
- [ ] **Paso 3:** `helm install monitoreo prometheus-community/kube-prometheus-stack -n monitoreo -f monitoreo/values-kube-prometheus.yaml`.

**Verificación:**
```bash
kubectl -n monitoreo get pods            # prometheus, grafana, alertmanager Running
# En Prometheus (targets): los 3 node_exporter en estado UP
```

**Para entender y explicar:** un **chart de Helm** es un paquete parametrizable de recursos
de Kubernetes — en vez de escribir 20 manifiestos a mano para montar Prometheus, se instala
un chart probado por la comunidad y se ajusta con un archivo `values`. `kube-prometheus-stack`
es el estándar de facto para monitoreo en Kubernetes.

- [ ] **Paso 4: Commit:**
```bash
git add monitoreo/ && git commit -m "feat(monitoreo): kube-prometheus-stack con scrape de las 3 VMs"
```

---

### Tarea 5.3: Dashboard de HW de las 3 VMs

**Objetivo:** un tablero de Grafana que compara el consumo de las 3 VMs.

**Archivos:** crear `monitoreo/dashboards/hw-3vms.json`.

- [ ] **Paso 1:** En Grafana (`http://datacenter-control/grafana`, credenciales del `values`),
  importar el dashboard comunitario **"Node Exporter Full"** (ID 1860).
- [ ] **Paso 2:** Crear un dashboard propio `NubeÚltima — HW 3 VMs` con paneles: CPU %, RAM
  usada, disco usado y tráfico de red, cada uno con una serie por VM (`instance`).
- [ ] **Paso 3:** Exportar su JSON a `monitoreo/dashboards/hw-3vms.json` y añadirlo como
  ConfigMap con la etiqueta `grafana_dashboard: "1"` para que se cargue solo al reconstruir.

**Verificación:** el dashboard muestra 3 series por panel, una por VM, con datos en vivo.

- [ ] **Paso 4: Commit:**
```bash
git add monitoreo/ && git commit -m "feat(monitoreo): dashboard de HW de las 3 VMs"
```

---

### Tarea 5.4: Capturas en reposo y bajo carga

**Objetivo:** evidencia de "eficiencia y consumo" (rúbrica).

**Archivos:** crear `pruebas/carga-mqtt.py`.

- [ ] **Paso 1:** `carga-mqtt.py`: publica miles de mensajes MQTT por segundo durante 5 min
  (sube el número de dispositivos simulados y baja el intervalo).
- [ ] **Paso 2:** Captura del dashboard **en reposo** (sistema estable).
- [ ] **Paso 3:** Correr `carga-mqtt.py`; captura del dashboard **bajo carga** (se ve subir
  CPU en VM2, quizás I/O de disco en la VM de InfluxDB).
- [ ] **Paso 4:** Anotar en `pruebas/` las cifras antes/durante/después.

**Verificación:** hay 2 juegos de capturas con diferencia visible y una tabla de números.

**Para entender y explicar:** medir el sistema en reposo y bajo carga muestra cómo la
plataforma **escala** y dónde está el cuello de botella. Es lo que un ingeniero de infra
hace para dimensionar recursos (CAPEX vs OPEX, presentaciones 1 y 4).

- [ ] **Paso 5: Commit:**
```bash
git add pruebas/ && git commit -m "test(monitoreo): prueba de carga y capturas de consumo"
```

---

# FASE 6 — BaaS: respaldo como servicio (puntos extra)

*Responsable principal: integrante 4.*

### Tarea 6.1: MinIO en VM3

**Objetivo:** un almacenamiento S3-compatible que será el destino de todos los respaldos.

**Archivos:** crear `infra/ansible/storage.yml`, `backup/minio/`.

- [ ] **Paso 1:** `storage.yml`: instala el binario oficial de MinIO como servicio systemd
  en `datacenter-storage`, datos en `/data/minio`, consola en `:9001`, API en `:9000`.
  Credenciales root en variables (no en el repo).
- [ ] **Paso 2:** Provisioner solo para `datacenter-storage`. `vagrant provision datacenter-storage`.
- [ ] **Paso 3:** Con el cliente `mc` (o la consola web), crear los buckets `velero` y `restic` y un usuario de servicio con acceso solo a esos buckets.

**Verificación:** `http://192.168.56.13:9001` abre la consola; los 2 buckets existen.

**Para entender y explicar:** **MinIO** habla el mismo protocolo que Amazon S3, así que
cualquier herramienta que sepa "hablar S3" (y son casi todas) puede guardar ahí sus
respaldos. VM3 es el "servicio de respaldo portador" que pide la rúbrica: un servicio
dedicado que las demás VMs consumen por API.

- [ ] **Paso 4: Commit:**
```bash
git add infra/ansible/storage.yml backup/minio/ && git commit -m "feat(baas): MinIO en VM storage como destino de respaldos"
```

---

### Tarea 6.2: Velero — respaldo del clúster hacia MinIO

**Objetivo:** respaldos programados del namespace `plataforma` (recursos + datos de disco).

**Archivos:** crear `backup/velero/install.md`, `backup/velero/schedule.yaml`.

- [ ] **Paso 1:** Instalar el CLI de Velero (`https://github.com/vmware-tanzu/velero/releases`).
- [ ] **Paso 2:** `velero install --provider aws --plugins velero/velero-plugin-for-aws:v1.10.0
  --bucket velero --use-node-agent --secret-file ./credentials-minio
  --backup-location-config region=minio,s3ForcePathStyle=true,s3Url=http://192.168.56.13:9000`.
- [ ] **Paso 3:** `schedule.yaml`: un `Schedule` de Velero que respalda `plataforma` cada día
  a las 02:00, con retención de 7 días, incluyendo los volúmenes (node-agent).
- [ ] **Paso 4:** Forzar un respaldo manual: `velero backup create prueba-1 --include-namespaces plataforma --wait`.

**Verificación:**
```bash
velero backup describe prueba-1        # Phase: Completed
# En la consola de MinIO, el bucket 'velero' tiene objetos.
```

**Para entender y explicar:** **Velero** es *la* herramienta de "backup as a service" para
Kubernetes (nació en VMware, hoy es proyecto CNCF). Respalda dos cosas: la **definición** de
los recursos (los YAML que describen deployments, services…) y el **contenido de los
volúmenes** (los datos de InfluxDB). Con eso se puede reconstruir la plataforma en otro
clúster.

- [ ] **Paso 5: Commit:**
```bash
git add backup/velero/ && git commit -m "feat(baas): Velero respaldando la plataforma a MinIO"
```

---

### Tarea 6.3: restic — respaldo del estado del clúster (nivel infra)

**Objetivo:** respaldar lo que Velero no cubre: los snapshots de la base de K3s y `/etc/rancher`.

**Archivos:** crear `backup/restic/backup.sh`, `restic-etcd.service`, `restic-etcd.timer`.

- [ ] **Paso 1:** En VM1, configurar K3s para tomar snapshots de su base embebida
  (`--etcd-snapshot-schedule-cron`). 
- [ ] **Paso 2:** `backup.sh`: inicializa (si hace falta) un repositorio restic en
  `s3:http://192.168.56.13:9000/restic`, con contraseña desde un archivo protegido, y hace
  `restic backup /var/lib/rancher/k3s/server/db/snapshots /etc/rancher`.
- [ ] **Paso 3:** `restic-etcd.service` + `.timer` de systemd para correrlo cada 6 h.
  Añadir su instalación al playbook `k3s-server.yml`.

**Verificación:** `restic -r s3:... snapshots` lista al menos un snapshot; `restic check` pasa.

**Para entender y explicar:** **restic** hace respaldos **cifrados**, **deduplicados** e
**incrementales**: solo sube lo que cambió, y en el destino nada se puede leer sin la
contraseña. Cubrimos dos niveles: Velero para la **aplicación**, restic para el **clúster**
en sí. Juntos son un plan de recuperación ante desastres completo.

- [ ] **Paso 4: Commit:**
```bash
git add backup/restic/ infra/ && git commit -m "feat(baas): restic respaldando el estado del cluster K3s"
```

---

### Tarea 6.4: Prueba automática de restauración

**Objetivo:** verificar periódicamente que los respaldos son restaurables (rúbrica:
"verificación de los respaldos").

**Archivos:** crear `backup/restore-test/restore-test-cronjob.yaml`.

- [ ] **Paso 1:** `restore-test-cronjob.yaml`: un `CronJob` semanal que:
  1. hace `velero restore create --from-backup <último> --namespace-mappings plataforma:plataforma-test`,
  2. espera a que los pods estén listos,
  3. consulta InfluxDB restaurada y compara el conteo de registros con un mínimo esperado,
  4. escribe el resultado (`OK` / `FALLO` + fecha) en un ConfigMap `restore-test-status`,
  5. borra el namespace `plataforma-test`.
- [ ] **Paso 2:** Ejecutarlo manualmente una vez (`kubectl create job --from=cronjob/...`).

**Verificación:** el ConfigMap `restore-test-status` queda con `OK` y una fecha reciente;
los logs del job muestran el conteo de registros restaurados.

**Para entender y explicar:** "un respaldo que nunca se probó, no es un respaldo". Esta
prueba automatizada restaura de verdad en un espacio aislado y valida los datos, sin tocar
producción. Es lo que distingue un BaaS serio de "copiar una carpeta".

- [ ] **Paso 3: Commit:**
```bash
git add backup/restore-test/ && git commit -m "feat(baas): CronJob de verificacion de restauracion"
```

---

### Tarea 6.5: Página de estado del BaaS

**Objetivo:** un endpoint que muestra el "SLA" del servicio de respaldo.

**Archivos:** modificar `saas/dashboard/app/main.py`.

- [ ] **Paso 1:** Añadir al panel una vista `/backups` que lee: último backup de Velero
  (`velero backup get` vía API de K8s o parseando el ConfigMap), tamaño, y el contenido del
  ConfigMap `restore-test-status`.
- [ ] **Paso 2:** Mostrar: fecha de la última copia, resultado del último restore-test,
  y un semáforo verde/rojo.

**Verificación:** `http://datacenter-control/backups` muestra datos reales de respaldo.

- [ ] **Paso 3: Commit:**
```bash
git add saas/ && git commit -m "feat(baas): pagina de estado de respaldos (SLA)"
```

---

### Tarea 6.6: Simulacro de desastre documentado

**Objetivo:** demostrar recuperación real ante la pérdida de una VM.

**Archivos:** crear `pruebas/restore-drill.md`.

- [ ] **Paso 1:** Documentar y ejecutar, grabando en video:
  1. Estado inicial: panel funcionando, datos fluyendo.
  2. `vagrant destroy -f datacenter-worker` (se "quema" el nodo worker).
  3. Observar: los pods de `plataforma` quedan `Pending` (no hay dónde correrlos).
  4. `vagrant up datacenter-worker` → el playbook lo re-une al clúster.
  5. Kubernetes reprograma los pods solo; si hubo pérdida de datos, `velero restore`.
  6. Verificar: el panel vuelve a mostrar datos.
- [ ] **Paso 2:** Anotar el tiempo total de recuperación (RTO).

**Verificación:** el video muestra el ciclo completo caída → recuperación; el panel vuelve
a estar operativo.

**Para entender y explicar:** esto pone a prueba de verdad la resiliencia. Muestra dos
mecanismos: el **self-healing** de Kubernetes (reprograma cargas cuando vuelve el nodo) y el
**BaaS** (restaura datos si se perdieron). RTO = cuánto tarda en volver el servicio.

- [ ] **Paso 3: Commit:**
```bash
git add pruebas/restore-drill.md && git commit -m "docs(baas): simulacro de desastre y recuperacion"
```

---

# FASE 7 — Seguridad (proporcionada)

*Responsable: integrante 4 con apoyo del 2.*

### Tarea 7.1: MQTT con TLS y autenticación

- [ ] **Paso 1:** Generar una CA propia y certificados de servidor para Mosquitto (`openssl`).
- [ ] **Paso 2:** Montar los certs como Secret; configurar Mosquitto para `listener 8883` con TLS y `password_file`.
- [ ] **Paso 3:** Actualizar `device-simulator` e `ingestion-api` para conectarse por 8883 con usuario/clave y validando la CA.

**Verificación:** `mosquitto_sub` sin credenciales o sin TLS es rechazado; con credenciales y CA, funciona.

**Para entender y explicar:** en la última milla los dispositivos se autentican para entrar
a la red (la "autenticación silenciosa" de la presentación 1). TLS cifra el tráfico para que
nadie en el medio lea la telemetría ni inyecte lecturas falsas.

- [ ] **Paso 4: Commit:** `git commit -m "feat(sec): MQTT con TLS y autenticacion"`

---

### Tarea 7.2: NetworkPolicies entre namespaces

**Archivos:** crear `plataforma/k8s/01-networkpolicies.yaml`.

- [ ] **Paso 1:** Políticas: `plataforma` solo acepta tráfico de `ingress` y de sí mismo;
  `monitoreo` puede scrapear a todos; `backup` puede leer de `plataforma`. Todo lo demás,
  denegado por defecto.
- [ ] **Paso 2:** `kubectl apply -f`; verificar que la plataforma sigue funcionando.

**Verificación:** un pod de prueba en un namespace no autorizado NO puede conectarse a InfluxDB.

**Para entender y explicar:** **mínimo privilegio / Zero Trust** (presentación 2, semana 12):
por defecto nada puede hablar con nada; se abren solo los caminos necesarios. Reduce el daño
si un componente es comprometido.

- [ ] **Paso 3: Commit:** `git commit -m "feat(sec): NetworkPolicies con deny-by-default"`

---

### Tarea 7.3: Auditoría de secretos y redacción de seguridad

- [ ] **Paso 1:** Verificar que ningún manifiesto tiene credenciales en texto plano (usar
  `Secret` + `.gitignore` para los archivos con valores reales). `git grep -iE "password|token|secret"` para revisar.
- [ ] **Paso 2:** Escribir en `docs/informe/` medio párrafo sobre las medidas: SSH por llave,
  TLS en MQTT, Secrets, NetworkPolicies, cifrado en restic, y el modelo Zero Trust.

- [ ] **Paso 3: Commit:** `git commit -m "docs(sec): auditoria de secretos y seccion de seguridad"`

---

# FASE 8 — Pruebas finales y evidencia

### Tarea 8.1: `deploy-all.sh` y reconstrucción total cronometrada

**Archivos:** crear `scripts/deploy-all.sh`.

- [ ] **Paso 1:** `deploy-all.sh`: aplica en orden `plataforma/k8s/`, instala el chart de
  monitoreo, aplica `backup/`. Idempotente.
- [ ] **Paso 2:** Prueba total desde cero: `vagrant destroy -f && vagrant up && ./scripts/deploy-all.sh`. Cronometrar.
- [ ] **Paso 3:** Correr `pruebas/conectividad.sh` y abrir el panel.

**Verificación:** de "nada" a "plataforma completa funcionando" con 2 comandos, en tiempo
documentado.

- [ ] **Paso 4: Commit:** `git commit -m "feat: script de despliegue completo"`

---

### Tarea 8.2: Checklist de capturas para el informe

**Archivos:** crear `scripts/screenshots.md`.

- [ ] **Paso 1:** Lista de capturas obligatorias, una por ítem de la rúbrica:
  - `vagrant up` construyendo las VMs
  - `ip a` en cada VM mostrando la IP estática
  - salida de `pruebas/conectividad.sh` (tabla ping + iperf3)
  - `kubectl get nodes -o wide` (INTERNAL-IP correctas)
  - `kubectl get pods -A` (todo Running)
  - el panel SaaS con datos en vivo + una alerta
  - Grafana: dashboard de HW en reposo y bajo carga
  - consola de MinIO con los buckets y objetos
  - `velero backup describe` Completed
  - ConfigMap `restore-test-status` en OK
  - video del simulacro de desastre
- [ ] **Paso 2:** Tomar todas las capturas y guardarlas en `docs/informe/capturas/`.

- [ ] **Paso 3: Commit:** `git commit -m "docs: capturas de evidencia para el informe"`

---

### Tarea 8.3: Runbook de la demo

**Archivos:** crear `docs/informe/demo-runbook.md`.

- [ ] **Paso 1:** Guion paso a paso de la presentación (qué comando correr, qué mostrar, en
  qué orden), pensado para 10–15 min. Incluir un "plan B" por si algo falla en vivo
  (capturas y video de respaldo).

- [ ] **Paso 2: Commit:** `git commit -m "docs: runbook de la demostracion"`

---

# FASE 9 — Informe escrito

*Cada integrante redacta su sección; el integrante 4 integra y revisa. Se guarda en
`docs/informe/`.*

Mapear a las 8 secciones del "Esquema Entrega de proyecto":

- [ ] **9.1 Carátula** — nombre (NubeÚltima o el elegido), grupo, carrera, fecha.
- [ ] **9.2 Índice.**
- [ ] **9.3 Introducción** — descripción, objetivos y alcance (reusar sección 1 del documento de diseño).
- [ ] **9.4 Teoría** — conceptos clave: virtualización (hipervisor vs contenedores),
  IaaS/PaaS/SaaS/BaaS, orquestación con Kubernetes, MQTT y series de tiempo, IPs estáticas y
  direccionamiento local, monitoreo, respaldos y DR. Citar las presentaciones del curso y la
  bibliografía (Erl, *Cloud Computing*; docs de Kubernetes/CNCF).
- [ ] **9.5 Diseño** — arquitectura del sistema + el diagrama de bloques del documento de
  diseño (redibujarlo prolijo, p. ej. en draw.io).
- [ ] **9.6 Implementación** — 6a componentes de HW (laptop, recursos por VM), 6b software
  utilizado (la tabla del stack), 6c proceso con capturas (resumen de las fases de este plan).
- [ ] **9.7 Resultado** — qué quedó funcionando, con las capturas y las tablas de conectividad
  y de consumo; estado de cada ítem de la rúbrica.
- [ ] **9.8 Conclusiones** — 8a resumen de resultados, 8b limitaciones (1 laptop, sin HA real,
  dispositivos simulados), 8c análisis en sus propias palabras (qué aprendieron, qué cambiarían).

- [ ] **Commit final:** `git commit -m "docs: informe escrito de entrega Fase 1"`

---

## Auto-revisión del plan (cobertura de la rúbrica)

| Ítem de la rúbrica | Tarea(s) que lo cubren |
|---|---|
| VMs "compilan" | 1.1, 1.4, 8.1 |
| IPs estáticas en red local | 1.1, 1.2 |
| Comunicación bidireccional estable | 1.3, 1.4 |
| 4 servicios corriendo y funcionales | 3.9, 4.2, 5.2, 6.5 |
| Monitorizar el HW utilizado | 5.1–5.4 |
| Acceso exitoso a los servicios | 4.3, 8.2 |
| Verificación de respaldos | 6.4, 6.6 |
| BaaS (puntos extra) | 6.1–6.6 |
| Documento escrito (8 secciones del esquema) | 9.1–9.8 |
| Teoría que sustenta la implementación | 9.4, notas "para entender y explicar" de cada tarea |

## Orden sugerido de trabajo en paralelo (3 semanas)

- **Semana 1:** Fase 0 (todos) → Fase 1 (int. 1) + Fase 3.1–3.7 en local (int. 3) + preparar Fase 5/6 leyendo docs (int. 4) + Fase 2 en cuanto Fase 1 dé el Hito 1 (int. 2).
- **Semana 2:** Fase 2 completa → Fase 3.8–3.10 (int. 2+3) → Fase 4 (int. 3) → Fase 5 (int. 4).
- **Semana 3:** Fase 6 (int. 4) → Fase 7 (int. 4+2) → Fase 8 (todos) → Fase 9 redacción (todos) → ensayo de la demo.
