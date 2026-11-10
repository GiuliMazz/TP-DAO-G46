"""Persistencia de socios identificados por DNI único en toda la red."""

import sqlite3
from uuid import UUID

from biblioteca.dominio.socio import EstadoSocio, Socio
from biblioteca.errores import ErrorValidacion, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.repositorios.consultas import filtro_nombre, validar_paginacion


class SocioRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion
        conexion.create_function("casefold", 1, str.casefold, deterministic=True)

    def agregar(self, socio: Socio) -> None:
        ejecutar(
            self.conexion,
            """INSERT INTO socio
               (id, documento, nombre_completo, nombre_normalizado, contacto, estado)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(socio.id), socio.documento, socio.nombre_completo,
             socio.nombre_completo.casefold(), socio.contacto, socio.estado.value),
        )

    def actualizar(self, socio: Socio) -> None:
        cursor = ejecutar(
            self.conexion,
            """UPDATE socio SET documento = ?, nombre_completo = ?, nombre_normalizado = ?,
               contacto = ?, estado = ? WHERE id = ?""",
            (socio.documento, socio.nombre_completo, socio.nombre_completo.casefold(),
             socio.contacto, socio.estado.value, str(socio.id)),
        )
        if cursor.rowcount != 1:
            raise RegistroNoEncontrado("El socio no existe.")

    def obtener(self, id: UUID) -> Socio | None:
        fila = ejecutar(self.conexion, "SELECT * FROM socio WHERE id = ?", (str(id),)).fetchone()
        return self._reconstruir(fila) if fila is not None else None

    def buscar_por_documento(self, documento: str) -> Socio | None:
        fila = ejecutar(
            self.conexion, "SELECT * FROM socio WHERE documento = ?", (documento,)
        ).fetchone()
        return self._reconstruir(fila) if fila is not None else None

    def listar(
        self, *, estado: EstadoSocio | None = None, nombre: str | None = None,
        texto: str | None = None, limite: int = 50, desplazamiento: int = 0,
    ) -> list[Socio]:
        validar_paginacion(limite, desplazamiento)
        if estado is not None and not isinstance(estado, EstadoSocio):
            raise ErrorValidacion("El filtro de estado del socio no es válido.")
        clausulas: list[str] = []
        parametros: list[object] = []
        if estado is not None:
            clausulas.append("estado = ?")
            parametros.append(estado.value)
        busqueda = filtro_nombre(nombre)
        if busqueda:
            clausulas.append("instr(nombre_normalizado, ?) > 0")
            parametros.append(busqueda)
        texto = filtro_nombre(texto)
        if texto:
            # Fragmento de DNI con separadores de presentación, sin exigir DNI completo.
            documento = texto.translate(str.maketrans("", "", ". -"))
            documento = documento if documento and all("0" <= c <= "9" for c in documento) else None
            clausulas.append("(instr(nombre_normalizado, ?) > 0 OR instr(documento, ?) > 0 "
                             "OR instr(casefold(contacto), ?) > 0)")
            parametros.extend((texto, documento, texto))
        condicion = " WHERE " + " AND ".join(clausulas) if clausulas else ""
        filas = ejecutar(
            self.conexion,
            "SELECT * FROM socio" + condicion
            + " ORDER BY nombre_normalizado, id LIMIT ? OFFSET ?",
            tuple(parametros + [limite, desplazamiento]),
        ).fetchall()
        return [self._reconstruir(fila) for fila in filas]

    @staticmethod
    def _reconstruir(fila: sqlite3.Row) -> Socio:
        return Socio(
            fila["documento"], fila["nombre_completo"], fila["contacto"],
            id=UUID(fila["id"]), estado=EstadoSocio(fila["estado"]),
        )
