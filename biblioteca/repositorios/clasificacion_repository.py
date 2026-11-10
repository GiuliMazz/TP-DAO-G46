"""Vocabularios, asociaciones y evidencia; el servicio controla la transacción."""

from datetime import datetime
import sqlite3
from typing import TYPE_CHECKING
from uuid import UUID

from biblioteca.dominio.clasificacion import (
    ClasificacionObra, DecisionClasificacion, EstadoClasificacion, Etiqueta, Genero,
    MetodoClasificacion, PublicoDestinatario, TerminoClasificacion, TipoClasificacion,
)
from biblioteca.errores import ErrorValidacion, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.repositorios.consultas import validar_paginacion

if TYPE_CHECKING:
    from biblioteca.servicios.reglas_clasificacion import ReglaClasificacion

CLASES_TERMINO = {
    TipoClasificacion.GENERO: Genero,
    TipoClasificacion.ETIQUETA: Etiqueta,
    TipoClasificacion.PUBLICO: PublicoDestinatario,
}


class ClasificacionRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def agregar_termino(self, termino: TerminoClasificacion) -> None:
        ejecutar(self.conexion,
                 "INSERT INTO termino_clasificacion (id, tipo, nombre, nombre_normalizado) VALUES (?, ?, ?, ?)",
                 (str(termino.id), termino.tipo.value, termino.nombre, termino.nombre.casefold()))

    def obtener_termino(self, id: UUID) -> TerminoClasificacion | None:
        fila = ejecutar(self.conexion, "SELECT * FROM termino_clasificacion WHERE id = ?", (str(id),)).fetchone()
        return self._termino(fila) if fila else None

    def buscar_termino(self, tipo: TipoClasificacion, nombre: str) -> TerminoClasificacion | None:
        fila = ejecutar(self.conexion,
                         "SELECT * FROM termino_clasificacion WHERE tipo = ? AND nombre_normalizado = ?",
                         (tipo.value, nombre.casefold())).fetchone()
        return self._termino(fila) if fila else None

    def listar_terminos(self, tipo: TipoClasificacion, *, limite: int = 50,
                        desplazamiento: int = 0) -> list[TerminoClasificacion]:
        validar_paginacion(limite, desplazamiento)
        filas = ejecutar(self.conexion,
                         "SELECT * FROM termino_clasificacion WHERE tipo = ? ORDER BY nombre_normalizado, id LIMIT ? OFFSET ?",
                         (tipo.value, limite, desplazamiento)).fetchall()
        return [self._termino(fila) for fila in filas]

    def obtener(self, obra_id: UUID, termino_id: UUID) -> ClasificacionObra | None:
        fila = ejecutar(self.conexion,
                         """SELECT c.*, t.nombre FROM clasificacion_obra c
                            JOIN termino_clasificacion t ON t.id = c.termino_id
                            WHERE c.obra_id = ? AND c.termino_id = ?""",
                         (str(obra_id), str(termino_id))).fetchone()
        return self._clasificacion(fila) if fila else None

    def guardar(self, clasificacion: ClasificacionObra, *, nueva: bool) -> None:
        d = clasificacion.decision
        datos = (d.estado.value, d.metodo.value, d.motivo, d.fecha.isoformat(), d.regla_id, d.regla_version)
        claves = (str(clasificacion.obra_id), str(clasificacion.termino.id))
        if nueva:
            ejecutar(self.conexion,
                     """INSERT INTO clasificacion_obra (obra_id, termino_id, tipo, estado, metodo,
                        motivo, fecha, regla_id, regla_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (*claves, clasificacion.termino.tipo.value, *datos))
        else:
            cursor = ejecutar(self.conexion,
                              """UPDATE clasificacion_obra SET estado = ?, metodo = ?, motivo = ?, fecha = ?,
                                 regla_id = ?, regla_version = ? WHERE obra_id = ? AND termino_id = ?""",
                              (*datos, *claves))
            if cursor.rowcount != 1:
                raise RegistroNoEncontrado("La clasificación no existe.")
        ejecutar(self.conexion,
                 """INSERT INTO decision_clasificacion (obra_id, termino_id, estado, metodo, motivo,
                    fecha, regla_id, regla_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (*claves, *datos))

    def listar(self, obra_id: UUID, *, estado: EstadoClasificacion | None = None,
               limite: int = 50, desplazamiento: int = 0) -> list[ClasificacionObra]:
        validar_paginacion(limite, desplazamiento)
        filtro = " AND c.estado = ?" if estado is not None else ""
        parametros = (str(obra_id),) + ((estado.value,) if estado is not None else ())
        filas = ejecutar(self.conexion,
                         """SELECT c.*, t.nombre FROM clasificacion_obra c
                            JOIN termino_clasificacion t ON t.id = c.termino_id WHERE c.obra_id = ?"""
                         + filtro + " ORDER BY c.tipo, t.nombre_normalizado, t.id LIMIT ? OFFSET ?",
                         (*parametros, limite, desplazamiento)).fetchall()
        return [self._clasificacion(fila) for fila in filas]

    def registrar_materia(self, obra_id: UUID, fuente: str, texto: str) -> int:
        ejecutar(self.conexion,
                 """INSERT INTO materia_original (obra_id, fuente, texto) VALUES (?, ?, ?)
                    ON CONFLICT (obra_id, fuente, texto) DO NOTHING""", (str(obra_id), fuente, texto))
        return ejecutar(self.conexion,
                        "SELECT id FROM materia_original WHERE obra_id = ? AND fuente = ? AND texto = ?",
                        (str(obra_id), fuente, texto)).fetchone()["id"]

    def materias(self, obra_id: UUID, *, limite: int = 50, desplazamiento: int = 0) -> list[dict]:
        validar_paginacion(limite, desplazamiento)
        return [dict(fila) for fila in ejecutar(self.conexion,
                "SELECT id, fuente, texto FROM materia_original WHERE obra_id = ? ORDER BY id LIMIT ? OFFSET ?",
                (str(obra_id), limite, desplazamiento)).fetchall()]

    def materias_para_evaluar(self, obra_id: UUID) -> list[dict]:
        # Sólo las materias de una obra, nunca el catálogo completo.
        return [dict(fila) for fila in ejecutar(self.conexion,
                "SELECT id, texto FROM materia_original WHERE obra_id = ? ORDER BY id",
                (str(obra_id),)).fetchall()]

    def registrar_evidencia(self, obra_id: UUID, termino_id: UUID, materia_id: int,
                            decision: DecisionClasificacion, contexto: str) -> None:
        ejecutar(self.conexion,
                 """INSERT INTO evidencia_clasificacion (obra_id, termino_id, materia_id, regla_id,
                    regla_version, resultado, motivo, fecha, contexto) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (obra_id, termino_id, materia_id, regla_id, regla_version, contexto) DO NOTHING""",
                 (str(obra_id), str(termino_id), materia_id, decision.regla_id, decision.regla_version,
                  decision.estado.value, decision.motivo, decision.fecha.isoformat(), contexto))

    def registrar_regla(self, regla: "ReglaClasificacion") -> None:
        datos = (str(regla.termino_id), regla.materia.casefold(), int(regla.aprobacion_automatica))
        fila = ejecutar(self.conexion,
                         "SELECT termino_id, materia, aprobacion_automatica FROM regla_clasificacion WHERE id = ? AND version = ?",
                         (regla.id, regla.version)).fetchone()
        if fila is not None:
            if tuple(fila) != datos:
                raise ErrorValidacion("Cambiar una regla requiere una nueva versión.")
            return
        ejecutar(self.conexion,
                 "INSERT INTO regla_clasificacion (id, version, termino_id, materia, aprobacion_automatica) VALUES (?, ?, ?, ?, ?)",
                 (regla.id, regla.version, *datos))

    def historial(self, obra_id: UUID, termino_id: UUID, *, limite: int = 50,
                  desplazamiento: int = 0) -> list[DecisionClasificacion]:
        validar_paginacion(limite, desplazamiento)
        filas = ejecutar(self.conexion,
                         "SELECT * FROM decision_clasificacion WHERE obra_id = ? AND termino_id = ? ORDER BY id LIMIT ? OFFSET ?",
                         (str(obra_id), str(termino_id), limite, desplazamiento)).fetchall()
        return [self._decision(fila) for fila in filas]

    def evidencias(self, obra_id: UUID, termino_id: UUID, *, limite: int = 50,
                   desplazamiento: int = 0) -> list[dict]:
        validar_paginacion(limite, desplazamiento)
        return [dict(fila) for fila in ejecutar(self.conexion,
                """SELECT e.regla_id, e.regla_version, e.resultado, e.motivo, e.fecha, e.contexto, m.fuente, m.texto
                   FROM evidencia_clasificacion e JOIN materia_original m ON m.id = e.materia_id
                   WHERE e.obra_id = ? AND e.termino_id = ? ORDER BY e.id LIMIT ? OFFSET ?""",
                (str(obra_id), str(termino_id), limite, desplazamiento)).fetchall()]

    @staticmethod
    def _termino(fila: sqlite3.Row) -> TerminoClasificacion:
        return CLASES_TERMINO[TipoClasificacion(fila["tipo"])](fila["nombre"], id=UUID(fila["id"]))

    @staticmethod
    def _decision(fila: sqlite3.Row) -> DecisionClasificacion:
        return DecisionClasificacion(EstadoClasificacion(fila["estado"]), MetodoClasificacion(fila["metodo"]),
                                     fila["motivo"], datetime.fromisoformat(fila["fecha"]),
                                     fila["regla_id"], fila["regla_version"])

    @classmethod
    def _clasificacion(cls, fila: sqlite3.Row) -> ClasificacionObra:
        termino = CLASES_TERMINO[TipoClasificacion(fila["tipo"])](fila["nombre"], id=UUID(fila["termino_id"]))
        return ClasificacionObra(UUID(fila["obra_id"]), termino, cls._decision(fila))
