"""Reglas de deteccion de anomalias. Funciones puras: reciben la lectura (dict) y
el historial reciente de valores de ese dispositivo, y devuelven una lista de
(regla, detalle).

Estas reglas son el "valor agregado" de la plataforma: convierten datos crudos en
alertas accionables para el operador. Funcionan a cualquier hora del dia.
"""
import statistics

UMBRAL_AIRE_PM25 = 35.0     # OMS: PM2.5 alto = mala calidad de aire
UMBRAL_LUZ_PICO = 3.0       # kWh instantaneo muy por encima de lo normal (~1.0)
FUGA_FLUJO_MIN = 4.0        # L/min: piso para considerar "fuga"
FUGA_FACTOR = 2.0           # y ademas debe ser >= 2x la mediana reciente del medidor


def evaluar(lectura: dict, historial: list[float]) -> list[tuple[str, str]]:
    tipo = lectura["tipo"]
    valor = lectura["valor"]
    alertas: list[tuple[str, str]] = []

    if tipo == "aire" and valor > UMBRAL_AIRE_PM25:
        alertas.append(("aire_contaminado",
                        f"PM2.5 = {valor} (umbral {UMBRAL_AIRE_PM25})"))

    if tipo == "luz" and valor > UMBRAL_LUZ_PICO:
        alertas.append(("pico_consumo", f"consumo instantaneo {valor} kWh"))

    if tipo == "agua":
        ultimas = historial[-3:]
        if len(ultimas) == 3 and all(v > FUGA_FLUJO_MIN for v in ultimas):
            previas = historial[:-3]
            base = statistics.median(previas) if previas else 0.0
            if base == 0.0 or valor >= base * FUGA_FACTOR:
                alertas.append(("posible_fuga",
                                f"flujo {valor} L/min sostenido "
                                f"(habitual ~{round(base, 1)} L/min)"))

    return alertas
