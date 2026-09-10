"""Pruebas de las reglas de anomalia."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rules import evaluar  # noqa: E402


def _lec(tipo, valor, ts="2026-09-10T03:00:00+00:00"):
    return {"ts": ts, "device_id": "x", "zona": "zona-1", "tipo": tipo, "valor": valor}


def test_aire_contaminado():
    a = evaluar(_lec("aire", 50.0), [])
    assert any(r == "aire_contaminado" for r, _ in a)


def test_aire_normal_sin_alerta():
    assert evaluar(_lec("aire", 12.0), []) == []


def test_pico_de_consumo():
    a = evaluar(_lec("luz", 3.5), [])
    assert any(r == "pico_consumo" for r, _ in a)


def test_fuga_requiere_flujo_sostenido_de_madrugada():
    # un solo valor alto: todavia no
    assert evaluar(_lec("agua", 5.0), [5.0]) == []
    # tres valores altos seguidos de madrugada: alerta
    a = evaluar(_lec("agua", 5.0), [4.0, 4.5, 5.0])
    assert any(r == "posible_fuga" for r, _ in a)


def test_fuga_no_aplica_de_dia():
    a = evaluar(_lec("agua", 5.0, ts="2026-09-10T14:00:00+00:00"), [4.0, 4.5, 5.0])
    assert a == []
