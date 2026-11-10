"""Auditoría durable de importación. No altera las bases de preparación."""

from datetime import datetime
import json
import sqlite3
from uuid import UUID

from biblioteca.errores import ErrorValidacion, RegistroNoEncontrado
from biblioteca.importacion.modelos import (
    CandidatoOpenLibrary, EstadoImportacion, EvaluacionOpenLibrary, RegistroImportacion, json_canonico,
)
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.repositorios.consultas import validar_paginacion


class ImportacionRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def registrar_evaluacion(self, evaluacion: EvaluacionOpenLibrary, fecha: datetime) -> int:
        c = evaluacion.candidato
        ejecutar(self.conexion,
                 """INSERT INTO evaluacion_importacion (edicion_ol, huella, politica, estado, documento_json,
                    controles_json, alertas_json, normalizados_json, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (edicion_ol, huella, politica) DO NOTHING""",
                 (c.clave, c.huella, evaluacion.politica, evaluacion.estado.value, c.documento,
                  json_canonico(evaluacion.controles), json_canonico(evaluacion.alertas),
                  json_canonico(evaluacion.normalizados) if evaluacion.normalizados is not None else None,
                  fecha.isoformat()))
        id = ejecutar(self.conexion,
                      "SELECT id FROM evaluacion_importacion WHERE edicion_ol = ? AND huella = ? AND politica = ?",
                      (c.clave, c.huella, evaluacion.politica)).fetchone()["id"]
        guardada = self.obtener_evaluacion(id)
        if guardada != evaluacion:
            raise ErrorValidacion("Cambiar los resultados de una política requiere una versión nueva.")
        return id

    def obtener_evaluacion(self, id: int) -> EvaluacionOpenLibrary:
        fila = ejecutar(self.conexion, "SELECT * FROM evaluacion_importacion WHERE id = ?", (id,)).fetchone()
        if fila is None:
            raise RegistroNoEncontrado("La evaluación no existe.")
        return EvaluacionOpenLibrary(CandidatoOpenLibrary(fila["documento_json"]), fila["politica"],
                                     EstadoImportacion(fila["estado"]), json.loads(fila["controles_json"]),
                                     tuple(json.loads(fila["alertas_json"])),
                                     json.loads(fila["normalizados_json"]) if fila["normalizados_json"] is not None else None)

    def registrar_decision(self, edicion_ol: str, evaluacion_id: int, estado: EstadoImportacion,
                           metodo: str, motivo: str, correcciones: dict, fecha: datetime) -> int:
        return ejecutar(self.conexion,
                        """INSERT INTO decision_importacion (edicion_ol, evaluacion_id, estado, metodo, motivo,
                           correcciones_json, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (edicion_ol, evaluacion_id, estado.value, metodo, motivo,
                         json_canonico(correcciones), fecha.isoformat())).lastrowid

    def actualizar_seguimiento(self, edicion_ol: str, evaluacion_id: int, decision_id: int) -> None:
        ejecutar(self.conexion,
                 """INSERT INTO seguimiento_importacion (edicion_ol, ultima_evaluacion_id, decision_id)
                    VALUES (?, ?, ?) ON CONFLICT (edicion_ol) DO UPDATE SET
                    ultima_evaluacion_id = excluded.ultima_evaluacion_id, decision_id = excluded.decision_id""",
                 (edicion_ol, evaluacion_id, decision_id))

    def obtener(self, edicion_ol: str) -> RegistroImportacion | None:
        fila = ejecutar(self.conexion,
                         """SELECT s.*, d.evaluacion_id, d.estado, d.metodo, d.motivo
                            FROM seguimiento_importacion s JOIN decision_importacion d ON d.id = s.decision_id
                            WHERE s.edicion_ol = ?""", (edicion_ol,)).fetchone()
        return self._registro(fila) if fila else None

    def correcciones(self, decision_id: int) -> dict:
        fila = ejecutar(self.conexion, "SELECT correcciones_json FROM decision_importacion WHERE id = ?", (decision_id,)).fetchone()
        if fila is None:
            raise RegistroNoEncontrado("La decisión no existe.")
        return json.loads(fila["correcciones_json"])

    def marcar_integrada(self, edicion_ol: str, edicion_id: UUID, decision_id: int) -> None:
        cursor = ejecutar(self.conexion,
                          "UPDATE seguimiento_importacion SET edicion_local_id = ?, decision_integrada_id = ? WHERE edicion_ol = ?",
                          (str(edicion_id), decision_id, edicion_ol))
        if cursor.rowcount != 1:
            raise RegistroNoEncontrado("El seguimiento no existe.")

    def listar(self, *, estado: EstadoImportacion | None = None, limite: int = 50,
               desplazamiento: int = 0) -> list[RegistroImportacion]:
        validar_paginacion(limite, desplazamiento)
        filtro = " WHERE d.estado = ?" if estado is not None else ""
        parametros = (estado.value,) if estado is not None else ()
        filas = ejecutar(self.conexion,
                         """SELECT s.*, d.evaluacion_id, d.estado, d.metodo, d.motivo
                            FROM seguimiento_importacion s JOIN decision_importacion d ON d.id = s.decision_id"""
                         + filtro + " ORDER BY s.edicion_ol LIMIT ? OFFSET ?",
                         (*parametros, limite, desplazamiento)).fetchall()
        return [self._registro(fila) for fila in filas]

    def historial(self, edicion_ol: str, *, limite: int = 50, desplazamiento: int = 0) -> list[dict]:
        validar_paginacion(limite, desplazamiento)
        return [dict(fila) for fila in ejecutar(self.conexion,
                "SELECT * FROM decision_importacion WHERE edicion_ol = ? ORDER BY id LIMIT ? OFFSET ?",
                (edicion_ol, limite, desplazamiento)).fetchall()]

    def evaluaciones(self, edicion_ol: str, *, limite: int = 50, desplazamiento: int = 0) -> list[dict]:
        validar_paginacion(limite, desplazamiento)
        return [dict(fila) for fila in ejecutar(self.conexion,
                """SELECT id, huella, politica, estado, controles_json, alertas_json, fecha
                   FROM evaluacion_importacion WHERE edicion_ol = ? ORDER BY id LIMIT ? OFFSET ?""",
                (edicion_ol, limite, desplazamiento)).fetchall()]

    def resumen(self) -> dict:
        estados = {e.value: 0 for e in EstadoImportacion}
        for fila in ejecutar(self.conexion,
                             """SELECT d.estado, COUNT(*) AS cantidad FROM seguimiento_importacion s
                                JOIN decision_importacion d ON d.id = s.decision_id GROUP BY d.estado""").fetchall():
            estados[fila["estado"]] = fila["cantidad"]
        cantidades = ejecutar(self.conexion,
                               """SELECT COUNT(*) AS evaluadas, COUNT(edicion_local_id) AS integradas,
                                  COUNT(DISTINCT e.obra_id) AS obras FROM seguimiento_importacion s
                                  LEFT JOIN edicion e ON e.id = s.edicion_local_id""").fetchone()
        return {"estados": estados, "ediciones_evaluadas": cantidades["evaluadas"],
                "ediciones_integradas": cantidades["integradas"], "obras_integradas": cantidades["obras"]}

    @staticmethod
    def _registro(fila: sqlite3.Row) -> RegistroImportacion:
        return RegistroImportacion(fila["edicion_ol"], fila["ultima_evaluacion_id"], fila["decision_id"],
                                    fila["evaluacion_id"], EstadoImportacion(fila["estado"]), fila["metodo"],
                                    fila["motivo"], UUID(fila["edicion_local_id"]) if fila["edicion_local_id"] else None)
