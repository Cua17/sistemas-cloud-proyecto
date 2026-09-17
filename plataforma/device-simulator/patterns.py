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
    """Factor 0..1 con minimo alrededor de las 04:00 y maximo alrededor de las 16:00.
    Es una onda seno desplazada: sin(x) va de -1 a 1, por eso se re-escala con
    0.5 + 0.5*sin(...) para que quede siempre entre 0 y 1. El '-10' corre la
    onda en el tiempo para que el minimo caiga de madrugada, no a medianoche."""
    return 0.5 + 0.5 * math.sin((hour - 10) / 24 * 2 * math.pi)


def base_reading(tipo: str, hour: float) -> float:
    """Lectura NORMAL (sin anomalia) para ese tipo de dispositivo a esa hora:
    un piso ('base') + la curva del dia multiplicada por la amplitud ('amp'),
    mas un poco de ruido aleatorio para que no sea una linea perfecta (los
    sensores reales siempre tienen algo de ruido)."""
    cfg = TIPOS[tipo]
    valor = cfg["base"] + cfg["amp"] * daily_factor(hour)
    valor += random.gauss(0, cfg["amp"] * 0.04)
    return max(0.0, round(valor, 2))  # nunca negativo


def inject_anomaly(tipo: str, valor: float, kind: str) -> float:
    """Deforma una lectura NORMAL (ya calculada con base_reading) para que
    quede claramente por encima de los umbrales que usa rules.py en el
    ingestion-api, sin importar la hora del dia - asi una anomalia se ve
    siempre como anomalia, de dia o de noche."""
    if kind == "fuga" and tipo == "agua":
        return round(max(valor, 5.0), 2)          # flujo sostenido que no baja
    if kind == "pico" and tipo == "luz":
        return round(max(valor * 4.0, 3.5), 2)    # pico de consumo
    if kind == "contaminacion" and tipo == "aire":
        return round(max(valor, 10.0) + 40.0, 2)  # episodio de mala calidad de aire
    return valor
