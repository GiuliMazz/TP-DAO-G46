"""Vocabularios separados y decisiones revisables sobre una obra."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar
from uuid import UUID, uuid4

from biblioteca.dominio.validacion import texto_obligatorio, validar_uuid
from biblioteca.errores import ErrorValidacion


class TipoClasificacion(str, Enum):
    GENERO = "GENERO"
    ETIQUETA = "ETIQUETA"
    PUBLICO = "PUBLICO"


class EstadoClasificacion(str, Enum):
    PROPUESTO = "PROPUESTO"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"


class MetodoClasificacion(str, Enum):
    MANUAL = "MANUAL"
    AUTOMATICO = "AUTOMATICO"


@dataclass(frozen=True)
class TerminoClasificacion:
    nombre: str
    id: UUID | None = None
    tipo: ClassVar[TipoClasificacion]

    def __post_init__(self) -> None:
        if type(self) is TerminoClasificacion:
            raise ErrorValidacion("Use Genero, Etiqueta o PublicoDestinatario.")
        object.__setattr__(self, "nombre", texto_obligatorio(self.nombre, "Nombre"))
        object.__setattr__(self, "id", uuid4() if self.id is None else validar_uuid(self.id))


@dataclass(frozen=True)
class Genero(TerminoClasificacion):
    tipo = TipoClasificacion.GENERO


@dataclass(frozen=True)
class Etiqueta(TerminoClasificacion):
    tipo = TipoClasificacion.ETIQUETA


@dataclass(frozen=True)
class PublicoDestinatario(TerminoClasificacion):
    tipo = TipoClasificacion.PUBLICO


@dataclass(frozen=True)
class DecisionClasificacion:
    estado: EstadoClasificacion
    metodo: MetodoClasificacion
    motivo: str
    fecha: datetime
    regla_id: str | None = None
    regla_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.estado, EstadoClasificacion) or not isinstance(self.metodo, MetodoClasificacion):
            raise ErrorValidacion("Estado y método de clasificación inválidos.")
        object.__setattr__(self, "motivo", texto_obligatorio(self.motivo, "Motivo"))
        if not isinstance(self.fecha, datetime) or self.fecha.utcoffset() is None:
            raise ErrorValidacion("La fecha debe incluir zona horaria.")
        object.__setattr__(self, "fecha", self.fecha.astimezone(timezone.utc))
        if self.metodo is MetodoClasificacion.AUTOMATICO:
            object.__setattr__(self, "regla_id", texto_obligatorio(self.regla_id, "Regla"))
            object.__setattr__(self, "regla_version", texto_obligatorio(self.regla_version, "Versión"))
            if self.estado is EstadoClasificacion.RECHAZADO:
                raise ErrorValidacion("Una regla no rechaza clasificaciones por ausencia de evidencia.")
        elif self.regla_id is not None or self.regla_version is not None:
            raise ErrorValidacion("Una decisión manual no debe atribuirse a una regla.")


class ClasificacionObra:
    def __init__(self, obra_id: UUID, termino: TerminoClasificacion,
                 decision: DecisionClasificacion) -> None:
        self._obra_id = validar_uuid(obra_id)
        if not isinstance(termino, TerminoClasificacion) or not isinstance(decision, DecisionClasificacion):
            raise ErrorValidacion("Término o decisión inválidos.")
        self._termino = termino
        self._decision = decision

    @property
    def obra_id(self) -> UUID:
        return self._obra_id

    @property
    def termino(self) -> TerminoClasificacion:
        return self._termino

    @property
    def decision(self) -> DecisionClasificacion:
        return self._decision

    def revisar(self, estado: EstadoClasificacion, motivo: str, fecha: datetime) -> None:
        if estado not in (EstadoClasificacion.APROBADO, EstadoClasificacion.RECHAZADO) or not isinstance(estado, EstadoClasificacion):
            raise ErrorValidacion("La revisión debe aprobar o rechazar explícitamente.")
        self._decision = DecisionClasificacion(estado, MetodoClasificacion.MANUAL, motivo, fecha)

    def aplicar_regla(self, decision: DecisionClasificacion) -> bool:
        if not isinstance(decision, DecisionClasificacion) or decision.metodo is not MetodoClasificacion.AUTOMATICO:
            raise ErrorValidacion("Se requiere una evaluación automática.")
        actual = self._decision
        if actual.metodo is MetodoClasificacion.MANUAL and actual.estado is not EstadoClasificacion.PROPUESTO:
            return False
        # Otra regla candidata no anula una aprobación. La misma regla sí puede
        # devolverla a revisión si cambia su versión o aparece contexto dudoso.
        if actual.estado is EstadoClasificacion.APROBADO and actual.regla_id != decision.regla_id:
            return False
        if (actual.estado, actual.metodo, actual.motivo, actual.regla_id, actual.regla_version) == (
            decision.estado, decision.metodo, decision.motivo, decision.regla_id, decision.regla_version
        ):
            return False
        self._decision = decision
        return True
