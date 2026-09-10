"""Esquema de una lectura de telemetria. Todo lo que entra se valida contra esto."""
from typing import Literal

from pydantic import BaseModel, field_validator


class Reading(BaseModel):
    ts: str                                  # ISO-8601
    device_id: str
    zona: str
    tipo: Literal["luz", "agua", "aire"]     # rechaza tipos desconocidos
    valor: float
    unidad: str

    @field_validator("valor")
    @classmethod
    def no_negativo(cls, v: float) -> float:
        if v < 0:
            raise ValueError("el valor no puede ser negativo")
        return v

    @field_validator("device_id", "zona")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("campo vacio")
        return v
