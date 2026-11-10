"""Resumen de disponibilidad sin cargar todas las copias de una obra."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DisponibilidadSede:
    obra_id: UUID
    sede_id: UUID
    nombre_sede: str
    sede_activa: bool
    total_propios: int
    total_ubicados: int
    bajas_ubicadas: int
    disponibles: int
