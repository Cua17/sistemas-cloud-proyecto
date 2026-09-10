"""dashboard - el SaaS: panel web del operador municipal.

Sirve una pagina y hace de proxy a la API de ingestion (asi el navegador solo habla
con este servicio). El operador abre la URL y usa la aplicacion, sin saber que abajo
hay una Raspberry Pi, KVM, Kubernetes y una base de datos.
"""
import os

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

INGESTION_API = os.getenv("INGESTION_API", "http://ingestion-api:8000")
PROMETHEUS = os.getenv("PROMETHEUS_URL", "http://192.168.100.1:9090")

app = FastAPI(title="NubeUltima - Panel del operador")
templates = Jinja2Templates(directory="app/templates")

# Consultas PromQL para el monitoreo del hardware, una por metrica.
PROMQL = {
    "cpu":   '100 - (avg by (maquina) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100)',
    "ram":   '(1 - avg by (maquina) (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
    "disco": '(1 - avg by (maquina) (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
    "temp":  'avg by (maquina) (node_hwmon_temp_celsius) or avg by (maquina) (node_thermal_zone_temp)',
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/infra")
async def infra():
    """Monitoreo del hardware: CPU/RAM/disco/temperatura de la Pi y las 3 VMs."""
    out: dict = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for metrica, q in PROMQL.items():
            try:
                r = await client.get(f"{PROMETHEUS}/api/v1/query", params={"query": q})
                for res in r.json()["data"]["result"]:
                    m = res["metric"].get("maquina", "?")
                    out.setdefault(m, {})[metrica] = round(float(res["value"][1]), 1)
            except Exception:
                pass
    return out


# /api/baas y el resto de /api/* van al ingestion-api via el proxy de abajo.


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/{path:path}")
async def proxy(path: str, request: Request):
    url = f"{INGESTION_API}/{path}"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url, params=dict(request.query_params))
        return JSONResponse(status_code=r.status_code, content=r.json())
    except httpx.HTTPError as e:
        return JSONResponse(status_code=502, content={"error": f"ingestion-api no responde: {e}"})
