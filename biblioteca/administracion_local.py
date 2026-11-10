"""Composición de servicios para administración; conexiones propias, sin siembra."""

from contextlib import closing
import json
import sqlite3

from biblioteca.consultas_locales import BASE_DEMO, ConsultasCatalogoLocal
from biblioteca.errores import ErrorPersistencia, ErrorValidacion
from biblioteca.persistencia.base_datos import VERSION_ESQUEMA
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.inventario_service import InventarioService
from biblioteca.servicios.sede_service import SedeService
from biblioteca.servicios.socio_service import SocioService


class AdministracionLocal(ConsultasCatalogoLocal):
    ACCIONES = {
        "socios": frozenset({"registrar", "modificar", "habilitar", "inhabilitar"}),
        "sedes": frozenset({"registrar", "modificar", "activar", "dar_de_baja"}),
        "inventario": frozenset({"registrar", "registrar_condicion", "dar_de_baja"}),
    }

    def __init__(self, base=BASE_DEMO):
        super().__init__(base)

    @staticmethod
    def _servicio(c, entidad):
        if entidad == "socios":
            return SocioService(SocioRepository(c))
        if entidad == "sedes":
            return SedeService(SedeRepository(c))
        if entidad == "inventario":
            return InventarioService(EjemplarRepository(c), EdicionRepository(c),
                                     SedeRepository(c), ObraRepository(c))
        raise ErrorValidacion("Módulo de administración desconocido.")

    def listar(self, entidad, **filtros):
        with closing(self._abrir()) as c:
            return self._servicio(c, entidad).listar(**filtros)

    def _abrir_escritura(self):
        try:
            marca = json.loads(self.base.with_suffix(self.base.suffix + ".tipo.json").read_text(encoding="utf-8"))
            if marca.get("version") != 1 or marca.get("tipo") not in {"OPERATIVA", "DEMOSTRACION"}:
                raise ValueError("Base sin administración")
        except (OSError, ValueError, TypeError, AttributeError) as error:
            raise ErrorPersistencia("La base seleccionada no admite administración. Verificá su tipo.") from error
        c = None
        try:
            c = sqlite3.connect(self.base.as_uri() + "?mode=rw", uri=True, timeout=2)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys = ON")
            if c.execute("PRAGMA user_version").fetchone()[0] != VERSION_ESQUEMA:
                raise ErrorPersistencia("Prepará una base compatible antes de guardar.")
            return c
        except (sqlite3.Error, ErrorPersistencia) as error:
            if c is not None:
                c.close()
            raise ErrorPersistencia("No se pudo abrir la base preparada para guardar.") from error

    def ejecutar(self, entidad, accion, *args, **datos):
        if accion not in self.ACCIONES.get(entidad, ()):
            raise ErrorValidacion("Operación de administración desconocida.")
        with closing(self._abrir_escritura()) as c:
            return getattr(self._servicio(c, entidad), accion)(*args, **datos)
