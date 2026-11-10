"""Casos de uso bibliográficos; sin SQL ni fases de validación de Open Library."""

from collections.abc import Iterable
from uuid import UUID

from biblioteca.dominio.autor import Autor
from biblioteca.dominio.edicion import Edicion
from biblioteca.dominio.obra import Obra
from biblioteca.dominio.validacion import validar_uuid
from biblioteca.errores import (
    ErrorValidacion, PosibleDuplicado, RegistroDuplicado, RegistroNoEncontrado,
)
from biblioteca.persistencia.base_datos import lectura_consistente, transaccion
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.resultados_catalogo import DetalleObra, FichaObra, PaginaCatalogo


class CatalogoService:
    def __init__(self, obras: ObraRepository, ediciones: EdicionRepository,
                 autores: AutorRepository) -> None:
        if obras.conexion is not ediciones.conexion or obras.conexion is not autores.conexion:
            raise ErrorValidacion("Los repositorios del catálogo deben compartir la misma conexión.")
        self._obras, self._ediciones, self._autores = obras, ediciones, autores
        self._conexion = obras.conexion

    def registrar_autor(self, nombre: str, *, id_openlibrary: str | None = None) -> Autor:
        autor = Autor(nombre, id_openlibrary=id_openlibrary)
        with transaccion(self._conexion):
            self._autores.agregar(autor)
        return autor

    def obtener_autor(self, id: UUID | str) -> Autor:
        autor = self._autores.obtener(validar_uuid(id))
        if autor is None:
            raise RegistroNoEncontrado("El autor no existe.")
        return autor

    def modificar_autor(self, id: UUID | str, nombre: str) -> Autor:
        with transaccion(self._conexion):
            autor = self.obtener_autor(id)
            autor.actualizar_nombre(nombre)
            self._autores.actualizar(autor)
        return autor

    def listar_autores(self, *, nombre: str | None = None, limite: int = 50,
                       desplazamiento: int = 0) -> list[Autor]:
        return self._autores.listar(nombre=nombre, limite=limite, desplazamiento=desplazamiento)

    def registrar_obra(
        self, titulo_original: str, autor_ids: Iterable[UUID | str], *,
        id_openlibrary: str | None = None, descripcion_original: str | None = None,
        anio_primera_publicacion: int | None = None, portada_obra_id: int | None = None,
        confirmar_distinta: bool = False,
    ) -> Obra:
        obra = Obra(titulo_original, autor_ids, id_openlibrary=id_openlibrary,
                    descripcion_original=descripcion_original,
                    anio_primera_publicacion=anio_primera_publicacion, portada_obra_id=portada_obra_id)
        with transaccion(self._conexion):
            self._comprobar_obra(obra, confirmar_distinta)
            self._obras.agregar(obra)
        return obra

    def obtener_obra(self, id: UUID | str) -> Obra:
        obra = self._obras.obtener(validar_uuid(id))
        if obra is None:
            raise RegistroNoEncontrado("La obra no existe.")
        return obra

    def modificar_obra(
        self, id: UUID | str, titulo_original: str, autor_ids: Iterable[UUID | str], *,
        descripcion_original: str | None = None, anio_primera_publicacion: int | None = None,
        portada_obra_id: int | None = None, confirmar_distinta: bool = False,
    ) -> Obra:
        with transaccion(self._conexion):
            obra = self.obtener_obra(id)
            obra.actualizar_datos(titulo_original, descripcion_original=descripcion_original,
                                  anio_primera_publicacion=anio_primera_publicacion,
                                  portada_obra_id=portada_obra_id)
            obra.reemplazar_autores(autor_ids)
            self._comprobar_obra(obra, confirmar_distinta)
            self._obras.actualizar(obra)
        return obra

    def registrar_edicion(
        self, obra_id: UUID | str, titulo: str, idioma: str = "spa", *,
        id_openlibrary: str | None = None, isbn_10: str | None = None,
        isbn_13: str | None = None, editorial: str | None = None,
        anio_publicacion: int | None = None, numero_paginas: int | None = None,
        portada_edicion_id: int | None = None, descripcion_es: str | None = None,
        confirmar_distinta: bool = False,
    ) -> Edicion:
        edicion = Edicion(obra_id, titulo, idioma, id_openlibrary=id_openlibrary,
                          isbn_10=isbn_10, isbn_13=isbn_13, editorial=editorial,
                          anio_publicacion=anio_publicacion, numero_paginas=numero_paginas,
                          portada_edicion_id=portada_edicion_id, descripcion_es=descripcion_es)
        with transaccion(self._conexion):
            obra = self.obtener_obra(edicion.obra_id)
            self._comprobar_edicion(edicion, confirmar_distinta)
            self._ediciones.agregar(edicion)
            if obra.edicion_preferida_id is None:
                obra.seleccionar_edicion(edicion)
                self._obras.actualizar(obra)
        return edicion

    def obtener_edicion(self, id: UUID | str) -> Edicion:
        edicion = self._ediciones.obtener(validar_uuid(id))
        if edicion is None:
            raise RegistroNoEncontrado("La edición no existe.")
        return edicion

    def modificar_edicion(
        self, id: UUID | str, titulo: str, idioma: str = "spa", *,
        isbn_10: str | None = None, isbn_13: str | None = None,
        editorial: str | None = None, anio_publicacion: int | None = None,
        numero_paginas: int | None = None, portada_edicion_id: int | None = None,
        descripcion_es: str | None = None, confirmar_distinta: bool = False,
    ) -> Edicion:
        with transaccion(self._conexion):
            edicion = self.obtener_edicion(id)
            edicion.actualizar_datos(titulo, idioma, isbn_10=isbn_10, isbn_13=isbn_13,
                                    editorial=editorial, anio_publicacion=anio_publicacion,
                                    numero_paginas=numero_paginas,
                                    portada_edicion_id=portada_edicion_id, descripcion_es=descripcion_es)
            self._comprobar_edicion(edicion, confirmar_distinta)
            self._ediciones.actualizar(edicion)
        return edicion

    def registrar_libro(self, obra: Obra, edicion: Edicion, *,
                        confirmar_distinta: bool = False) -> DetalleObra:
        """Alta conjunta de obra/relaciones/primera edición, ya construidas y validadas.

        Recibe entidades nuevas y devuelve una lectura de lo persistido; no modifica
        los objetos del llamador. Los autores deben estar registrados previamente.
        """
        if edicion.obra_id != obra.id:
            raise ErrorValidacion("La primera edición debe pertenecer a la obra que se registra.")
        if obra.edicion_preferida_id not in (None, edicion.id):
            raise ErrorValidacion("La preferida del alta conjunta debe ser su primera edición.")
        with transaccion(self._conexion):
            self._comprobar_obra(obra, confirmar_distinta)
            self._comprobar_edicion(edicion, confirmar_distinta)
            self._obras.agregar(obra)
            self._ediciones.agregar(edicion)
            guardada = self.obtener_obra(obra.id)
            guardada.seleccionar_edicion(edicion)
            self._obras.actualizar(guardada)
        return self.obtener_detalle(obra.id)

    def seleccionar_edicion_preferida(self, obra_id: UUID | str,
                                     edicion_id: UUID | str) -> Obra:
        with transaccion(self._conexion):
            obra = self.obtener_obra(obra_id)
            obra.seleccionar_edicion(self.obtener_edicion(edicion_id))
            self._obras.actualizar(obra)
        return obra

    def obtener_detalle(self, obra_id: UUID | str) -> DetalleObra:
        obra = self.obtener_obra(obra_id)
        return DetalleObra(obra, self._autores.para_obra(obra.id),
                           self._ediciones.preferida_para_obra(obra.id),
                           self._ediciones.contar_para_obra(obra.id))

    def listar_obras(self, *, titulo: str | None = None, autor: str | None = None,
                     genero_id: UUID | str | None = None, etiqueta_id: UUID | str | None = None,
                     publico_id: UUID | str | None = None,
                     limite: int = 50, desplazamiento: int = 0) -> list[FichaObra]:
        return self._obras.listar(titulo=titulo, autor=autor,
                                  genero_id=genero_id, etiqueta_id=etiqueta_id, publico_id=publico_id,
                                  limite=limite, desplazamiento=desplazamiento)

    def listar_ediciones(self, obra_id: UUID | str, *, limite: int = 50,
                        desplazamiento: int = 0) -> list[Edicion]:
        id = validar_uuid(obra_id)
        self.obtener_obra(id)
        return self._ediciones.listar_para_obra(id, limite=limite, desplazamiento=desplazamiento)

    def consultar_pagina(
        self, *, texto: str | None = None, genero_id: UUID | str | None = None,
        sede_id: UUID | str | None = None, disponibles: bool | None = None,
        limite: int = 24, desplazamiento: int = 0,
    ) -> PaginaCatalogo:
        """Leer total y página coherentes, sin bloquear escritores con BEGIN IMMEDIATE.

        Si el llamador ya posee una transacción, no confirmarla ni revertirla.
        La lectura independiente se cierra incluso cuando un filtro falla.
        """
        with lectura_consistente(self._conexion):
            return self._obras.consultar_pagina(texto=texto, genero_id=genero_id, sede_id=sede_id,
                disponibles=disponibles, limite=limite, desplazamiento=desplazamiento)

    def _comprobar_obra(self, obra: Obra, confirmar_distinta: bool) -> None:
        self._validar_confirmacion(confirmar_distinta)
        if not obra.autor_ids:
            raise ErrorValidacion("El alta requiere al menos un autor identificado.")
        for id in obra.autor_ids:
            self.obtener_autor(id)
        if obra.id_openlibrary:
            existente = self._obras.buscar_por_openlibrary(obra.id_openlibrary)
            if existente is not None and existente.id != obra.id:
                raise RegistroDuplicado("El ID de obra de Open Library ya está registrado.")
        if not confirmar_distinta and self._obras.coincidencias(obra):
            raise PosibleDuplicado(
                "Ya hay una obra con ese título y autores. Revise si corresponde usarla; "
                "confirmar_distinta=True sólo permite continuar tras comprobar que es otra obra."
            )

    def _comprobar_edicion(self, edicion: Edicion, confirmar_distinta: bool) -> None:
        self._validar_confirmacion(confirmar_distinta)
        if edicion.id_openlibrary:
            existente = self._ediciones.buscar_por_openlibrary(edicion.id_openlibrary)
            if existente is not None and existente.id != edicion.id:
                raise RegistroDuplicado("El ID de edición de Open Library ya está registrado.")
        if (not confirmar_distinta and edicion.isbn_canonico
                and self._ediciones.coincidencias_isbn(edicion.isbn_canonico, edicion.id)):
            raise PosibleDuplicado(
                "El ISBN coincide con una edición registrada. Revísela antes de confirmar otra distinta."
            )

    @staticmethod
    def _validar_confirmacion(valor: bool) -> None:
        if not isinstance(valor, bool):
            raise ErrorValidacion("La confirmación de obra o edición distinta debe ser booleana.")
