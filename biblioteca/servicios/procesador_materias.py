"""Procesamiento compartido: participa en la transacción del caso de uso."""

from collections.abc import Iterable
from datetime import datetime, timezone
import json
from uuid import UUID

from biblioteca.dominio.clasificacion import ClasificacionObra
from biblioteca.dominio.validacion import texto_obligatorio, validar_uuid
from biblioteca.errores import ErrorPersistencia, ErrorValidacion, RegistroNoEncontrado
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.servicios.reglas_clasificacion import ReglaClasificacion


class ProcesadorMaterias:
    def __init__(self, clasificaciones: ClasificacionRepository, obras: ObraRepository) -> None:
        if clasificaciones.conexion is not obras.conexion:
            raise ErrorValidacion("Los repositorios deben compartir conexión.")
        self._clasificaciones, self._obras = clasificaciones, obras

    def procesar(self, obra_id: UUID | str, materias: Iterable[str], reglas: Iterable[ReglaClasificacion],
                 *, fuente: str = "Open Library", fecha: datetime | None = None) -> None:
        if not self._obras.conexion.in_transaction:
            raise ErrorPersistencia("El procesamiento de materias requiere una transacción activa.")
        obra_id = validar_uuid(obra_id)
        fuente = texto_obligatorio(fuente, "Fuente")
        if (not isinstance(materias, Iterable) or not isinstance(reglas, Iterable)
                or isinstance(materias, (str, bytes)) or isinstance(reglas, (str, bytes))):
            raise ErrorValidacion("Se requieren colecciones de materias y reglas.")
        materias, reglas = tuple(materias), tuple(reglas)
        if any(not isinstance(m, str) or not m.strip() for m in materias):
            raise ErrorValidacion("Cada materia debe ser texto no vacío.")
        if any(not isinstance(r, ReglaClasificacion) for r in reglas):
            raise ErrorValidacion("Las reglas deben ser ReglaClasificacion.")
        if len({r.id for r in reglas}) != len(reglas):
            raise ErrorValidacion("El lote debe usar una sola versión por regla.")
        fecha = datetime.now(timezone.utc) if fecha is None else fecha
        if not isinstance(fecha, datetime) or fecha.utcoffset() is None:
            raise ErrorValidacion("La fecha debe incluir zona horaria.")
        if self._obras.obtener(obra_id) is None:
            raise RegistroNoEncontrado("La obra no existe.")
        terminos = {}
        for regla in reglas:
            termino = self._clasificaciones.obtener_termino(regla.termino_id)
            if termino is None:
                raise RegistroNoEncontrado("El término de clasificación no existe.")
            terminos[regla.termino_id] = termino
            self._clasificaciones.registrar_regla(regla)
        for materia in materias:
            self._clasificaciones.registrar_materia(obra_id, fuente, materia)
        materias_guardadas = self._clasificaciones.materias_para_evaluar(obra_id)
        contexto = tuple(sorted({m["texto"] for m in materias_guardadas}))
        contexto_json = json.dumps(contexto, ensure_ascii=False)
        for regla in reglas:
            termino = terminos[regla.termino_id]
            for materia in materias_guardadas:
                decision = regla.evaluar(materia["texto"], contexto, termino.tipo, fecha)
                if decision is None:
                    continue
                clasificacion = self._clasificaciones.obtener(obra_id, termino.id)
                if clasificacion is None:
                    clasificacion = ClasificacionObra(obra_id, termino, decision)
                    self._clasificaciones.guardar(clasificacion, nueva=True)
                elif clasificacion.aplicar_regla(decision):
                    self._clasificaciones.guardar(clasificacion, nueva=False)
                self._clasificaciones.registrar_evidencia(obra_id, termino.id, materia["id"], decision, contexto_json)
