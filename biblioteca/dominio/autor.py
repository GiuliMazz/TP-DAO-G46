"""Identidad bibliográfica de un autor; el nombre no es una clave única."""

from uuid import UUID, uuid4

from biblioteca.dominio.bibliografia import id_openlibrary as validar_id_ol
from biblioteca.dominio.validacion import texto_obligatorio, validar_uuid


class Autor:
    def __init__(self, nombre: str, *, id: UUID | None = None,
                 id_openlibrary: str | None = None) -> None:
        self._id = uuid4() if id is None else validar_uuid(id)
        self._id_openlibrary = validar_id_ol(id_openlibrary, "A")
        self.actualizar_nombre(nombre)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def id_openlibrary(self) -> str | None:
        return self._id_openlibrary

    def actualizar_nombre(self, nombre: str) -> None:
        self._nombre = texto_obligatorio(nombre, "Nombre del autor")
