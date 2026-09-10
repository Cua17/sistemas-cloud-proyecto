"""Pruebas de las reglas de anomalia."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rules import evaluar  # noqa: E402


def _lec(tipo, valor):
    return {"ts": "2026-09-10T14:00:00+00:00", "device_id": "x",
            "zona": "zona-1", "tipo": tipo, "valor": valor}


def test_aire_contaminado():
    a = evaluar(_lec("aire", 50.0), [])
    assert any(r == "aire_contaminado" for r, _ in a)


def test_aire_normal_sin_alerta():
    assert evaluar(_lec("aire", 12.0), []) == []


def test_pico_de_consumo():
    assert any(r == "pico_consumo" for r, _ in evaluar(_lec("luz", 3.5), []))


def test_consumo_normal_sin_alerta():
    assert evaluar(_lec("luz", 1.2), []) == []


def test_fuga_requiere_flujo_sostenido():
    # un solo valor alto: todavia no
    assert evaluar(_lec("agua", 6.0), [6.0]) == []
    # tres valores altos seguidos, muy por encima de lo habitual: alerta
    hist = [1.0, 1.2, 0.9, 1.1, 5.0, 5.5, 6.0]
    assert any(r == "posible_fuga" for r, _ in evaluar(_lec("agua", 6.0), hist))


def test_fuga_no_dispara_si_el_medidor_siempre_es_alto():
    # si el flujo habitual del medidor ya es ~5, tres lecturas de ~5 no son fuga
    hist = [5.0, 5.2, 4.8, 5.1, 5.0, 5.3, 5.0]
    assert evaluar(_lec("agua", 5.0), hist) == []
