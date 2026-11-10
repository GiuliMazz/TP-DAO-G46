"""Instantáneas y resultados técnicos de importación, separados del dominio."""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from uuid import UUID

from biblioteca.errores import ErrorValidacion


class EstadoImportacion(str, Enum):
    PENDIENTE = "PENDIENTE"
    ENRIQUECIDA = "ENRIQUECIDA"
    VALIDADA = "VALIDADA"
    RECHAZADA = "RECHAZADA"


def json_canonico(datos: object) -> str:
    return json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class CandidatoOpenLibrary:
    documento: str

    def __post_init__(self) -> None:
        try:
            datos = json.loads(self.documento)
            if not isinstance(datos, dict):
                raise ValueError()
            object.__setattr__(self, "documento", json_canonico(datos))
        except (ValueError, TypeError) as error:
            raise ErrorValidacion("La instantánea debe ser un objeto JSON válido.") from error

    @classmethod
    def desde_datos(cls, datos: dict) -> "CandidatoOpenLibrary":
        return cls(json_canonico(datos))

    @property
    def datos(self) -> dict:
        return json.loads(self.documento)

    @property
    def huella(self) -> str:
        return sha256(self.documento.encode("utf-8")).hexdigest()

    @property
    def clave(self) -> str:
        edicion = self.datos.get("edicion")
        id = edicion.get("id_openlibrary") if isinstance(edicion, dict) else None
        return id if isinstance(id, str) and id.strip() else "sin-id:" + self.huella


@dataclass(frozen=True)
class EvaluacionOpenLibrary:
    candidato: CandidatoOpenLibrary
    politica: str
    estado: EstadoImportacion
    controles: dict[str, bool]
    alertas: tuple[str, ...]
    normalizados: dict | None

    def puede_aprobar(self) -> bool:
        return (self.estado is not EstadoImportacion.RECHAZADA and bool(self.controles)
                and all(self.controles.values()) and self.normalizados is not None)


@dataclass(frozen=True)
class RegistroImportacion:
    edicion_ol: str
    ultima_evaluacion_id: int
    decision_id: int
    decision_evaluacion_id: int
    estado: EstadoImportacion
    metodo: str
    motivo: str
    edicion_local_id: UUID | None

    @property
    def tiene_cambios_sin_revisar(self) -> bool:
        return self.ultima_evaluacion_id != self.decision_evaluacion_id
