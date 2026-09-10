"""Pruebas de los patrones del simulador (funciones puras)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from patterns import base_reading, daily_factor, inject_anomaly  # noqa: E402


def test_consumo_mayor_de_dia_que_de_madrugada():
    dia = sum(base_reading("luz", 15) for _ in range(50)) / 50
    noche = sum(base_reading("luz", 3) for _ in range(50)) / 50
    assert dia > noche


def test_lecturas_nunca_negativas():
    for h in range(24):
        for tipo in ("luz", "agua", "aire"):
            assert base_reading(tipo, h) >= 0.0


def test_daily_factor_en_rango():
    for h in range(24):
        assert 0.0 <= daily_factor(h) <= 1.0


def test_fuga_de_agua_sube_el_flujo():
    assert inject_anomaly("agua", 0.5, "fuga") >= 4.5


def test_pico_de_luz_multiplica():
    assert inject_anomaly("luz", 1.0, "pico") > 3.0


def test_anomalia_de_otro_tipo_no_afecta():
    assert inject_anomaly("aire", 10.0, "fuga") == 10.0
