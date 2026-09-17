"""device-simulator - hace de medidores IoT de una ciudad y publica por MQTT.

Representa la "ultima milla": dispositivos NB-IoT/LoRaWAN mandando telemetria.
Publica en  ciudad/{zona}/{tipo}/{device_id}  un JSON
    {ts, device_id, zona, tipo, valor, unidad}

Cada dispositivo puede entrar en estado "anomalo" durante varios ciclos seguidos
(fuga de agua, pico de consumo, mala calidad de aire), asi las alertas aparecen
de forma visible y sostenida en el panel.
"""
import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from patterns import TIPOS, base_reading, inject_anomaly

MQTT_HOST      = os.getenv("MQTT_HOST", "mqtt-broker")
MQTT_PORT      = int(os.getenv("MQTT_PORT", "1883"))
ZONAS         = os.getenv("ZONAS", "zona-1,zona-2,zona-3,zona-4").split(",")
DEV_POR_ZONA  = int(os.getenv("DEVICES_POR_ZONA", "1"))
INTERVALO     = int(os.getenv("INTERVALO_SEG", "15"))
ANOMALIA_PROB = float(os.getenv("ANOMALIA_PROB", "0.06"))   # prob. de INICIAR una anomalia
ANOMALIA_CICLOS = (3, 7)                                     # cuantos ciclos dura

ANOMALIA_DE_TIPO = {"agua": "fuga", "luz": "pico", "aire": "contaminacion"}


def construir_dispositivos():
    """Arma la lista de dispositivos simulados: uno de cada tipo (luz/agua/
    aire) por cada zona configurada. Cada dispositivo es solo un diccionario
    en memoria, con un contador 'anomalo' que arranca en 0 (comportamiento
    normal) y se usa mas abajo en main() para saber si esta en medio de una
    anomalia sostenida."""
    devs = []
    for zona in ZONAS:
        for tipo in TIPOS:
            for i in range(DEV_POR_ZONA):
                devs.append({
                    "id": f"{tipo}-{zona}-{i + 1:02d}",
                    "zona": zona, "tipo": tipo,
                    "anomalo": 0,          # ciclos de anomalia que quedan
                })
    return devs


def conectar(cli):
    """Reintenta la conexion al broker cada 5s hasta lograrlo. Hace falta
    porque en Kubernetes los pods pueden arrancar en cualquier orden: si el
    simulador arranca antes que mosquitto, no se cae, simplemente espera."""
    while True:
        try:
            cli.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            return
        except OSError as e:
            print(f"simulador: broker no disponible ({e}), reintento en 5s", flush=True)
            time.sleep(5)


def main():
    devices = construir_dispositivos()
    cli = mqtt.Client(client_id="device-simulator")
    conectar(cli)
    cli.loop_start()
    print(f"simulador: {len(devices)} dispositivos en {len(ZONAS)} zonas, "
          f"cada {INTERVALO}s -> {MQTT_HOST}:{MQTT_PORT}", flush=True)

    # Bucle infinito: una vez por INTERVALO_SEG (15s por defecto), genera y
    # publica una lectura de CADA dispositivo.
    while True:
        ahora = datetime.now(timezone.utc)
        hour = ahora.hour + ahora.minute / 60.0  # hora en decimal, ej 14.5 = 14:30
        for d in devices:
            # Si el dispositivo esta "sano" (anomalo == 0), tiene una chance
            # de ANOMALIA_PROB de arrancar una anomalia nueva este ciclo, que
            # va a durar entre 3 y 7 ciclos seguidos (para que se vea sostenida
            # en el panel, no un parpadeo de una sola lectura).
            if d["anomalo"] == 0 and random.random() < ANOMALIA_PROB:
                d["anomalo"] = random.randint(*ANOMALIA_CICLOS)
                print(f"simulador: {d['id']} entra en anomalia ({d['anomalo']} ciclos)", flush=True)

            valor = base_reading(d["tipo"], hour)
            if d["anomalo"] > 0:
                # Sigue en anomalia: se deforma el valor y se descuenta un
                # ciclo. Cuando llegue a 0, vuelve a comportarse normal.
                valor = inject_anomaly(d["tipo"], valor, ANOMALIA_DE_TIPO[d["tipo"]])
                d["anomalo"] -= 1

            payload = {
                "ts": ahora.isoformat(),
                "device_id": d["id"], "zona": d["zona"], "tipo": d["tipo"],
                "valor": valor, "unidad": TIPOS[d["tipo"]]["unidad"],
            }
            # qos=0 ("como mucho una vez"): el nivel mas liviano de MQTT, sin
            # confirmacion de entrega - perder una lectura suelta no importa
            # porque en 15s llega la siguiente.
            cli.publish(f"ciudad/{d['zona']}/{d['tipo']}/{d['id']}", json.dumps(payload), qos=0)
        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
