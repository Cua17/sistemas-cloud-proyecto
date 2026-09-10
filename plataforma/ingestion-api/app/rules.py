"""Reglas de deteccion de anomalias. Funciones puras: reciben la lectura (dict) y
el historial reciente de ese dispositivo, y devuelven una lista de (regla, detalle).

Estas reglas son el "valor agregado" de la plataforma: convierten datos crudos en
alertas accionables para el operador.
"""
from datetime import datetime, timezone

UMBRAL_AIRE_PM25 = 35.0      # OMS: 24h > 35 ug/m3 es mala calidad
UMBRAL_LUZ_PICO = 2.0        # kWh instantaneo muy por encima de lo normal
FUGA_FLUJO_MIN = 3.5         # L/min sostenido de madrugada = posible fuga


def _hora(ts: str) -> int:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
    except Exception:
        return datetime.now(timezone.utc).hour


def evaluar(lectura: dict, historial: list[float]) -> list[tuple[str, str]]:
    tipo = lectura["tipo"]
    valor = lectura["valor"]
    alertas: list[tuple[str, str]] = []

    if tipo == "aire" and valor > UMBRAL_AIRE_PM25:
        alertas.append(("aire_contaminado", f"PM2.5 = {valor} (umbral {UMBRAL_AIRE_PM25})"))

    if tipo == "luz" and valor > UMBRAL_LUZ_PICO:
        alertas.append(("pico_consumo", f"consumo instantaneo {valor} kWh"))

    if tipo == "agua" and 0 <= _hora(lectura["ts"]) < 5 and valor > FUGA_FLUJO_MIN:
        ultimas = historial[-3:]
        if len(ultimas) == 3 and all(v > FUGA_FLUJO_MIN for v in ultimas):
            alertas.append(("posible_fuga",
                            f"flujo {valor} L/min sostenido de madrugada"))

    return alertas
