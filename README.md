# NubeÚltima — Proyecto Sistemas Cloud (Fase 1)

Plataforma Cloud convergente para telemetría IoT de última milla, montada como homelab en
una sola laptop. Demuestra de forma práctica las capas de servicio **IaaS, PaaS, SaaS y
BaaS**.

**Curso:** Sistemas Cloud y Tecnologías de Última Milla (EHP 1) — Universidad del Istmo
**Catedrático:** Sergio Saenz

## Qué hace

Dispositivos IoT simulados (medidores de luz/agua y sensores de calidad de aire en 4 zonas
de una ciudad) envían telemetría por MQTT hacia un centro de datos de 3 máquinas virtuales.
Una plataforma de microservicios la ingiere, detecta anomalías (fugas, picos de consumo,
aire contaminado) y la muestra a un operador municipal en un panel web. En paralelo corren
monitoreo de hardware y un servicio de respaldo automático verificable.

| Capa | Implementación |
|------|----------------|
| IaaS | 3 VMs Linux en VirtualBox, IPs estáticas, red host-only |
| PaaS | Clúster K3s (Kubernetes) sobre VM1 + VM2 |
| SaaS | Panel web del operador |
| BaaS | MinIO + Velero + restic, con prueba de restauración |

## Documentación

- Diseño: [`docs/superpowers/specs/2026-08-28-plataforma-iot-ultima-milla-design.md`](docs/superpowers/specs/2026-08-28-plataforma-iot-ultima-milla-design.md)
- Plan de implementación: [`docs/superpowers/plans/2026-09-01-nubeultima-fase1.md`](docs/superpowers/plans/2026-09-01-nubeultima-fase1.md)

## Estado

En desarrollo — Fase 0 (preparación del entorno).

## Integrantes

- _(completar)_
