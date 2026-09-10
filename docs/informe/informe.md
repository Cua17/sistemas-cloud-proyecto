# NubeÚltima — Plataforma Cloud Convergente para Telemetría IoT de Última Milla

> Borrador del informe de entrega. Sigue el "Esquema Entrega de proyecto".
> Los `[[...]]` son notas para el grupo: completar con capturas, cifras y redacción propia.

---

## 1. Carátula

- **Nombre del proyecto:** NubeÚltima — Plataforma Cloud Convergente para Telemetría IoT de Última Milla
- **Grupo:** `[[integrantes]]`
- **Carrera:** Ingeniería en Sistemas y Ciencias de la Computación / Ingeniería en Electrónica y Telecomunicaciones
- **Fecha de entrega:** `[[fecha]]`

## 2. Índice

`[[generar al final]]`

## 3. Introducción

### Descripción del proyecto

Se construye, sobre una **Raspberry Pi 4**, una réplica a pequeña escala del sistema cloud
que un operador de telecomunicaciones usaría para ofrecer un servicio de "ciudad
inteligente". Dispositivos IoT simulados (medidores de luz y agua, sensores de calidad de
aire, repartidos en cuatro zonas de una ciudad) envían telemetría por **MQTT** —el
protocolo real de NB-IoT/LoRaWAN— hacia un centro de datos virtualizado de **tres máquinas
virtuales**. Sobre ellas corre una **plataforma de microservicios orquestada con
Kubernetes** que ingiere los datos, detecta anomalías (fugas, picos de consumo,
contaminación) y los expone a un operador municipal en un **panel web**. En paralelo
funcionan el **monitoreo del hardware** y un **servicio de respaldo automático y
verificable**.

### Objetivos

1. Ejecutar el desacoplamiento de hardware y software mediante virtualización (KVM) y
   contenerización (Kubernetes) en un entorno local.
2. Implementar y diferenciar de forma práctica las capas de servicio **IaaS, PaaS, SaaS** y,
   como extra, **BaaS**.
3. Demostrar comunicación de red bidireccional estable entre las VMs con IPs estáticas.
4. Monitorizar la eficiencia y el consumo de hardware.
5. Verificar la realización y restauración de los respaldos.

### Alcance

- **Incluye:** virtualización local sobre Raspberry Pi, red interna con direccionamiento
  estático, clúster Kubernetes de dos nodos, cuatro microservicios (tres propios en Python
  + broker MQTT), base de datos, panel web, monitoreo con Prometheus, respaldos con MinIO +
  restic, pruebas de conectividad y de restauración, simulacro de desastre.
- **No incluye:** hardware IoT físico, nubes públicas de pago, alta disponibilidad
  multi-sitio, convergencia con equipos reales de última milla (GPON/HFC/5G) — se simula el
  comportamiento con MQTT.

## 4. Teoría

### 4.1 Conceptos clave

**Virtualización y desacople hardware/software.** Un *hipervisor* abstrae el hardware
físico y permite ejecutar varias máquinas virtuales, cada una con su propio sistema
operativo, sobre una sola máquina física. Esto rompe la relación "una aplicación = un
servidor" y habilita consolidación, aislamiento y reproducibilidad. Usamos **KVM**, el
hipervisor nativo del kernel de Linux (tipo 1, integrado en el SO del host).

**Contenerización y orquestación.** Un *contenedor* no virtualiza el hardware sino el
sistema operativo: los procesos comparten el kernel del host pero se ejecutan aislados
(namespaces + cgroups). Es mucho más liviano que una VM. Un *orquestador* (Kubernetes)
gestiona muchos contenedores en varios nodos: los distribuye, los reinicia si fallan
(*self-healing*), maneja la red interna, el escalado y los secretos. Usamos **K3s**,
Kubernetes certificado por la CNCF empaquetado para hardware con pocos recursos.

**Modelos de servicio en la nube.**

| Modelo | Qué provee | En este proyecto |
|---|---|---|
| **IaaS** | Infraestructura (cómputo, red, almacenamiento) | Las 3 VMs KVM |
| **PaaS** | Plataforma para desplegar aplicaciones sin administrar servidores | El clúster K3s |
| **SaaS** | Software listo para usar | El panel del operador |
| **BaaS** | Respaldo como servicio | MinIO + restic |

**MQTT y bases de series de tiempo.** MQTT es un protocolo de mensajería *publicar/suscribir*
liviano, diseñado para redes con poco ancho de banda y dispositivos de bajo consumo — el
estándar de facto en IoT. La telemetría (valor + marca de tiempo) se almacena para consultas
por rango; para la escala de este proyecto se usa **SQLite**.

**Infraestructura como código (IaC).** La infraestructura se describe en archivos de texto
versionados (no se arma a mano): `virt-install` + `cloud-init` para las VMs, playbooks de
**Ansible** para su configuración, manifiestos YAML para Kubernetes. Se puede destruir y
recrear todo con un comando.

**Monitoreo.** *node_exporter* traduce el estado del sistema operativo (CPU, RAM, disco,
temperatura) a métricas; *Prometheus* las recolecta y almacena; se consultan con el lenguaje
PromQL.

**Respaldo y recuperación ante desastres.** *restic* hace copias **cifradas, deduplicadas e
incrementales**. Un respaldo que no se probó no es un respaldo: la *prueba de restauración*
recupera la copia en un entorno aislado y valida los datos. El *RTO* (Recovery Time
Objective) es cuánto tarda el servicio en volver.

### 4.2 Teoría que sustenta la implementación

`[[relacionar con las presentaciones del curso: "El servidor bare-metal subutilizado",
"El hipervisor", "El cambio de paradigma: contenedores", "Kubernetes: orquestación a nivel
industrial", "SDN y NFV", "El impacto sistémico: de CAPEX a OPEX". Citar Erl, *Cloud
Computing: Concepts, Technology and Architecture*, y la documentación de Kubernetes/CNCF.]]`

## 5. Diseño

### 5.1 Arquitectura del sistema

`[[insertar el diagrama de bloques — redibujar en draw.io a partir del de abajo]]`

```
Dispositivos IoT simulados (última milla)  ── MQTT ──►  ┌─────────────────────────────┐
  medidores luz/agua + aire, 4 zonas                    │ Raspberry Pi 4 (4 GB) — KVM  │
                                                        │                             │
Laptop del operador ── navegador ──► socat (Pi:8080) ──►│  VM control .11  K3s server  │
                                                        │  VM worker  .12  K3s agent   │  IaaS
Prometheus (Pi:9090) ◄── node_exporter ────────────────►│  VM storage .13  MinIO       │
                                                        │  red libvirt 192.168.100.0/24│
                                                        │                             │
                                                        │  K3s (PaaS):                │
                                                        │   mqtt-broker · ingestion-api│
                                                        │   device-simulator · dashboard
                                                        │                             │
                                                        │  BaaS: restic → MinIO        │
                                                        │  restore-test (cada 6 h)     │
                                                        └─────────────────────────────┘
```

### 5.2 Componentes y su interacción

| Componente | Rol | Depende de |
|---|---|---|
| `device-simulator` | Genera telemetría y la publica por MQTT | mqtt-broker |
| `mqtt-broker` (Mosquitto) | Transporte de mensajes | — |
| `ingestion-api` (FastAPI) | Valida, persiste en SQLite, aplica reglas de anomalía, API REST | mqtt-broker |
| `dashboard` | El SaaS: panel del operador; proxy a la API y a Prometheus | ingestion-api, Prometheus |
| Prometheus + node_exporter | Monitoreo del HW de la Pi y las 3 VMs | — |
| MinIO | Almacenamiento S3 para respaldos (BaaS) | — |
| restic + timers | Respaldo automático y prueba de restauración | MinIO, ingestion-api |

## 6. Implementación

### 6.1 Componentes de hardware

| Componente | Detalle |
|---|---|
| Placa | Raspberry Pi 4 Model B, 4 GB RAM, CPU ARM Cortex-A72 (4 núcleos) |
| Almacenamiento | microSD Kingston Canvas Select Plus 128 GB (clase A1) |
| Alimentación | Fuente USB-C 5 V / 3 A |
| Refrigeración | `[[disipador pasivo / ventilador]]` |
| Red | Ethernet/WiFi a la red local; laptop como cliente de administración |

### 6.2 Software utilizado

| Capa | Herramienta | Versión | Función |
|---|---|---|---|
| SO host | Raspberry Pi OS Lite (Debian 13) | 64-bit | Base de la Pi |
| Hipervisor | KVM + QEMU + libvirt | QEMU 10, libvirt 11 | Virtualización |
| Provisión de VMs | virt-install + cloud-init | — | Crear las 3 VMs (IaC) |
| SO invitado | Debian 13 (ARM64) | trixie | Las 3 VMs |
| Automatización | Ansible | 2.19 | Configurar las VMs |
| Orquestador | K3s (Kubernetes) | v1.31.5 | PaaS |
| Contenedores | containerd | 1.7 (incluido en K3s) | Runtime |
| Broker MQTT | Eclipse Mosquitto | 2.0 | Mensajería IoT |
| Base de datos | SQLite | 3 | Telemetría y alertas |
| Microservicios | Python + FastAPI + paho-mqtt + Pydantic | 3.12 | Código propio |
| Panel web | FastAPI + HTML/JS | — | SaaS |
| Monitoreo | Prometheus + node_exporter | 2.53 / 1.9 | HW |
| Respaldo — almacenamiento | MinIO | release actual | BaaS (S3) |
| Respaldo — motor | restic | 0.18 | Copias cifradas |
| Publicación del panel | socat (systemd) | — | Pi:8080 → VM |
| Control de versiones | Git + GitHub | — | `Cua17/sistemas-cloud-proyecto` |

### 6.3 Proceso de la implementación

**Fase 1 — IaaS.** Preparación del host (cgroups, `journald` a RAM, zram); instalación de
KVM/libvirt; red virtual `192.168.100.0/24`; creación de las 3 VMs Debian con IPs estáticas
`.11/.12/.13`; configuración base con Ansible; prueba de conectividad bidireccional (ping +
iperf3); reconstrucción limpia verificada. `[[capturas: vagrant/virt-install, `ip a`,
tabla de conectividad, `virsh list`]]`

**Fase 2 — PaaS + SaaS.** Instalación de K3s (server + agent); desarrollo de los 3
microservicios en Python; construcción de imágenes ARM64 en la Pi e importación al clúster
sin registro externo; despliegue con `kubectl apply`; publicación del panel con socat;
verificación de punta a punta. `[[capturas: `kubectl get nodes/pods`, el panel con datos]]`

**Fase 3 — Monitoreo + BaaS.** node_exporter en las 4 máquinas + Prometheus en la Pi; MinIO
en la VM storage; restic con timers systemd (respaldo cada 30 min, prueba de restauración
cada 6 h); integración del monitoreo y el estado del BaaS en el panel; simulacro de
desastre. `[[capturas: Prometheus targets, panel con la sección Infraestructura y BaaS,
`restic snapshots`, log del restore-test]]`

## 7. Resultado

`[[completar con las cifras finales]]`

- **IaaS:** las 3 VMs se construyen desde código en ~85 s; conectividad bidireccional con
  0 % de pérdida, latencia < 1 ms, ~2 Gbit/s entre VMs.
- **PaaS:** clúster K3s de 2 nodos `Ready`; 4 pods `Running`.
- **SaaS:** panel accesible desde la laptop en `http://<IP-Pi>:8080/`; telemetría en vivo,
  detección de anomalías funcionando (fuga, pico, contaminación).
- **Monitoreo:** Prometheus scrapea las 4 máquinas; CPU/RAM/disco/temperatura visibles.
- **BaaS:** respaldos automáticos hacia MinIO; prueba de restauración `[[OK/…]]`;
  simulacro de desastre `[[RTO]]`.
- **Consumo:** con todo corriendo, la Pi usa ~3.1 GB de 3.7 GB; temperatura ~52–55 °C, sin
  thermal throttling.

## 8. Conclusiones

### 8.1 Resumen de resultados

`[[3-4 frases con lo logrado: las 4 capas de servicio funcionando sobre una sola Raspberry
Pi, con el caso de uso de un operador de telecomunicaciones]]`

### 8.2 Limitaciones del proyecto

- Una sola Raspberry Pi de 4 GB: el stack completo queda al límite de memoria; hubo que
  recortar (SQLite en vez de InfluxDB, sin Grafana, VMs pequeñas). Una Pi de 8 GB daría
  margen.
- Los dispositivos IoT son simulados; no hay radio real de última milla.
- Sin alta disponibilidad: un solo nodo de control, un solo MinIO.
- El arranque desde microSD limita el rendimiento de I/O (un SSD USB sería mejor).

### 8.3 Análisis de lo experimentado

`[[en sus propias palabras: qué aprendieron sobre virtualización vs contenedores, sobre
Kubernetes, sobre el trade-off recursos/funcionalidad, sobre por qué "un respaldo que no se
prueba no es un respaldo". Qué cambiarían.]]`

---

## Anexo — problemas encontrados y su solución

| Problema | Causa | Solución |
|---|---|---|
| VirtualBox no arrancaba en la laptop (proyecto original) | El hipervisor de Windows tomaba AMD-V | Se desactivó VBS/Hyper-V. Luego se migró a Raspberry Pi por requisito del curso |
| Docker en Raspberry Pi OS: cgroup de memoria desactivado | Optimización por defecto de Debian 13 | `cgroup_enable=memory` en `cmdline.txt` |
| El firewall de libvirt bloqueaba el reenvío de puertos a las VMs | Regla `reject` en la cadena FORWARD | Proxy `socat` en la Pi |
| Alertas de fuga falsas todo el tiempo | El patrón de agua no bajaba de noche + regla atada a una hora fija | Patrón realista + regla relativa a la mediana histórica del medidor |
| RAM de la Pi al límite al construir imágenes | Solo 4 GB | Apagar la VM storage durante los builds |
| Grafana pesaba 343 MB | — | Se usa Prometheus solo (cumple igual) |
