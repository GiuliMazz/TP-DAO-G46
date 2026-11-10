"""Publicación de una obra; los estados técnicos OL no pertenecen a esta entidad."""

from uuid import UUID, uuid4

from biblioteca.dominio.bibliografia import (
    entero_positivo_opcional, id_openlibrary as validar_id_ol, isbn13_desde_isbn10,
    normalizar_isbn, texto_opcional,
)
from biblioteca.dominio.validacion import texto_obligatorio, validar_uuid
from biblioteca.errores import ErrorValidacion


class Edicion:
    def __init__(
        self, obra_id: UUID | str, titulo: str, idioma: str = "spa", *,
        id: UUID | None = None, id_openlibrary: str | None = None,
        isbn_10: str | None = None, isbn_13: str | None = None,
        editorial: str | None = None, anio_publicacion: int | None = None,
        numero_paginas: int | None = None, portada_edicion_id: int | None = None,
        descripcion_es: str | None = None,
    ) -> None:
        self._id = uuid4() if id is None else validar_uuid(id)
        self._obra_id = validar_uuid(obra_id)
        self._id_openlibrary = validar_id_ol(id_openlibrary, "M")
        self.actualizar_datos(
            titulo, idioma, isbn_10=isbn_10, isbn_13=isbn_13, editorial=editorial,
            anio_publicacion=anio_publicacion, numero_paginas=numero_paginas,
            portada_edicion_id=portada_edicion_id, descripcion_es=descripcion_es,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def obra_id(self) -> UUID:
        return self._obra_id

    @property
    def id_openlibrary(self) -> str | None:
        return self._id_openlibrary

    @property
    def titulo(self) -> str:
        return self._titulo

    @property
    def idioma(self) -> str:
        return self._idioma

    @property
    def isbn_10(self) -> str | None:
        return self._isbn_10

    @property
    def isbn_13(self) -> str | None:
        return self._isbn_13

    @property
    def isbn_canonico(self) -> str | None:
        return self.isbn_13 or (isbn13_desde_isbn10(self.isbn_10) if self.isbn_10 else None)

    @property
    def editorial(self) -> str | None:
        return self._editorial

    @property
    def anio_publicacion(self) -> int | None:
        return self._anio_publicacion

    @property
    def numero_paginas(self) -> int | None:
        return self._numero_paginas

    @property
    def portada_edicion_id(self) -> int | None:
        return self._portada_edicion_id

    @property
    def descripcion_es(self) -> str | None:
        return self._descripcion_es

    def actualizar_datos(
        self, titulo: str, idioma: str = "spa", *,
        isbn_10: str | None = None, isbn_13: str | None = None,
        editorial: str | None = None, anio_publicacion: int | None = None,
        numero_paginas: int | None = None, portada_edicion_id: int | None = None,
        descripcion_es: str | None = None,
    ) -> None:
        titulo = texto_obligatorio(titulo, "Título de edición")
        if idioma != "spa":
            raise ErrorValidacion("El catálogo inicial admite ediciones en español (spa).")
        i10, i13 = normalizar_isbn(isbn_10, 10), normalizar_isbn(isbn_13, 13)
        if i10 and i13 and isbn13_desde_isbn10(i10) != i13:
            raise ErrorValidacion("Los ISBN-10 e ISBN-13 no corresponden entre sí.")
        datos = (
            titulo, idioma, i10, i13, texto_opcional(editorial, "Editorial"),
            entero_positivo_opcional(anio_publicacion, "Año de publicación"),
            entero_positivo_opcional(numero_paginas, "Número de páginas"),
            entero_positivo_opcional(portada_edicion_id, "Portada de edición"),
            texto_opcional(descripcion_es, "Descripción en español"),
        )
        (self._titulo, self._idioma, self._isbn_10, self._isbn_13, self._editorial,
         self._anio_publicacion, self._numero_paginas, self._portada_edicion_id,
         self._descripcion_es) = datos
