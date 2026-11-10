"""Socio identificado mediante DNI, sin asociación obligatoria a una sede."""

from enum import Enum
from uuid import UUID, uuid4

from biblioteca.dominio.validacion import normalizar_dni, texto_obligatorio, validar_uuid
from biblioteca.errores import ErrorValidacion


class EstadoSocio(str, Enum):
    HABILITADO = "HABILITADO"
    INHABILITADO = "INHABILITADO"


class Socio:
    def __init__(
        self,
        documento: str,
        nombre_completo: str,
        contacto: str,
        *,
        id: UUID | None = None,
        estado: EstadoSocio = EstadoSocio.HABILITADO,
    ) -> None:
        if not isinstance(estado, EstadoSocio):
            raise ErrorValidacion("El estado del socio no es válido.")
        self._id = uuid4() if id is None else validar_uuid(id)
        self.actualizar_datos(documento, nombre_completo, contacto)
        self._estado = estado

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def documento(self) -> str:
        return self._documento

    @property
    def nombre_completo(self) -> str:
        return self._nombre_completo

    @property
    def contacto(self) -> str:
        return self._contacto

    @property
    def estado(self) -> EstadoSocio:
        return self._estado

    def actualizar_datos(
        self, documento: str, nombre_completo: str, contacto: str
    ) -> None:
        datos = (
            normalizar_dni(documento),
            texto_obligatorio(nombre_completo, "Nombre completo"),
            texto_obligatorio(contacto, "Contacto"),
        )
        self._documento, self._nombre_completo, self._contacto = datos

    def habilitar(self) -> None:
        self._estado = EstadoSocio.HABILITADO

    def inhabilitar(self) -> None:
        self._estado = EstadoSocio.INHABILITADO

    def esta_habilitado(self) -> bool:
        return self._estado is EstadoSocio.HABILITADO
