# Documento de diseño — Proyecto Sistemas Cloud (Fase 1)

**Proyecto:** NubeÚltima — Plataforma Cloud Convergente para Telemetría IoT de Última Milla
**Curso:** Sistemas Cloud y Tecnologías de Última Milla (EHP 1) — Universidad del Istmo
**Catedrático:** Sergio Saenz
**Grupo:** 4 integrantes
**Fecha del documento:** 2026-08-28
**Plazo Fase 1:** ~3 semanas

> El nombre "NubeÚltima" es provisional. Alternativas: "CiudadNodo", "TelurIoT". El grupo puede cambiarlo.

---

## 1. Resumen ejecutivo

Se construye, en una sola laptop, una réplica a pequeña escala del sistema cloud que un
operador de telecomunicaciones usaría para ofrecer un servicio de "ciudad inteligente":
dispositivos IoT en la última milla (medidores de luz/agua y sensores de calidad de aire,
**simulados**) envían telemetría por MQTT hacia un centro de datos virtualizado de 3 VMs,
donde una plataforma de microservicios la ingiere, detecta anomalías y la expone a un
operador municipal a través de un panel web (SaaS). En paralelo corren un servicio de
monitoreo de hardware y un servicio de respaldo automático verificable (BaaS).

El proyecto demuestra de forma práctica el desacople hardware/software y las capas de
servicio **IaaS, PaaS, SaaS y BaaS**.

### Objetivos

1. Desplegar 3 VMs Linux independientes con IPs estáticas y comunicación bidireccional estable (IaaS).
2. Montar sobre ellas una plataforma de microservicios orquestada (PaaS).
3. Desplegar una aplicación funcional de cara al usuario final (SaaS).
4. Implementar un servicio de respaldo automático y verificable (BaaS — puntos extra).
5. Monitorizar el consumo de hardware de la infraestructura.
6. Documentar todo el proceso según el esquema de entrega del curso.

### Alcance

- **Incluye:** virtualización local, red local con direccionamiento estático, orquestación
  con Kubernetes ligero (K3s), 4 microservicios (3 propios + broker + base de datos),
  panel web, monitoreo con Prometheus/Grafana, respaldos con Velero + restic hacia MinIO,
  hardening básico de seguridad, pruebas de conectividad y de restauración.
- **No incluye:** hardware IoT físico, nubes públicas de pago (AWS/Azure/GCP), alta
  disponibilidad multi-sitio, la convergencia con GPON/HFC/5G a nivel de equipos reales
  (se simula el comportamiento de la última milla vía MQTT), CI/CD.

### Costo

USD 0. Todo el software es libre / gratuito para uso educativo y corre en la laptop del
estudiante. Únicos costos: ~40–60 GB de disco, ~7–8 GB de RAM cuando las 3 VMs corren
en simultáneo (de 16 GB; se puede bajar a ~6 GB reduciendo asignaciones), y tiempo.

---

## 2. Contexto y justificación

El catedrático es Coordinador de Infrastructure & Cloud Engineering en Tigo y ex IP
Planning Engineer, con maestría en redes y seguridad informática. El proyecto se diseñó
para alinearse con su experiencia: un caso de uso que un operador real opera (conectividad
IoT + plataforma de datos para municipios), con énfasis en automatización, monitoreo,
seguridad y continuidad (respaldos con SLA).

El escenario corresponde directamente al contenido de la Semana 11 del programa
("Cómo convergen plataformas Cloud —AWS/Azure IoT— con redes de última milla —LoRaWAN,
NB-IoT, 5G—") y usa conceptos de las 4 presentaciones del curso: hipervisor vs
contenedores, orquestación con Kubernetes, SDN/NFV (plano de control vs plano de datos),
Edge Computing y modelo CAPEX→OPEX.

---

## 3. Arquitectura del sistema

### 3.1 Diagrama de bloques

```
  ÚLTIMA MILLA (simulada)
  ┌─────────────────────────────────────────────┐
  │  device-simulator (Python)                   │
  │  - N medidores de luz  (kWh)                  │
  │  - N medidores de agua (L/min, detección fuga)│
  │  - N estaciones de aire (PM2.5, CO2, ruido)   │
  │  Publica por MQTT/TLS, 4 zonas de ciudad      │
  └───────────────────────┬─────────────────────┘
                          │  MQTT (protocolo real de NB-IoT/LoRaWAN)
                          ▼
  ═══════════════════════════════════════════════════════════════════════
  IaaS — CENTRO DE DATOS   (Oracle VirtualBox 7.2 sobre Windows 11 Home)
  ═══════════════════════════════════════════════════════════════════════
   Red host-only  192.168.56.0/24   ·   IPs estáticas   ·   SSH por llave
   Segunda interfaz NAT en cada VM (solo salida a internet para apt/imágenes)

   ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
   │ VM1 datacenter-control │  │ VM2 datacenter-worker  │  │ VM3 datacenter-storage │
   │ 192.168.56.11          │  │ 192.168.56.12          │  │ 192.168.56.13          │
   │ 2 vCPU / 3 GB          │  │ 2 vCPU / 3 GB          │  │ 2 vCPU / 2 GB          │
   │                        │  │                        │  │  (fuera del clúster)   │
   │ K3s server (control    │  │ K3s agent (cargas de   │  │ MinIO (S3)             │
   │ plane) + Traefik       │  │ trabajo)               │  │ restic repo            │
   │ + panel SaaS           │  │                        │  │ node_exporter (systemd)│
   │ node_exporter          │  │ node_exporter          │  │                        │
   └────────────┬───────────┘  └───────────┬────────────┘  └───────────┬────────────┘
                └──────────── red del clúster (Flannel VXLAN) ─────────┘
                                           │
  ═══════════════════════════════════════════════════════════════════════
  PaaS — PLATAFORMA DE MICROSERVICIOS   (K3s = Kubernetes certificado CNCF)
  ═══════════════════════════════════════════════════════════════════════
   Namespace `plataforma`:
     • mqtt-broker      Eclipse Mosquitto           (configurado)
     • ingestion-api    FastAPI  — PROPIO           recibe→valida→InfluxDB, API REST
     • anomaly-service  Python   — PROPIO           reglas de umbral → alertas
     • device-simulator Python   — PROPIO           (la "última milla")
     • influxdb         InfluxDB 2.x OSS            base de series de tiempo
   Namespace `monitoreo`:
     • kube-prometheus-stack (Prometheus + Grafana + alertmanager) vía Helm
   Namespace `backup`:
     • velero + node-agent
     • CronJob restic-influx + CronJob restore-test
   Ingress: Traefik (incluido en K3s)  ·  Secrets  ·  NetworkPolicies por namespace

  ═══════════════════════════════════════════════════════════════════════
  SaaS — PANEL DE CIUDAD                          BaaS — RESPALDO COMO SERVICIO
  ═══════════════════════════════════════════════════════════════════════
   http://192.168.56.11/                          MinIO en VM3 = endpoint del servicio
   - mapa de 4 zonas + estado dispositivos        Velero  → respaldo del clúster K8s
   - consumo actual (luz/agua) y AQI              restic  → InfluxDB + configs + dashboards
   - alertas activas                              CronJob nocturno + prueba de restore
   - gráficas Grafana embebidas                   página de estado (última copia, tamaño,
   El operador solo abre el navegador.              resultado del último restore-test)

  MONITOREO DE HW (rúbrica):  Prometheus scrapea node_exporter de VM1/VM2/VM3
                              → dashboard Grafana: CPU / RAM / disco / red por VM
```

### 3.2 Roles de las VMs

| VM | Nombre | IP | Rol | Justificación |
|----|--------|-----|-----|---------------|
| VM1 | datacenter-control | 192.168.56.11 | Plano de control: K3s server, ingress, panel SaaS | "El cerebro" (analogía SDN de la presentación 4) |
| VM2 | datacenter-worker | 192.168.56.12 | Plano de datos: ejecuta los microservicios | "El músculo" |
| VM3 | datacenter-storage | 192.168.56.13 | Almacenamiento y respaldo, **fuera del clúster** | Demuestra comunicación entre VMs no agrupadas y aísla el BaaS |

Las 3 VMs se crean de forma independiente (cada una con su propia definición) y son
direccionables por separado. Que VM1 y VM2 formen un clúster K3s es una funcionalidad
(cooperan como un centro de datos real), no una violación del requisito de independencia.

### 3.3 Flujo de datos

1. `device-simulator` genera lecturas con patrones realistas (curva diaria de consumo,
   fugas de agua nocturnas ocasionales, picos de consumo, episodios de contaminación) y
   las publica en topics MQTT del tipo `ciudad/{zona}/{tipo}/{id}`.
2. `mqtt-broker` (Mosquitto) recibe con autenticación usuario/contraseña + TLS.
3. `ingestion-api` está suscrito al broker: valida el payload, lo enriquece con metadatos
   de zona, y lo escribe en `influxdb`. Expone además una API REST de consulta.
4. `anomaly-service` evalúa reglas de umbral (medidor sin reportar > X min, flujo de agua
   constante de madrugada, consumo > percentil histórico, AQI > umbral) y publica alertas
   (almacenadas en InfluxDB / expuestas por la API).
5. El `dashboard` (SaaS) consulta la API de `ingestion-api` y embebe paneles de Grafana;
   el operador lo abre en `http://192.168.56.11/`.
6. `Prometheus` scrapea `node_exporter` de las 3 VMs de forma continua; `Grafana` grafica
   el consumo de hardware.
7. Los `CronJob` de respaldo copian InfluxDB, configs y estado del clúster hacia MinIO en
   VM3; un `CronJob` de restore-test valida periódicamente que la copia es restaurable.

### 3.4 Componentes como unidades aisladas

| Unidad | Qué hace | Interfaz | Depende de |
|--------|----------|----------|-----------|
| device-simulator | Genera y publica telemetría simulada | Publica MQTT | broker |
| mqtt-broker | Transporte de mensajes | MQTT 1883/8883 | — |
| ingestion-api | Persiste telemetría + API de consulta | MQTT (sub) + HTTP REST | broker, influxdb |
| anomaly-service | Detecta anomalías y emite alertas | Lee/escribe vía ingestion-api o InfluxDB | influxdb |
| influxdb | Almacén de series de tiempo | HTTP (línea de InfluxDB) | volumen persistente |
| dashboard (SaaS) | UI para el operador | HTTP (navegador) | ingestion-api, Grafana |
| kube-prometheus-stack | Monitoreo de infra | HTTP (Grafana/Prometheus) | node_exporter |
| Velero + restic CronJobs | Respaldo y verificación | S3 (MinIO) | MinIO, InfluxDB |
| MinIO | Almacenamiento de objetos para respaldos | S3 API | disco de VM3 |

---

## 4. Stack tecnológico

Todo software libre / gratuito para uso educativo. Descargar siempre desde el sitio oficial.

| Capa | Herramienta | Versión objetivo | Fuente oficial | Licencia |
|------|-------------|------------------|----------------|----------|
| Hipervisor | Oracle VirtualBox | 7.2.x | virtualbox.org | GPLv3 (base; sin Extension Pack) |
| VMs como código | Vagrant | 2.4.x | developer.hashicorp.com | BUSL-1.1 (libre para uso educativo) |
| Configuración | Ansible | 2.16+ | ansible.com (Red Hat) | GPLv3 |
| SO invitado | Ubuntu Server LTS | 24.04 (box `bento/ubuntu-24.04`) | ubuntu.com / app.vagrantup.com | Libre |
| Orquestador | K3s | v1.30.x | k3s.io (SUSE/Rancher) | Apache 2.0 |
| Gestor de paquetes K8s | Helm | 4.x | helm.sh | Apache 2.0 |
| Broker MQTT | Eclipse Mosquitto | 2.x (imagen oficial) | mosquitto.org | EPL/EDL |
| Base series de tiempo | InfluxDB OSS | 2.7.x (imagen oficial) | influxdata.com | MIT / Apache 2.0 |
| Microservicios propios | Python + FastAPI + paho-mqtt | Python 3.12 | fastapi.tiangolo.com | MIT |
| Monitoreo infra | kube-prometheus-stack (Prometheus, Grafana, node_exporter) | chart 60+ | prometheus.io / grafana.com | Apache 2.0 / AGPLv3 |
| Respaldo K8s | Velero | 1.14.x | velero.io (CNCF) | Apache 2.0 |
| Respaldo datos/archivos | restic | 0.16+ | restic.net | BSD-2 |
| Almacenamiento respaldos | MinIO | release actual | min.io | AGPLv3 |
| Imágenes de contenedor | Docker Hub *Official Images* / Quay.io | — | hub.docker.com | — |

**Nota sobre descargas de imágenes:** un integrante debe crear una cuenta gratuita de
Docker Hub para evitar el límite de descargas anónimas durante el desarrollo.

---

## 5. Cumplimiento de la rúbrica

### 5.1 Rúbrica del proyecto físico

| Requisito | Implementación | Evidencia a presentar |
|-----------|----------------|----------------------|
| Las VMs deben "compilar" | `vagrant up` construye las 3 VMs desde el `Vagrantfile` + playbooks Ansible | Video/capturas de `vagrant up` desde cero |
| IPs estáticas en red local | Red host-only `192.168.56.0/24`, IPs `.11/.12/.13` fijadas con netplan vía Ansible | `ip a` en cada VM, archivo netplan |
| Comunicación bidireccional estable | Script `pruebas/conectividad.sh`: matriz de `ping` + `iperf3` (throughput y jitter de los 3 pares) + prueba MQTT y HTTP entre VMs | Tabla de resultados, presentada como mini-SLA interno |
| 4 servicios corriendo y funcionales | (1) panel SaaS, (2) API de ingestión, (3) Grafana de monitoreo, (4) portal BaaS / estado de respaldos | Demo en vivo + `kubectl get pods` + capturas |
| Monitorizar el HW utilizado | Prometheus + node_exporter en las 3 VMs → dashboard Grafana con CPU/RAM/disco/red por VM | Capturas del dashboard en reposo y bajo carga |
| Acceso exitoso a los servicios | Demo desde el navegador del host + healthchecks HTTP | Capturas, respuestas HTTP 200 |
| Verificación de los respaldos | `CronJob` restic + Velero hacia MinIO; `CronJob` restore-test a namespace scratch con validación de datos; simulacro de desastre documentado (borrar VM2 y restaurar) | Log del restore-test, video del simulacro |

> **Pendiente de confirmar con el catedrático:** qué entiende exactamente por "los 4 tipos
> de servicio" (interpretación de este diseño: 4 servicios accesibles por el usuario).

### 5.2 Puntos extra — BaaS

"Emular un servicio de respaldo portador": MinIO en VM3 es el servicio de respaldo que las
demás VMs consumen vía API S3. Velero respalda el estado del clúster; restic respalda los
datos de InfluxDB, las configuraciones de Mosquitto y los dashboards de Grafana. Copias
programadas (CronJob), cifradas (restic) y verificadas (restore-test automático). Una
página de estado muestra: fecha de la última copia, tamaño, y resultado del último
restore-test — presentado como un producto BaaS con SLA.

### 5.3 Seguridad (proporcionada al alcance)

- SSH solo por llave, sin contraseña.
- MQTT con autenticación usuario/contraseña + TLS con CA propia generada por el grupo.
- Credenciales en Secrets de Kubernetes (no en texto plano en los manifiestos).
- NetworkPolicies que aíslan los namespaces `plataforma`, `monitoreo` y `backup`.
- Cifrado en reposo de los respaldos (restic).
- Párrafo de "Zero Trust / mínimo privilegio" en el informe, enlazado a la Semana 12.

---

## 6. Estructura del repositorio

```
Sistemas Cloud/
├── docs/
│   ├── superpowers/specs/         # este documento y el plan de implementación
│   └── informe/                   # el documento escrito de entrega (secciones)
├── infra/
│   ├── Vagrantfile
│   └── ansible/                   # playbooks: red, k3s-server, k3s-agent, minio
├── plataforma/
│   ├── ingestion-api/             # código propio + Dockerfile
│   ├── anomaly-service/           # código propio + Dockerfile
│   ├── device-simulator/          # código propio + Dockerfile
│   └── k8s/                       # manifiestos: namespaces, mosquitto, influxdb, deployments, ingress, networkpolicies
├── saas/
│   └── dashboard/                 # frontend + Dockerfile
├── monitoreo/
│   └── values-kube-prometheus.yaml
├── backup/
│   ├── velero/                    # configuración e install
│   └── cronjobs/                  # restic-influx, restore-test
└── pruebas/
    ├── conectividad.sh
    ├── carga-mqtt.py
    └── restore-drill.md
```

---

## 7. Reparto de trabajo (4 integrantes)

| # | Área | Responsabilidades | Herramientas |
|---|------|-------------------|--------------|
| 1 | Infra / IaC | Vagrantfile, playbooks Ansible, red host-only, IPs estáticas, script de conectividad | VirtualBox, Vagrant, Ansible |
| 2 | Plataforma / PaaS | Clúster K3s, Helm, Traefik/ingress, manifiestos, Dockerfiles, NetworkPolicies | K3s, Helm, kubectl |
| 3 | Aplicación | `ingestion-api`, `anomaly-service`, `device-simulator`, `dashboard` | Python, FastAPI, paho-mqtt |
| 4 | Monitoreo + BaaS + informe | kube-prometheus-stack, MinIO, Velero, restic, CronJobs, restore-drill; lidera el documento escrito | Prometheus, Grafana, Velero, restic, MinIO |

Cada integrante redacta la sección del informe correspondiente a su área.

---

## 8. Cronograma (3 semanas)

### Semana 1 — cimientos (en paralelo)
- **Hito:** `vagrant up` levanta 3 VMs con IPs estáticas; `conectividad.sh` pasa; `kubectl get nodes` muestra VM1+VM2 `Ready`; MinIO accesible en VM3; los 4 servicios corren localmente en Docker en la laptop de quien los desarrolla.

### Semana 2 — integración
- **Hito:** la plataforma completa desplegada en K3s; el panel SaaS accesible desde el navegador del host; Prometheus scrapeando las 3 VMs con dashboard de HW funcionando; primeras copias automáticas hacia MinIO.

### Semana 3 — pulido y entrega
- **Hito:** Velero + restic + restore-test automatizados; simulacro de desastre grabado; hardening de seguridad aplicado; pruebas de carga y latencia hechas; capturas completas; informe escrito redactado y revisado; ensayo de la demo final.

---

## 9. Riesgos y plan B

| Riesgo | Mitigación / plan B (mantiene los requisitos obligatorios) |
|--------|-----------------------------------------------------------|
| Curva de K3s demasiado alta | Sustituir por Docker Compose multi-nodo (menos vistoso, sigue siendo PaaS) |
| Ansible añade fricción | Provisioners shell bien comentados dentro del Vagrantfile |
| `anomaly-service` propio consume mucho tiempo | Implementar las reglas en Node-RED (visual, sin código) |
| Velero se complica | Quedarse solo con restic (sigue siendo un BaaS válido y verificable) |
| RAM insuficiente durante la demo | Bajar réplicas, apagar el simulador de carga, cerrar apps del host |
| Límite de descargas de Docker Hub | Cuenta gratuita + `imagePullPolicy: IfNotPresent` + pre-pull de imágenes |

---

## 10. Criterios de éxito

1. `vagrant destroy && vagrant up` reconstruye todo el centro de datos sin intervención manual.
2. Las 3 VMs se comunican en ambos sentidos de forma estable (matriz de pruebas en verde).
3. El operador abre el navegador y ve telemetría en vivo y alertas reales.
4. El dashboard de monitoreo muestra el consumo de HW de las 3 VMs.
5. Existe al menos un restore verificado (automático + simulacro manual).
6. El informe escrito cubre las 8 secciones del esquema de entrega del curso.
