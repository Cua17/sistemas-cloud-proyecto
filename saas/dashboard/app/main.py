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

app = FastAPI(title="NubeUltima - Panel del operador")
templates = Jinja2Templates(directory="app/templates")


@app.get("/health")
def health():
    return {"status": "ok"}


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
