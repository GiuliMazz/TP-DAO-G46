"""SQL de inventario y proyecciones de disponibilidad; sin commits propios."""

import sqlite3
from uuid import UUID

from biblioteca.dominio.ejemplar import CondicionFisica, Ejemplar, SituacionOperativa
from biblioteca.dominio.validacion import validar_uuid
from biblioteca.errores import ErrorValidacion, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.repositorios.consultas import validar_paginacion
from biblioteca.resultados_inventario import DisponibilidadSede


class EjemplarRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def agregar(self, ejemplar: Ejemplar) -> None:
        ejecutar(self.conexion,
                 """INSERT INTO ejemplar (id, codigo_inventario, edicion_id, sede_propietaria_id,
                    sede_actual_id, condicion_fisica, situacion_operativa)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (str(ejemplar.id), ejemplar.codigo_inventario, str(ejemplar.edicion_id),
                  str(ejemplar.sede_propietaria_id),
                  str(ejemplar.sede_actual_id) if ejemplar.sede_actual_id else None,
                  ejemplar.condicion_fisica.value, ejemplar.situacion_operativa.value))

    def actualizar(self, ejemplar: Ejemplar) -> None:
        # En 2B sólo se actualizan condición/baja. Identidad y ubicación no se editan.
        cursor = ejecutar(self.conexion,
                          """UPDATE ejemplar SET condicion_fisica = ?, situacion_operativa = ?
                             WHERE id = ? AND codigo_inventario = ? AND edicion_id = ?
                             AND sede_propietaria_id = ? AND sede_actual_id IS ?""",
                          (ejemplar.condicion_fisica.value, ejemplar.situacion_operativa.value,
                           str(ejemplar.id), ejemplar.codigo_inventario, str(ejemplar.edicion_id),
                           str(ejemplar.sede_propietaria_id),
                           str(ejemplar.sede_actual_id) if ejemplar.sede_actual_id else None))
        if cursor.rowcount != 1:
            raise RegistroNoEncontrado("El ejemplar no existe o su identidad/ubicación no coincide.")

    def obtener(self, id: UUID) -> Ejemplar | None:
        fila = ejecutar(self.conexion, "SELECT * FROM ejemplar WHERE id = ?", (str(id),)).fetchone()
        return self._reconstruir(fila) if fila else None

    def buscar_por_codigo(self, codigo: str) -> Ejemplar | None:
        fila = ejecutar(self.conexion, "SELECT * FROM ejemplar WHERE codigo_inventario = ?",
                         (codigo,)).fetchone()
        return self._reconstruir(fila) if fila else None

    def listar(
        self, *, obra_id: UUID | str | None = None, edicion_id: UUID | str | None = None,
        sede_actual_id: UUID | str | None = None, sede_propietaria_id: UUID | str | None = None,
        condicion_fisica: CondicionFisica | None = None,
        situacion_operativa: SituacionOperativa | None = None, solo_disponibles: bool = False,
        limite: int = 50, desplazamiento: int = 0,
    ) -> list[Ejemplar]:
        validar_paginacion(limite, desplazamiento)
        if not isinstance(solo_disponibles, bool):
            raise ErrorValidacion("El filtro de disponibilidad debe ser booleano.")
        clausulas: list[str] = []
        parametros: list[object] = []
        for columna, valor in (
            ("d.obra_id", obra_id), ("e.edicion_id", edicion_id),
            ("e.sede_actual_id", sede_actual_id), ("e.sede_propietaria_id", sede_propietaria_id),
        ):
            if valor is not None:
                clausulas.append(columna + " = ?")
                parametros.append(str(validar_uuid(valor)))
        for columna, valor, tipo in (
            ("e.condicion_fisica", condicion_fisica, CondicionFisica),
            ("e.situacion_operativa", situacion_operativa, SituacionOperativa),
        ):
            if valor is not None:
                if not isinstance(valor, tipo):
                    raise ErrorValidacion("El filtro de condición o situación no es válido.")
                clausulas.append(columna + " = ?")
                parametros.append(valor.value)
        if solo_disponibles:
            # Proyección SQL de la disponibilidad del dominio y de la sede activa.
            # Aplicarla antes de LIMIT evita páginas incompletas por filtrar después.
            clausulas.append("""e.situacion_operativa = 'LIBRE' AND e.condicion_fisica = 'APTO'
                AND e.sede_actual_id = e.sede_propietaria_id AND s.activa = 1
                AND (SELECT COUNT(*) FROM obra_autor oa WHERE oa.obra_id = d.obra_id) > 0""")
        condicion = " WHERE " + " AND ".join(clausulas) if clausulas else ""
        filas = ejecutar(self.conexion,
                         """SELECT e.* FROM ejemplar e JOIN edicion d ON d.id = e.edicion_id
                            JOIN obra o ON o.id = d.obra_id
                            LEFT JOIN sede s ON s.id = e.sede_actual_id""" + condicion
                         + " ORDER BY e.codigo_inventario, e.id LIMIT ? OFFSET ?",
                         tuple(parametros + [limite, desplazamiento])).fetchall()
        return [self._reconstruir(fila) for fila in filas]

    def disponibilidad_por_sede(
        self, obra_id: UUID, *, sede_id: UUID | None = None,
        limite: int = 50, desplazamiento: int = 0,
    ) -> list[DisponibilidadSede]:
        validar_paginacion(limite, desplazamiento)
        condicion = " WHERE s.id = ?" if sede_id is not None else ""
        # Agrupar primero las copias de esta obra, sin recorrer todo el inventario
        # de cada sede ni multiplicar copias por las relaciones de autoría.
        filas = ejecutar(self.conexion,
                         """WITH propias AS (
                                SELECT e.sede_propietaria_id AS sede_id, COUNT(*) AS cantidad
                                FROM edicion d JOIN ejemplar e ON e.edicion_id = d.id
                                WHERE d.obra_id = ? GROUP BY e.sede_propietaria_id),
                            ubicadas AS (
                                SELECT e.sede_actual_id AS sede_id, COUNT(*) AS cantidad,
                                    SUM(CASE WHEN e.situacion_operativa = 'BAJA' THEN 1 ELSE 0 END) AS bajas,
                                    SUM(CASE WHEN e.sede_actual_id = e.sede_propietaria_id
                                        AND e.situacion_operativa = 'LIBRE' AND e.condicion_fisica = 'APTO'
                                        THEN 1 ELSE 0 END) AS aptas
                                FROM edicion d JOIN ejemplar e ON e.edicion_id = d.id
                                WHERE d.obra_id = ? GROUP BY e.sede_actual_id)
                            SELECT s.id, s.nombre, s.activa,
                                COALESCE(p.cantidad, 0) AS propios, COALESCE(u.cantidad, 0) AS ubicados,
                                COALESCE(u.bajas, 0) AS bajas,
                                CASE WHEN s.activa = 1 AND
                                    (SELECT COUNT(*) FROM obra_autor oa WHERE oa.obra_id = ?) > 0
                                    THEN COALESCE(u.aptas, 0) ELSE 0 END AS disponibles
                            FROM sede s LEFT JOIN propias p ON p.sede_id = s.id
                                LEFT JOIN ubicadas u ON u.sede_id = s.id""" + condicion
                         + " ORDER BY s.nombre_normalizado, s.id LIMIT ? OFFSET ?",
                         (str(obra_id), str(obra_id), str(obra_id),
                          *((str(sede_id),) if sede_id is not None else ()),
                          limite, desplazamiento)).fetchall()
        return [DisponibilidadSede(obra_id, UUID(fila["id"]), fila["nombre"], bool(fila["activa"]),
                                   fila["propios"], fila["ubicados"], fila["bajas"], fila["disponibles"])
                for fila in filas]

    @staticmethod
    def _reconstruir(fila: sqlite3.Row) -> Ejemplar:
        return Ejemplar(
            fila["codigo_inventario"], fila["edicion_id"], fila["sede_propietaria_id"],
            sede_actual_id=UUID(fila["sede_actual_id"]) if fila["sede_actual_id"] else None,
            id=UUID(fila["id"]), condicion_fisica=CondicionFisica(fila["condicion_fisica"]),
            situacion_operativa=SituacionOperativa(fila["situacion_operativa"]),
        )
