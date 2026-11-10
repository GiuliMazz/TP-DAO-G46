"""Copia física: identidad, propiedad y disponibilidad propia, sin SQLite."""

from enum import Enum
from uuid import UUID, uuid4

from biblioteca.dominio.validacion import texto_obligatorio, validar_uuid
from biblioteca.errores import ErrorValidacion


class CondicionFisica(str, Enum):
    APTO = "APTO"
    DANIADO = "DANIADO"
    DESTRUIDO = "DESTRUIDO"


class SituacionOperativa(str, Enum):
    LIBRE = "LIBRE"
    BAJA = "BAJA"


def normalizar_codigo_inventario(codigo: str) -> str:
    normalizado = texto_obligatorio(codigo, "Código de inventario").upper()
    if any(c.isspace() or not c.isprintable() for c in normalizado):
        raise ErrorValidacion("El código de inventario no admite espacios internos ni controles.")
    return normalizado


class Ejemplar:
    def __init__(
        self, codigo_inventario: str, edicion_id: UUID | str,
        sede_propietaria_id: UUID | str, *, sede_actual_id: UUID | str | None,
        id: UUID | None = None, condicion_fisica: CondicionFisica = CondicionFisica.APTO,
        situacion_operativa: SituacionOperativa = SituacionOperativa.LIBRE,
    ) -> None:
        if not isinstance(condicion_fisica, CondicionFisica):
            raise ErrorValidacion("La condición física no es válida.")
        if not isinstance(situacion_operativa, SituacionOperativa):
            raise ErrorValidacion("La situación operativa no es válida.")
        self._id = uuid4() if id is None else validar_uuid(id)
        self._codigo_inventario = normalizar_codigo_inventario(codigo_inventario)
        self._edicion_id = validar_uuid(edicion_id)
        self._sede_propietaria_id = validar_uuid(sede_propietaria_id)
        self._sede_actual_id = validar_uuid(sede_actual_id) if sede_actual_id is not None else None
        self._condicion_fisica = condicion_fisica
        self._situacion_operativa = situacion_operativa

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def codigo_inventario(self) -> str:
        return self._codigo_inventario

    @property
    def edicion_id(self) -> UUID:
        return self._edicion_id

    @property
    def sede_propietaria_id(self) -> UUID:
        return self._sede_propietaria_id

    @property
    def sede_actual_id(self) -> UUID | None:
        return self._sede_actual_id

    @property
    def condicion_fisica(self) -> CondicionFisica:
        return self._condicion_fisica

    @property
    def situacion_operativa(self) -> SituacionOperativa:
        return self._situacion_operativa

    def esta_disponible(self) -> bool:
        """Disponibilidad propia para nueva asignación; el servicio valida la sede."""
        return (
            self.situacion_operativa is SituacionOperativa.LIBRE
            and self.condicion_fisica is CondicionFisica.APTO
            and self.sede_actual_id == self.sede_propietaria_id
        )

    def registrar_condicion(self, condicion: CondicionFisica) -> None:
        if not isinstance(condicion, CondicionFisica):
            raise ErrorValidacion("La condición física no es válida.")
        if self.condicion_fisica is CondicionFisica.DESTRUIDO and condicion is not CondicionFisica.DESTRUIDO:
            raise ErrorValidacion("Un ejemplar destruido no puede volver a declararse apto o dañado.")
        self._condicion_fisica = condicion

    def dar_de_baja(self) -> None:
        self._situacion_operativa = SituacionOperativa.BAJA
