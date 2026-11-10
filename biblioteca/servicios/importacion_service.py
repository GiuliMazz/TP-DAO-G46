"""Aceptación durable y alta bibliográfica no destructiva, sin crear inventario."""

from collections.abc import Iterable
from datetime import datetime, timezone

from biblioteca.dominio.autor import Autor
from biblioteca.dominio.edicion import Edicion
from biblioteca.dominio.obra import Obra
from biblioteca.dominio.validacion import texto_obligatorio
from biblioteca.errores import ErrorValidacion, PosibleDuplicado, RegistroNoEncontrado
from biblioteca.importacion.modelos import (
    CandidatoOpenLibrary, EstadoImportacion as Estado, EvaluacionOpenLibrary, RegistroImportacion,
)
from biblioteca.importacion.validador_openlibrary import ValidadorOpenLibrary
from biblioteca.persistencia.base_datos import transaccion
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.importacion_repository import ImportacionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.servicios.procesador_materias import ProcesadorMaterias
from biblioteca.servicios.reglas_clasificacion import ReglaClasificacion


class ImportacionService:
    def __init__(self, importaciones: ImportacionRepository, obras: ObraRepository,
                 ediciones: EdicionRepository, autores: AutorRepository,
                 clasificaciones: ClasificacionRepository, *, validador: ValidadorOpenLibrary | None = None) -> None:
        if any(r.conexion is not importaciones.conexion for r in (obras, ediciones, autores, clasificaciones)):
            raise ErrorValidacion("Los repositorios de importación deben compartir conexión.")
        self._importaciones, self._obras, self._ediciones, self._autores = importaciones, obras, ediciones, autores
        self._clasificaciones = clasificaciones
        self._conexion = importaciones.conexion
        self._validador = validador if validador is not None else ValidadorOpenLibrary()

    def evaluar(self, candidato: CandidatoOpenLibrary, *, fecha: datetime | None = None) -> RegistroImportacion:
        if not isinstance(candidato, CandidatoOpenLibrary):
            raise ErrorValidacion("Se requiere una instantánea de Open Library.")
        evaluacion = self._validador.evaluar(candidato)
        fecha = self._fecha(fecha)
        with transaccion(self._conexion):
            id = self._importaciones.registrar_evaluacion(evaluacion, fecha)
            anterior = self._importaciones.obtener(candidato.clave)
            if anterior is not None and (anterior.metodo == "MANUAL" or anterior.decision_evaluacion_id == id):
                decision_id = anterior.decision_id
            else:
                motivo = "Controles técnicos: " + evaluacion.estado.value
                if evaluacion.alertas:
                    motivo += "; " + ", ".join(evaluacion.alertas)
                decision_id = self._importaciones.registrar_decision(candidato.clave, id, evaluacion.estado,
                                                                      "AUTOMATICO", motivo, {}, fecha)
            self._importaciones.actualizar_seguimiento(candidato.clave, id, decision_id)
        return self.obtener(candidato.clave)

    def revisar(self, edicion_ol: str, estado: Estado, motivo: str, *, titulo_edicion: str | None = None,
                titulo_obra: str | None = None, fecha: datetime | None = None) -> RegistroImportacion:
        if not isinstance(estado, Estado) or estado not in (Estado.VALIDADA, Estado.RECHAZADA):
            raise ErrorValidacion("La revisión debe aceptar o rechazar explícitamente.")
        motivo = texto_obligatorio(motivo, "Motivo de revisión")
        fecha = self._fecha(fecha)
        correcciones = {}
        for campo, valor in (("titulo_edicion", titulo_edicion), ("titulo_obra", titulo_obra)):
            if valor is not None:
                correcciones[campo] = texto_obligatorio(valor, campo)
        if correcciones and estado is Estado.RECHAZADA:
            raise ErrorValidacion("Las correcciones de títulos corresponden a una aceptación.")
        with transaccion(self._conexion):
            actual = self.obtener(edicion_ol)
            evaluacion = self._importaciones.obtener_evaluacion(actual.ultima_evaluacion_id)
            if estado is Estado.VALIDADA and not evaluacion.puede_aprobar():
                raise ErrorValidacion("No se pueden omitir controles técnicos pendientes o contradictorios.")
            id = self._importaciones.registrar_decision(edicion_ol, actual.ultima_evaluacion_id, estado,
                                                        "MANUAL", motivo, correcciones, fecha)
            self._importaciones.actualizar_seguimiento(edicion_ol, actual.ultima_evaluacion_id, id)
        return self.obtener(edicion_ol)

    def integrar(self, edicion_ol: str, reglas: Iterable[ReglaClasificacion] = (), *,
                 confirmar_distinta: bool = False, fecha: datetime | None = None) -> Edicion:
        if type(confirmar_distinta) is not bool:
            raise ErrorValidacion("La confirmación de registro distinto debe ser booleana.")
        fecha = self._fecha(fecha)
        with transaccion(self._conexion):
            registro = self.obtener(edicion_ol)
            if registro.estado is not Estado.VALIDADA:
                raise ErrorValidacion("Sólo se integran candidatas con aceptación vigente.")
            evaluacion = self._importaciones.obtener_evaluacion(registro.decision_evaluacion_id)
            if not evaluacion.puede_aprobar():
                raise ErrorValidacion("La evidencia aceptada no cumple los controles técnicos.")
            datos = evaluacion.normalizados
            correcciones = self._importaciones.correcciones(registro.decision_id)
            if "titulo_edicion" in correcciones:
                datos["edicion"]["titulo"] = correcciones["titulo_edicion"]
            if "titulo_obra" in correcciones:
                datos["obra"]["titulo_original"] = correcciones["titulo_obra"]
            obra = self._obras.buscar_por_openlibrary(datos["obra"]["id_openlibrary"])
            edicion = self._ediciones.buscar_por_openlibrary(edicion_ol)
            if edicion is not None and (obra is None or edicion.obra_id != obra.id):
                raise ErrorValidacion("La edición existente pertenece a otra obra; no se puede reasignar.")
            if obra is None:
                autores = []
                for dato in datos["autores"]:
                    autor = self._autores.buscar_por_openlibrary(dato["id_openlibrary"])
                    if autor is None:
                        autor = Autor(dato["nombre"], id_openlibrary=dato["id_openlibrary"])
                        self._autores.agregar(autor)
                    autores.append(autor.id)
                obra = Obra(autor_ids=autores, **datos["obra"])
                if not confirmar_distinta and self._obras.coincidencias(obra):
                    raise PosibleDuplicado("Coincidencia de título y autores: revisar antes de importar otra obra.")
                self._obras.agregar(obra)
            if edicion is None:
                edicion = Edicion(obra.id, **datos["edicion"])
                if not confirmar_distinta and edicion.isbn_canonico and self._ediciones.coincidencias_isbn(edicion.isbn_canonico):
                    raise PosibleDuplicado("ISBN coincidente: revisar antes de importar otra edición.")
                self._ediciones.agregar(edicion)
                if obra.edicion_preferida_id is None:
                    obra.seleccionar_edicion(edicion)
                    self._obras.actualizar(obra)
            ProcesadorMaterias(self._clasificaciones, self._obras).procesar(
                obra.id, datos["materias"], reglas, fuente="Open Library", fecha=fecha)
            self._importaciones.marcar_integrada(edicion_ol, edicion.id, registro.decision_id)
        return edicion

    def obtener(self, edicion_ol: str) -> RegistroImportacion:
        registro = self._importaciones.obtener(edicion_ol)
        if registro is None:
            raise RegistroNoEncontrado("La candidata de importación no existe.")
        return registro

    def listar(self, *, estado: Estado | None = None, limite: int = 50,
               desplazamiento: int = 0) -> list[RegistroImportacion]:
        if estado is not None and not isinstance(estado, Estado):
            raise ErrorValidacion("Estado de importación inválido.")
        return self._importaciones.listar(estado=estado, limite=limite, desplazamiento=desplazamiento)

    def historial(self, edicion_ol: str, *, limite: int = 50, desplazamiento: int = 0) -> list[dict]:
        self.obtener(edicion_ol)
        return self._importaciones.historial(edicion_ol, limite=limite, desplazamiento=desplazamiento)

    def evaluaciones(self, edicion_ol: str, *, limite: int = 50, desplazamiento: int = 0) -> list[dict]:
        self.obtener(edicion_ol)
        return self._importaciones.evaluaciones(edicion_ol, limite=limite, desplazamiento=desplazamiento)

    def evidencia(self, edicion_ol: str, *, de_decision: bool = False) -> EvaluacionOpenLibrary:
        """Consultar el detalle nuevo o el que respalda la decisión vigente desde una vista."""
        if type(de_decision) is not bool:
            raise ErrorValidacion("La selección de evidencia debe ser booleana.")
        registro = self.obtener(edicion_ol)
        id = registro.decision_evaluacion_id if de_decision else registro.ultima_evaluacion_id
        return self._importaciones.obtener_evaluacion(id)

    def resumen(self) -> dict:
        return self._importaciones.resumen()

    @staticmethod
    def _fecha(fecha: datetime | None) -> datetime:
        fecha = datetime.now(timezone.utc) if fecha is None else fecha
        if not isinstance(fecha, datetime) or fecha.utcoffset() is None:
            raise ErrorValidacion("La fecha debe incluir zona horaria.")
        return fecha.astimezone(timezone.utc)
