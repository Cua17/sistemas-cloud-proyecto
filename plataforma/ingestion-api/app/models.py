"""Esquema de una lectura de telemetria. Todo lo que entra se valida contra esto.

Pydantic (BaseModel) es lo que hace la validacion: se le pasa un diccionario
(el JSON que llego por MQTT) y, si no calza con lo que se define aca abajo,
tira una excepcion en vez de dejar pasar datos raros hacia la base de datos.
Es la frontera de confianza del sistema: todo lo que entra por MQTT se trata
como sospechoso hasta que pasa por esta clase."""
from typing import Literal

from pydantic import BaseModel, field_validator


class Reading(BaseModel):
    ts: str                                  # ISO-8601
    device_id: str
    zona: str
    tipo: Literal["luz", "agua", "aire"]     # rechaza cualquier otro tipo (ej. "gas")
    valor: float
    unidad: str

    @field_validator("valor")
    @classmethod
    def no_negativo(cls, v: float) -> float:
        """Un consumo o una medicion de aire nunca puede ser negativa - si
        llegara un valor asi, es un dato corrupto y se rechaza directo."""
        if v < 0:
            raise ValueError("el valor no puede ser negativo")
        return v

    @field_validator("device_id", "zona")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        """Evita que se cuele un device_id o zona vacios/solo-espacios, que
        romperian las consultas que agrupan por estos campos."""
        if not v or not v.strip():
            raise ValueError("campo vacio")
        return v
