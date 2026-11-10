"""Reglas locales explícitas; no deducen géneros a partir de palabras sueltas."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from biblioteca.dominio.clasificacion import (
    DecisionClasificacion, EstadoClasificacion, MetodoClasificacion, TipoClasificacion,
)
from biblioteca.dominio.validacion import texto_obligatorio, validar_uuid
from biblioteca.errores import ErrorValidacion


def normalizar_materia(texto: str) -> str:
    return " ".join(texto.split()).casefold()


@dataclass(frozen=True)
class ReglaClasificacion:
    id: str
    version: str
    materia: str
    termino_id: UUID
    aprobacion_automatica: bool = True

    def __post_init__(self) -> None:
        for campo in ("id", "version", "materia"):
            object.__setattr__(self, campo, texto_obligatorio(getattr(self, campo), campo))
        object.__setattr__(self, "termino_id", validar_uuid(self.termino_id))
        if type(self.aprobacion_automatica) is not bool:
            raise ErrorValidacion("La aprobación automática debe ser booleana.")

    def evaluar(self, materia: str, contexto: tuple[str, ...], tipo: TipoClasificacion,
                fecha: datetime) -> DecisionClasificacion | None:
        if normalizar_materia(materia) != normalizar_materia(self.materia):
            return None
        # Política conservadora: una obra sobre un género no es necesariamente de él.
        marcadores = ("criticism", "crítica", "critica", "study and teaching", "adaptations", "adaptaciones")
        contexto_dudoso = tipo is TipoClasificacion.GENERO and any(
            marcador in normalizar_materia(texto) for texto in contexto for marcador in marcadores
        )
        aprobar = self.aprobacion_automatica and not contexto_dudoso
        motivo = ("Correspondencia exacta autorizada por la regla." if aprobar else
                  "Correspondencia candidata; requiere revisión por contexto o política de la regla.")
        return DecisionClasificacion(
            EstadoClasificacion.APROBADO if aprobar else EstadoClasificacion.PROPUESTO,
            MetodoClasificacion.AUTOMATICO, motivo, fecha, self.id, self.version,
        )
