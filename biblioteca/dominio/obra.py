"""Obra intelectual, autoría y elección de edición para mostrar en el catálogo."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from biblioteca.dominio.bibliografia import (
    entero_positivo_opcional, id_openlibrary as validar_id_ol, texto_opcional,
)
from biblioteca.dominio.validacion import texto_obligatorio, validar_uuid
from biblioteca.errores import ErrorValidacion

if TYPE_CHECKING:
    from biblioteca.dominio.edicion import Edicion


class Obra:
    def __init__(
        self, titulo_original: str, autor_ids: Iterable[UUID | str] = (), *,
        id: UUID | None = None, id_openlibrary: str | None = None,
        descripcion_original: str | None = None, anio_primera_publicacion: int | None = None,
        portada_obra_id: int | None = None, edicion_preferida_id: UUID | None = None,
    ) -> None:
        self._id = uuid4() if id is None else validar_uuid(id)
        self._id_openlibrary = validar_id_ol(id_openlibrary, "W")
        self._edicion_preferida_id = (
            validar_uuid(edicion_preferida_id) if edicion_preferida_id is not None else None
        )
        self.reemplazar_autores(autor_ids)
        self.actualizar_datos(
            titulo_original, descripcion_original=descripcion_original,
            anio_primera_publicacion=anio_primera_publicacion, portada_obra_id=portada_obra_id,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def id_openlibrary(self) -> str | None:
        return self._id_openlibrary

    @property
    def titulo_original(self) -> str:
        return self._titulo_original

    @property
    def descripcion_original(self) -> str | None:
        return self._descripcion_original

    @property
    def anio_primera_publicacion(self) -> int | None:
        return self._anio_primera_publicacion

    @property
    def portada_obra_id(self) -> int | None:
        return self._portada_obra_id

    @property
    def autor_ids(self) -> tuple[UUID, ...]:
        return self._autor_ids

    @property
    def edicion_preferida_id(self) -> UUID | None:
        return self._edicion_preferida_id

    def actualizar_datos(
        self, titulo_original: str, *, descripcion_original: str | None = None,
        anio_primera_publicacion: int | None = None, portada_obra_id: int | None = None,
    ) -> None:
        datos = (
            texto_obligatorio(titulo_original, "Título original"),
            texto_opcional(descripcion_original, "Descripción original"),
            entero_positivo_opcional(anio_primera_publicacion, "Año de la obra"),
            entero_positivo_opcional(portada_obra_id, "Portada de obra"),
        )
        (self._titulo_original, self._descripcion_original,
         self._anio_primera_publicacion, self._portada_obra_id) = datos

    def reemplazar_autores(self, autor_ids: Iterable[UUID | str]) -> None:
        if isinstance(autor_ids, (str, bytes)):
            raise ErrorValidacion("Los autores deben indicarse como una colección de identificadores.")
        try:
            nuevos = tuple(dict.fromkeys(validar_uuid(id) for id in autor_ids))
        except TypeError as error:
            raise ErrorValidacion("Se requiere una colección de autores.") from error
        self._autor_ids = nuevos

    def vincular_autor(self, autor_id: UUID | str) -> None:
        id = validar_uuid(autor_id)
        if id not in self._autor_ids:
            self._autor_ids += (id,)

    def desvincular_autor(self, autor_id: UUID | str) -> None:
        id = validar_uuid(autor_id)
        if id in self._autor_ids and len(self._autor_ids) == 1:
            raise ErrorValidacion("No se puede quitar el último autor identificado de la obra.")
        self._autor_ids = tuple(actual for actual in self._autor_ids if actual != id)

    def seleccionar_edicion(self, edicion: Edicion) -> None:
        if edicion.obra_id != self.id or edicion.idioma != "spa":
            raise ErrorValidacion("La edición preferida debe ser española y pertenecer a esta obra.")
        self._edicion_preferida_id = edicion.id
