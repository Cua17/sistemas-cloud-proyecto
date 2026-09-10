# Simulacro de desastre — NubeÚltima

Demuestra la recuperación ante la pérdida de un nodo del centro de datos. Se prueban dos
mecanismos: el **self-healing de Kubernetes** (reprograma cargas) y el **BaaS** (restaura
datos si se perdieron).

## Preparación

```bash
# Estado inicial: anotar el conteo de lecturas y que el panel funciona
curl -s http://192.168.0.51:8080/api/stats
```

## Escenario 1 — Se "quema" el nodo worker

```bash
# En la Pi:
virsh --connect qemu:///system destroy nubeultima-worker      # apagado forzado (falla de HW)
```

**Qué se observa (~1-2 min):**
```bash
kubectl get nodes                       # nubeultima-worker  NotReady
kubectl -n nubeultima get pods -o wide   # los pods del worker: Terminating / Pending
```
El panel deja de recibir telemetría nueva (el broker y la ingestión estaban en ese nodo).

## Recuperación

```bash
# En la Pi: recrear el nodo desde código
cd ~/nubeultima
bash infra/kvm/crear-vms.sh              # recrea SOLO las VMs que faltan
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/common.yml --limit nubeultima-worker
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/vm-tuning.yml --limit nubeultima-worker
# reinstalar el agente K3s en el worker nuevo
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/k3s.yml
# reimportar las imagenes al worker nuevo
bash infra/k3s/construir-imagenes.sh     # (o solo reimportar desde /var/lib/libvirt si estan cacheadas)
```

**Qué se observa:**
```bash
kubectl get nodes                        # worker vuelve a Ready
kubectl -n nubeultima get pods            # Kubernetes reprograma los pods solo
```

## Escenario 2 — Se perdió la base de datos

Si el disco del pod de `ingestion-api` se perdió (el PVC vivía en el worker):

```bash
# Restaurar desde el ultimo respaldo verificado
sudo /usr/local/bin/nubeultima-restore-test        # confirma que el backup es restaurable
# restauracion real al volumen del pod:
export RESTIC_REPOSITORY=s3:http://192.168.100.13:9000/nubeultima-backups
export RESTIC_PASSWORD_FILE=/etc/nubeultima/restic-password
export AWS_ACCESS_KEY_ID=$(cat /etc/nubeultima/minio-access)
export AWS_SECRET_ACCESS_KEY=$(cat /etc/nubeultima/minio-secret)
restic restore latest --target /var/tmp/rst
POD=$(kubectl -n nubeultima get pod -l app=ingestion-api -o jsonpath='{.items[0].metadata.name}')
kubectl -n nubeultima cp $(find /var/tmp/rst -name nubeultima.db) $POD:/data/nubeultima.db
kubectl -n nubeultima rollout restart deploy/ingestion-api
```

## Verificación final

```bash
curl -s http://192.168.0.51:8080/api/stats     # las lecturas historicas volvieron
# abrir el panel: telemetria nueva fluyendo otra vez
```

## Resultados (completar al ejecutarlo)

| Métrica | Valor |
|---|---|
| Tiempo de detección (nodo NotReady) | ___ |
| Tiempo de recuperación del nodo (RTO) | ___ |
| Lecturas antes / después de restaurar | ___ / ___ |
| ¿El panel volvió a operar? | ___ |
| ¿Se perdió algún dato? | ___ |
