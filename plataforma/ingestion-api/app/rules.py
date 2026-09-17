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
    """Punto de entrada unico: recibe UNA lectura ya validada + el historial
    reciente de ESE mismo dispositivo, y devuelve la lista de alertas que
    corresponda (puede ser vacia, si no hay nada raro)."""
    tipo = lectura["tipo"]
    valor = lectura["valor"]
    alertas: list[tuple[str, str]] = []

    # Aire y luz: reglas simples, se evaluan con la lectura actual sola, sin
    # necesitar historial (un solo valor fuera de rango ya alcanza).
    if tipo == "aire" and valor > UMBRAL_AIRE_PM25:
        alertas.append(("aire_contaminado",
                        f"PM2.5 = {valor} (umbral {UMBRAL_AIRE_PM25})"))

    if tipo == "luz" and valor > UMBRAL_LUZ_PICO:
        alertas.append(("pico_consumo", f"consumo instantaneo {valor} kWh"))

    # Agua: la regla mas elaborada, porque un pico puntual (alguien llenando
    # una piscina) no deberia ser una alerta - se pide que sea ALGO SOSTENIDO
    # Y ademas anormal para ESE medidor puntual, no un umbral fijo para todos.
    if tipo == "agua":
        ultimas = historial[-3:]
        # 1) sostenido: las ultimas 3 lecturas seguidas por encima del piso
        if len(ultimas) == 3 and all(v > FUGA_FLUJO_MIN for v in ultimas):
            previas = historial[:-3]
            # 2) anormal para este medidor: se compara contra la MEDIANA de
            # sus lecturas previas (no contra un numero fijo igual para
            # todos), asi cada dispositivo se juzga contra su propio habito.
            base = statistics.median(previas) if previas else 0.0
            if base == 0.0 or valor >= base * FUGA_FACTOR:
                alertas.append(("posible_fuga",
                                f"flujo {valor} L/min sostenido "
                                f"(habitual ~{round(base, 1)} L/min)"))

    return alertas
