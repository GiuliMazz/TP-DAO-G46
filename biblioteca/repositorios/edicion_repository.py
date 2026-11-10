"""Ediciones, ISBN para detectar coincidencias y páginas por obra."""

import sqlite3
from uuid import UUID

from biblioteca.dominio.edicion import Edicion
from biblioteca.errores import RegistroNoEncontrado
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.repositorios.consultas import validar_paginacion


class EdicionRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def agregar(self, edicion: Edicion) -> None:
        ejecutar(self.conexion,
                 """INSERT INTO edicion (id, obra_id, id_openlibrary, titulo, titulo_normalizado,
                    idioma, isbn_10, isbn_13, isbn_canonico, editorial, anio_publicacion,
                    numero_paginas, portada_edicion_id, descripcion_es)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (str(edicion.id), str(edicion.obra_id), edicion.id_openlibrary,
                  *self._datos(edicion)))

    def actualizar(self, edicion: Edicion) -> None:
        cursor = ejecutar(self.conexion,
                          """UPDATE edicion SET titulo = ?, titulo_normalizado = ?, idioma = ?,
                             isbn_10 = ?, isbn_13 = ?, isbn_canonico = ?, editorial = ?,
                             anio_publicacion = ?, numero_paginas = ?, portada_edicion_id = ?,
                             descripcion_es = ? WHERE id = ? AND obra_id = ?""",
                          (*self._datos(edicion), str(edicion.id), str(edicion.obra_id)))
        if cursor.rowcount != 1:
            raise RegistroNoEncontrado("La edición no existe o pertenece a otra obra.")

    def obtener(self, id: UUID) -> Edicion | None:
        fila = ejecutar(self.conexion, "SELECT * FROM edicion WHERE id = ?", (str(id),)).fetchone()
        return self._reconstruir(fila) if fila else None

    def buscar_por_openlibrary(self, id_ol: str) -> Edicion | None:
        fila = ejecutar(self.conexion, "SELECT * FROM edicion WHERE id_openlibrary = ?", (id_ol,)).fetchone()
        return self._reconstruir(fila) if fila else None

    def coincidencias_isbn(self, canonico: str, excluir: UUID | None = None) -> tuple[UUID, ...]:
        filas = ejecutar(self.conexion,
                         "SELECT id FROM edicion WHERE isbn_canonico = ? AND id != ? ORDER BY id",
                         (canonico, str(excluir) if excluir else "")).fetchall()
        return tuple(UUID(fila["id"]) for fila in filas)

    def contar_para_obra(self, obra_id: UUID) -> int:
        return ejecutar(self.conexion, "SELECT COUNT(*) FROM edicion WHERE obra_id = ?",
                        (str(obra_id),)).fetchone()[0]

    def preferida_para_obra(self, obra_id: UUID) -> Edicion | None:
        fila = ejecutar(self.conexion,
                         """SELECT e.* FROM edicion e JOIN obra o ON o.id = e.obra_id
                            WHERE o.id = ? AND e.idioma = 'spa'
                            ORDER BY CASE WHEN e.id = o.edicion_preferida_id THEN 0 ELSE 1 END,
                                     e.id LIMIT 1""", (str(obra_id),)).fetchone()
        return self._reconstruir(fila) if fila else None

    def listar_para_obra(self, obra_id: UUID, *, limite: int = 50,
                        desplazamiento: int = 0) -> list[Edicion]:
        validar_paginacion(limite, desplazamiento)
        filas = ejecutar(self.conexion,
                         "SELECT * FROM edicion WHERE obra_id = ? ORDER BY id LIMIT ? OFFSET ?",
                         (str(obra_id), limite, desplazamiento)).fetchall()
        return [self._reconstruir(fila) for fila in filas]

    @staticmethod
    def _datos(edicion: Edicion) -> tuple[object, ...]:
        return (edicion.titulo, edicion.titulo.casefold(), edicion.idioma,
                edicion.isbn_10, edicion.isbn_13, edicion.isbn_canonico, edicion.editorial,
                edicion.anio_publicacion, edicion.numero_paginas,
                edicion.portada_edicion_id, edicion.descripcion_es)

    @staticmethod
    def _reconstruir(fila: sqlite3.Row) -> Edicion:
        return Edicion(
            fila["obra_id"], fila["titulo"], fila["idioma"], id=UUID(fila["id"]),
            id_openlibrary=fila["id_openlibrary"], isbn_10=fila["isbn_10"], isbn_13=fila["isbn_13"],
            editorial=fila["editorial"], anio_publicacion=fila["anio_publicacion"],
            numero_paginas=fila["numero_paginas"], portada_edicion_id=fila["portada_edicion_id"],
            descripcion_es=fila["descripcion_es"],
        )
