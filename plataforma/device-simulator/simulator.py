"""device-simulator - hace de medidores IoT de una ciudad y publica por MQTT.

Representa la "ultima milla": dispositivos NB-IoT/LoRaWAN mandando telemetria.
Config por variables de entorno (ver abajo). Publica en:
    ciudad/{zona}/{tipo}/{device_id}
con un JSON  {ts, device_id, zona, tipo, valor, unidad}
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
ANOMALIA_PROB = float(os.getenv("ANOMALIA_PROB", "0.03"))

ANOMALIA_DE_TIPO = {"agua": "fuga", "luz": "pico", "aire": "contaminacion"}


def construir_dispositivos():
    devs = []
    for zona in ZONAS:
        for tipo in TIPOS:
            for i in range(DEV_POR_ZONA):
                devs.append({"id": f"{tipo}-{zona}-{i + 1:02d}", "zona": zona, "tipo": tipo})
    return devs


def main():
    devices = construir_dispositivos()
    cli = mqtt.Client(client_id="device-simulator")
    cli.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    cli.loop_start()
    print(f"simulador: {len(devices)} dispositivos en {len(ZONAS)} zonas, "
          f"cada {INTERVALO}s -> {MQTT_HOST}:{MQTT_PORT}", flush=True)

    while True:
        ahora = datetime.now(timezone.utc)
        hour = ahora.hour + ahora.minute / 60.0
        for d in devices:
            valor = base_reading(d["tipo"], hour)
            if random.random() < ANOMALIA_PROB:
                valor = inject_anomaly(d["tipo"], valor, ANOMALIA_DE_TIPO[d["tipo"]])
            payload = {
                "ts": ahora.isoformat(),
                "device_id": d["id"],
                "zona": d["zona"],
                "tipo": d["tipo"],
                "valor": valor,
                "unidad": TIPOS[d["tipo"]]["unidad"],
            }
            topic = f"ciudad/{d['zona']}/{d['tipo']}/{d['id']}"
            cli.publish(topic, json.dumps(payload), qos=0)
        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
