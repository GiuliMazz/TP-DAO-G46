"""Persistencia y consultas acotadas de autores."""

import sqlite3
from uuid import UUID

from biblioteca.dominio.autor import Autor
from biblioteca.errores import RegistroNoEncontrado
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.repositorios.consultas import filtro_nombre, validar_paginacion


class AutorRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def agregar(self, autor: Autor) -> None:
        ejecutar(self.conexion,
                 "INSERT INTO autor (id, id_openlibrary, nombre, nombre_normalizado) VALUES (?, ?, ?, ?)",
                 (str(autor.id), autor.id_openlibrary, autor.nombre, autor.nombre.casefold()))

    def actualizar(self, autor: Autor) -> None:
        cursor = ejecutar(self.conexion,
                          "UPDATE autor SET nombre = ?, nombre_normalizado = ? WHERE id = ?",
                          (autor.nombre, autor.nombre.casefold(), str(autor.id)))
        if cursor.rowcount != 1:
            raise RegistroNoEncontrado("El autor no existe.")

    def obtener(self, id: UUID) -> Autor | None:
        fila = ejecutar(self.conexion, "SELECT * FROM autor WHERE id = ?", (str(id),)).fetchone()
        return self._reconstruir(fila) if fila else None

    def buscar_por_openlibrary(self, id_ol: str) -> Autor | None:
        fila = ejecutar(self.conexion, "SELECT * FROM autor WHERE id_openlibrary = ?", (id_ol,)).fetchone()
        return self._reconstruir(fila) if fila else None

    def para_obra(self, obra_id: UUID) -> tuple[Autor, ...]:
        filas = ejecutar(self.conexion,
                         """SELECT a.* FROM autor a JOIN obra_autor oa ON oa.autor_id = a.id
                            WHERE oa.obra_id = ? ORDER BY oa.orden""", (str(obra_id),)).fetchall()
        return tuple(self._reconstruir(fila) for fila in filas)

    def listar(self, *, nombre: str | None = None, limite: int = 50,
               desplazamiento: int = 0) -> list[Autor]:
        validar_paginacion(limite, desplazamiento)
        filas = ejecutar(self.conexion,
                         """SELECT * FROM autor WHERE instr(nombre_normalizado, ?) > 0
                            ORDER BY nombre_normalizado, id LIMIT ? OFFSET ?""",
                         (filtro_nombre(nombre), limite, desplazamiento)).fetchall()
        return [self._reconstruir(fila) for fila in filas]

    @staticmethod
    def _reconstruir(fila: sqlite3.Row) -> Autor:
        return Autor(fila["nombre"], id=UUID(fila["id"]), id_openlibrary=fila["id_openlibrary"])
