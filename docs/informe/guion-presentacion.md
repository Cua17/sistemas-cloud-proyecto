# Guión de presentación — NubeÚltima

> Lo que se dice en la exposición son **5 cajas de un diagrama**, no 30 herramientas.
> El profe quiere ver que entendemos los *conceptos*. La lista completa de software va en
> el informe escrito (sección "Software Utilizado").

## El diagrama (dibujarlo en una diapositiva)

```
  Dispositivos IoT (simulados)          [ÚLTIMA MILLA]
   medidores luz/agua + aire · MQTT
            │
            ▼
  ┌───────────────────────────────────────────────┐
  │  Raspberry Pi 4  —  KVM (hipervisor)           │   ← el "centro de datos" físico
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
  │  │ VM control│  │ VM worker │  │ VM storage│    │   ← 3 VMs independientes  [IaaS]
  │  │  .100.11  │  │  .100.12  │  │  .100.13  │    │
  │  └────┬─────┘  └────┬─────┘  └──────────┘      │
  │       └── Docker Swarm ──┘                     │   ← plataforma de microservicios [PaaS]
  │            │                                   │
  │   simulador→broker→ingestión→SQLite            │
  │                    │                           │
  │            panel web del operador  ────────────┼──▶ el usuario abre el navegador  [SaaS]
  │                                                │
  │   MinIO + restic  ← respaldos automaticos      │   ← backup como servicio  [BaaS]
  │   Netdata         ← monitoreo del hardware     │
  └───────────────────────────────────────────────┘
```

## Las 5 frases (una por caja)

1. **IaaS — "el centro de datos".**
   Sobre la Raspberry Pi instalamos **KVM**, el hipervisor nativo de Linux. Con él creamos
   **3 máquinas virtuales independientes**, cada una con su IP fija, que se comunican entre
   sí. Todo se crea desde archivos de texto con un comando (`crear-vms.sh`) — infraestructura
   como código.

2. **PaaS — "la plataforma".**
   Unimos dos de esas VMs con **Docker Swarm**, el modo clúster de Docker. Ahí se despliegan
   los microservicios sin administrar servidores: Swarm los reparte entre las VMs, los
   reinicia si se caen y maneja la red interna.

3. **La aplicación IoT (última milla).**
   Un **simulador** hace de medidores de luz, agua y aire de 4 zonas de una ciudad, y manda
   sus lecturas por **MQTT** (el protocolo real de NB-IoT/LoRaWAN). Un **microservicio** las
   recibe, las valida, detecta anomalías (fugas, picos, aire contaminado) y las guarda.

4. **SaaS — "el producto".**
   El operador municipal abre una **página web** y ve el mapa de zonas, el estado de los
   medidores y las alertas en vivo. No sabe (ni le importa) que abajo hay una Pi, KVM,
   Docker y una base de datos.

5. **BaaS + monitoreo.**
   **restic** hace respaldos automáticos y cifrados hacia **MinIO** (un almacenamiento tipo
   Amazon S3) en la tercera VM, y probamos que se pueden restaurar. **Netdata** muestra en
   tiempo real el consumo de CPU, RAM y temperatura de la Pi y las VMs.

## Cierre (una frase)

> "Demostramos las 4 capas de servicio de la nube —IaaS, PaaS, SaaS y BaaS— sobre una
> sola Raspberry Pi, con el caso de uso real de un operador de telecomunicaciones:
> conectividad IoT de última milla + plataforma de datos para una ciudad inteligente."

---

## Estado (para nosotros, no para la diapositiva)

| Capa | Estado |
|---|---|
| IaaS (3 VMs KVM) | ✅ Fase 1 completa |
| PaaS (Docker Swarm) | ⏳ Fase 2 |
| App + SaaS | ⏳ Fase 2 |
| BaaS + Monitoreo | ⏳ Fase 3 |
