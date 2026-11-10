"""Casos de uso de clasificación, separados del importador y del inventario."""

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import UUID

from biblioteca.dominio.clasificacion import (
    ClasificacionObra, DecisionClasificacion, EstadoClasificacion, MetodoClasificacion,
    TerminoClasificacion, TipoClasificacion,
)
from biblioteca.dominio.validacion import validar_uuid
from biblioteca.errores import ErrorValidacion, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import transaccion
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository, CLASES_TERMINO
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.servicios.reglas_clasificacion import ReglaClasificacion
from biblioteca.servicios.procesador_materias import ProcesadorMaterias


class ClasificacionService:
    def __init__(self, clasificaciones: ClasificacionRepository, obras: ObraRepository) -> None:
        if clasificaciones.conexion is not obras.conexion:
            raise ErrorValidacion("Los repositorios deben compartir conexión.")
        self._clasificaciones = clasificaciones
        self._obras = obras
        self._conexion = obras.conexion

    def registrar_termino(self, tipo: TipoClasificacion, nombre: str) -> TerminoClasificacion:
        self._validar_tipo(tipo)
        termino = CLASES_TERMINO[tipo](nombre)
        with transaccion(self._conexion):
            self._clasificaciones.agregar_termino(termino)
        return termino

    def listar_terminos(self, tipo: TipoClasificacion, *, limite: int = 50,
                        desplazamiento: int = 0) -> list[TerminoClasificacion]:
        self._validar_tipo(tipo)
        return self._clasificaciones.listar_terminos(tipo, limite=limite, desplazamiento=desplazamiento)

    def proponer(self, obra_id: UUID | str, termino_id: UUID | str, motivo: str,
                  *, fecha: datetime | None = None) -> ClasificacionObra:
        obra_id, termino_id = validar_uuid(obra_id), validar_uuid(termino_id)
        decision = DecisionClasificacion(EstadoClasificacion.PROPUESTO, MetodoClasificacion.MANUAL,
                                         motivo, self._fecha(fecha))
        with transaccion(self._conexion):
            self._exigir_obra(obra_id)
            termino = self._exigir_termino(termino_id)
            existente = self._clasificaciones.obtener(obra_id, termino_id)
            if existente is not None:
                return existente
            clasificacion = ClasificacionObra(obra_id, termino, decision)
            self._clasificaciones.guardar(clasificacion, nueva=True)
            return clasificacion

    def revisar(self, obra_id: UUID | str, termino_id: UUID | str,
                estado: EstadoClasificacion, motivo: str, *, fecha: datetime | None = None) -> ClasificacionObra:
        with transaccion(self._conexion):
            clasificacion = self.obtener(obra_id, termino_id)
            clasificacion.revisar(estado, motivo, self._fecha(fecha))
            self._clasificaciones.guardar(clasificacion, nueva=False)
            return clasificacion

    def obtener(self, obra_id: UUID | str, termino_id: UUID | str) -> ClasificacionObra:
        clasificacion = self._clasificaciones.obtener(validar_uuid(obra_id), validar_uuid(termino_id))
        if clasificacion is None:
            raise RegistroNoEncontrado("La clasificación no existe.")
        return clasificacion

    def listar(self, obra_id: UUID | str, *, estado: EstadoClasificacion | None = None,
               limite: int = 50, desplazamiento: int = 0) -> list[ClasificacionObra]:
        obra_id = validar_uuid(obra_id)
        self._exigir_obra(obra_id)
        if estado is not None and not isinstance(estado, EstadoClasificacion):
            raise ErrorValidacion("Estado de clasificación inválido.")
        return self._clasificaciones.listar(obra_id, estado=estado, limite=limite, desplazamiento=desplazamiento)

    def preparar_reglas_iniciales(self) -> tuple[ReglaClasificacion, ...]:
        """Alta explícita e idempotente; no se ejecuta al migrar ni al importar el módulo."""
        correspondencias = (
            (TipoClasificacion.GENERO, "Fantasía", "Fantasy fiction", "genero-fantasia"),
            (TipoClasificacion.ETIQUETA, "Magia", "Magic -- Fiction", "tema-magia-ficcion"),
            (TipoClasificacion.PUBLICO, "Infantil", "Children's fiction", "publico-infantil"),
            (TipoClasificacion.PUBLICO, "Juvenil", "Young adult fiction", "publico-juvenil"),
        )
        reglas = []
        with transaccion(self._conexion):
            for tipo, nombre, materia, id in correspondencias:
                termino = self._clasificaciones.buscar_termino(tipo, nombre)
                if termino is None:
                    termino = CLASES_TERMINO[tipo](nombre)
                    self._clasificaciones.agregar_termino(termino)
                regla = ReglaClasificacion(id, "1", materia, termino.id)
                self._clasificaciones.registrar_regla(regla)
                reglas.append(regla)
        return tuple(reglas)

    def procesar_materias(self, obra_id: UUID | str, materias: Iterable[str],
                          reglas: Iterable[ReglaClasificacion], *, fuente: str = "Open Library",
                          fecha: datetime | None = None) -> None:
        with transaccion(self._conexion):
            ProcesadorMaterias(self._clasificaciones, self._obras).procesar(
                obra_id, materias, reglas, fuente=fuente, fecha=fecha)

    def preparar_reglas_catalogo_local(self) -> tuple[ReglaClasificacion, ...]:
        """Ampliación explícita para la selección local; coincidencias completas.

        No infiere edades por ausencia ni convierte materias genéricas (Fantasy,
        History, Biography) en géneros. Conserva las reglas iniciales y su versión.
        El procesador mantiene propuestas por contexto crítico y decisiones humanas.
        """
        reglas = list(self.preparar_reglas_iniciales())
        correspondencias = (
            (TipoClasificacion.GENERO, "Fantasía", "Fiction, fantasy, general"),
            (TipoClasificacion.GENERO, "Fantasía", "Fiction, fantasy, epic"),
            (TipoClasificacion.GENERO, "Ciencia ficción", "Science fiction"),
            (TipoClasificacion.GENERO, "Ciencia ficción", "Fiction, science fiction, general"),
            (TipoClasificacion.GENERO, "Terror", "Horror tales"),
            (TipoClasificacion.GENERO, "Terror", "Horror fiction"),
            (TipoClasificacion.GENERO, "Terror", "Horror stories"),
            (TipoClasificacion.GENERO, "Terror", "Fiction, horror"),
            (TipoClasificacion.GENERO, "Policial", "Detective and mystery stories"),
            (TipoClasificacion.GENERO, "Policial", "Mystery and detective stories"),
            (TipoClasificacion.GENERO, "Policial", "Fiction, mystery & detective, general"),
            (TipoClasificacion.GENERO, "Novela histórica", "Historical fiction"),
            (TipoClasificacion.GENERO, "Novela histórica", "Fiction, historical, general"),
            (TipoClasificacion.GENERO, "Romance", "Fiction, romance, general"),
            (TipoClasificacion.GENERO, "Romance", "Fiction, romance, contemporary"),
            (TipoClasificacion.ETIQUETA, "Magia", "Magic"),
            (TipoClasificacion.ETIQUETA, "Dragones", "Dragons"),
            (TipoClasificacion.ETIQUETA, "Amistad", "Friendship"),
            (TipoClasificacion.ETIQUETA, "Tecnología", "Technology"),
            (TipoClasificacion.ETIQUETA, "Ciencia", "Science"),
            (TipoClasificacion.PUBLICO, "Juvenil", "Juvenile fiction"),
            (TipoClasificacion.PUBLICO, "Juvenil", "Juvenile literature"),
        )
        with transaccion(self._conexion):
            for numero, (tipo, nombre, materia) in enumerate(correspondencias, 1):
                termino = self._clasificaciones.buscar_termino(tipo, nombre)
                if termino is None:
                    termino = CLASES_TERMINO[tipo](nombre)
                    self._clasificaciones.agregar_termino(termino)
                # Juvenile no distingue niños/adolescentes. La materia genérica
                # Science fiction apareció también en biografías de la muestra.
                # Conservar propuestas; el descriptor específico sí es automático.
                # Versión 2 mantiene trazabilidad de la evaluación inicial.
                dudoso = tipo is TipoClasificacion.PUBLICO or materia == "Science fiction"
                regla = ReglaClasificacion(f"local-2026-{numero:02d}", "2" if dudoso else "1",
                                          materia, termino.id, aprobacion_automatica=not dudoso)
                self._clasificaciones.registrar_regla(regla)
                reglas.append(regla)
        return tuple(reglas)

    def materias(self, obra_id: UUID | str, *, limite: int = 50, desplazamiento: int = 0) -> list[dict]:
        obra_id = validar_uuid(obra_id)
        self._exigir_obra(obra_id)
        return self._clasificaciones.materias(obra_id, limite=limite, desplazamiento=desplazamiento)

    def historial(self, obra_id: UUID | str, termino_id: UUID | str,
                  *, limite: int = 50, desplazamiento: int = 0) -> list[DecisionClasificacion]:
        clasificacion = self.obtener(obra_id, termino_id)
        return self._clasificaciones.historial(clasificacion.obra_id, clasificacion.termino.id,
                                               limite=limite, desplazamiento=desplazamiento)

    def evidencias(self, obra_id: UUID | str, termino_id: UUID | str,
                   *, limite: int = 50, desplazamiento: int = 0) -> list[dict]:
        clasificacion = self.obtener(obra_id, termino_id)
        return self._clasificaciones.evidencias(clasificacion.obra_id, clasificacion.termino.id,
                                                limite=limite, desplazamiento=desplazamiento)

    def _exigir_obra(self, id: UUID) -> None:
        if self._obras.obtener(id) is None:
            raise RegistroNoEncontrado("La obra no existe.")

    def _exigir_termino(self, id: UUID) -> TerminoClasificacion:
        termino = self._clasificaciones.obtener_termino(id)
        if termino is None:
            raise RegistroNoEncontrado("El término de clasificación no existe.")
        return termino

    @staticmethod
    def _fecha(fecha: datetime | None) -> datetime:
        return datetime.now(timezone.utc) if fecha is None else fecha

    @staticmethod
    def _validar_tipo(tipo: TipoClasificacion) -> None:
        if not isinstance(tipo, TipoClasificacion):
            raise ErrorValidacion("Tipo de clasificación inválido.")
