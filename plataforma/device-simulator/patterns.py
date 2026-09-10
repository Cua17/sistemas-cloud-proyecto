"""Patrones de telemetria realista para los dispositivos simulados.

Funciones puras (faciles de probar): dada una hora del dia, devuelven un valor
plausible para un medidor de luz/agua o un sensor de aire, con curva diaria + ruido.
"""
import math
import random

# Config por tipo de dispositivo. 'base' es el valor de fondo (madrugada); 'amp' es
# cuanto sube en el pico del dia. Asi de noche los valores son bajos (nadie consume)
# y las reglas de anomalia solo se disparan con anomalias de verdad.
TIPOS = {
    "luz":  {"unidad": "kWh",   "base": 0.10, "amp": 0.9},
    "agua": {"unidad": "L/min", "base": 0.30, "amp": 9.0},
    "aire": {"unidad": "PM2.5", "base": 10.0, "amp": 12.0},
}


def daily_factor(hour: float) -> float:
    """Factor 0..1 con minimo alrededor de las 04:00 y maximo alrededor de las 16:00."""
    return 0.5 + 0.5 * math.sin((hour - 10) / 24 * 2 * math.pi)


def base_reading(tipo: str, hour: float) -> float:
    """Lectura normal para ese tipo de dispositivo a esa hora."""
    cfg = TIPOS[tipo]
    valor = cfg["base"] + cfg["amp"] * daily_factor(hour)
    valor += random.gauss(0, cfg["amp"] * 0.04)
    return max(0.0, round(valor, 2))


def inject_anomaly(tipo: str, valor: float, kind: str) -> float:
    """Deforma una lectura para simular una anomalia (valores claramente por
    encima de los umbrales de las reglas, sin importar la hora)."""
    if kind == "fuga" and tipo == "agua":
        return round(max(valor, 5.0), 2)          # flujo sostenido que no baja
    if kind == "pico" and tipo == "luz":
        return round(max(valor * 4.0, 3.5), 2)    # pico de consumo
    if kind == "contaminacion" and tipo == "aire":
        return round(max(valor, 10.0) + 40.0, 2)  # episodio de mala calidad de aire
    return valor
