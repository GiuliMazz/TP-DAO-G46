"""Composición de lecturas para presentación. Una conexión por operación/hilo.

No importa herramientas de preparación, no migra ni siembra datos. Los servicios
conservan las reglas; sólo reúne sus resultados para las pantallas.
"""

from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from biblioteca.dominio.clasificacion import ClasificacionObra, EstadoClasificacion, TerminoClasificacion, TipoClasificacion
from biblioteca.dominio.edicion import Edicion
from biblioteca.dominio.sede import Sede
from biblioteca.errores import ErrorPersistencia
from biblioteca.persistencia.base_datos import VERSION_ESQUEMA, lectura_consistente
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.clasificacion_service import ClasificacionService
from biblioteca.servicios.inventario_service import InventarioService
from biblioteca.servicios.sede_service import SedeService
from biblioteca.resultados_catalogo import DetalleObra
from biblioteca.resultados_inventario import DisponibilidadSede

RAIZ = Path(__file__).resolve().parents[1]
BASE_DEMO = RAIZ / "datos/generados/catalogo_local/demo.db"
PORTADAS = RAIZ / "datos/catalogo_local/portadas"


@dataclass(frozen=True)
class ConfiguracionCatalogo:
    tipo: str
    sedes: tuple[Sede, ...]
    generos: tuple[TerminoClasificacion, ...]


@dataclass(frozen=True)
class FichaCatalogoLocal:
    detalle: DetalleObra
    ediciones: tuple[Edicion, ...]
    existencias: tuple[DisponibilidadSede, ...]
    clasificaciones: tuple[ClasificacionObra, ...]


def _todas(consulta, **filtros):
    """Recorrer catálogos pequeños de configuración/detalle, nunca listar obras."""
    filas, desplazamiento = [], 0
    while True:
        pagina = consulta(**filtros, limite=100, desplazamiento=desplazamiento)
        filas.extend(pagina)
        if len(pagina) < 100:
            return tuple(filas)
        desplazamiento += 100


class ConsultasCatalogoLocal:
    def __init__(self, base=BASE_DEMO):
        self.base = Path(base).resolve()

    def _abrir(self):
        conexion = None
        try:
            # mode=ro impide crear una base inexistente o modificar una preparada.
            conexion = sqlite3.connect(self.base.as_uri() + "?mode=ro", uri=True, timeout=2)
            conexion.row_factory = sqlite3.Row
            conexion.execute("PRAGMA foreign_keys = ON")
            if conexion.execute("PRAGMA user_version").fetchone()[0] != VERSION_ESQUEMA:
                raise ErrorPersistencia("La base necesita una preparación compatible antes de abrirla.")
            return conexion
        except (sqlite3.Error, ErrorPersistencia) as error:
            if conexion is not None:
                conexion.close()
            raise ErrorPersistencia("No se pudo abrir el catálogo local preparado. Verificá la base seleccionada.") from error

    @staticmethod
    def _catalogo(c):
        return CatalogoService(ObraRepository(c), EdicionRepository(c), AutorRepository(c))

    def configuracion(self):
        try:
            marcador = json.loads(self.base.with_suffix(self.base.suffix + ".tipo.json").read_text(encoding="utf-8"))
            tipo = marcador["tipo"]
            if marcador.get("version") != 1 or tipo not in ("OPERATIVA", "DEMOSTRACION", "RENDIMIENTO"):
                raise ValueError("Tipo desconocido")
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ErrorPersistencia("No se pudo verificar si la base es operativa o de demostración.") from error
        with closing(self._abrir()) as c, lectura_consistente(c):
            clasificaciones = ClasificacionService(ClasificacionRepository(c), ObraRepository(c))
            return ConfiguracionCatalogo(tipo, _todas(SedeService(SedeRepository(c)).listar),
                _todas(clasificaciones.listar_terminos, tipo=TipoClasificacion.GENERO))

    def consultar_pagina(self, **filtros):
        with closing(self._abrir()) as c:
            return self._catalogo(c).consultar_pagina(**filtros)

    def ficha(self, obra_id):
        with closing(self._abrir()) as c, lectura_consistente(c):
            catalogo = self._catalogo(c)
            inventario = InventarioService(EjemplarRepository(c), EdicionRepository(c),
                                           SedeRepository(c), ObraRepository(c))
            clasificador = ClasificacionService(ClasificacionRepository(c), ObraRepository(c))
            return FichaCatalogoLocal(catalogo.obtener_detalle(obra_id),
                _todas(catalogo.listar_ediciones, obra_id=obra_id),
                _todas(inventario.consultar_disponibilidad, obra_id=obra_id),
                _todas(clasificador.listar, obra_id=obra_id, estado=EstadoClasificacion.APROBADO))

    @staticmethod
    def portada_local(portada_id):
        if type(portada_id) is int and portada_id > 0:
            archivo = PORTADAS / f"{portada_id}.jpg"
            if archivo.is_file():
                return f"{portada_id}.jpg"
        return None
