"""Persistencia de sedes; la transacción pertenece al caso de uso."""

import sqlite3
from uuid import UUID

from biblioteca.dominio.sede import Sede
from biblioteca.errores import ErrorValidacion, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.repositorios.consultas import filtro_nombre, validar_paginacion


class SedeRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def agregar(self, sede: Sede) -> None:
        ejecutar(
            self.conexion,
            """INSERT INTO sede
               (id, nombre, nombre_normalizado, direccion, contacto, horarios, activa)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(sede.id), sede.nombre, sede.nombre_normalizado, sede.direccion,
             sede.contacto, sede.horarios, int(sede.activa)),
        )

    def actualizar(self, sede: Sede) -> None:
        cursor = ejecutar(
            self.conexion,
            """UPDATE sede SET nombre = ?, nombre_normalizado = ?, direccion = ?,
               contacto = ?, horarios = ?, activa = ? WHERE id = ?""",
            (sede.nombre, sede.nombre_normalizado, sede.direccion, sede.contacto,
             sede.horarios, int(sede.activa), str(sede.id)),
        )
        if cursor.rowcount != 1:
            raise RegistroNoEncontrado("La sede no existe.")

    def obtener(self, id: UUID) -> Sede | None:
        fila = ejecutar(self.conexion, "SELECT * FROM sede WHERE id = ?", (str(id),)).fetchone()
        return self._reconstruir(fila) if fila is not None else None

    def buscar_por_nombre_normalizado(self, nombre: str) -> Sede | None:
        fila = ejecutar(
            self.conexion, "SELECT * FROM sede WHERE nombre_normalizado = ?", (nombre,)
        ).fetchone()
        return self._reconstruir(fila) if fila is not None else None

    def listar(
        self, *, activa: bool | None = None, nombre: str | None = None,
        limite: int = 50, desplazamiento: int = 0,
    ) -> list[Sede]:
        validar_paginacion(limite, desplazamiento)
        if activa is not None and not isinstance(activa, bool):
            raise ErrorValidacion("El filtro de sede activa debe ser booleano.")
        clausulas: list[str] = []
        parametros: list[object] = []
        if activa is not None:
            clausulas.append("activa = ?")
            parametros.append(int(activa))
        busqueda = filtro_nombre(nombre)
        if busqueda:
            clausulas.append("instr(nombre_normalizado, ?) > 0")
            parametros.append(busqueda)
        condicion = " WHERE " + " AND ".join(clausulas) if clausulas else ""
        filas = ejecutar(
            self.conexion,
            "SELECT * FROM sede" + condicion
            + " ORDER BY nombre_normalizado, id LIMIT ? OFFSET ?",
            tuple(parametros + [limite, desplazamiento]),
        ).fetchall()
        return [self._reconstruir(fila) for fila in filas]

    @staticmethod
    def _reconstruir(fila: sqlite3.Row) -> Sede:
        return Sede(
            fila["nombre"], fila["direccion"], fila["contacto"], fila["horarios"],
            id=UUID(fila["id"]), activa=bool(fila["activa"]),
        )
