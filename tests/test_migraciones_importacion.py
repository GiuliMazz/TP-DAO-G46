"""Actualizar una base de esquema 4 conservando administración y revisiones."""

from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from biblioteca.dominio.clasificacion import EstadoClasificacion
from biblioteca.errores import ErrorPersistencia
from biblioteca.persistencia.base_datos import VERSION_ESQUEMA, conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.clasificacion_service import ClasificacionService
from biblioteca.servicios.inventario_service import InventarioService
from biblioteca.servicios.sede_service import SedeService
from biblioteca.servicios.socio_service import SocioService


def crear_version_4(ruta):
    with closing(conectar(ruta)) as c:
        carpeta = Path("biblioteca/persistencia/migraciones")
        for nombre in ("001_sedes_socios.sql", "002_catalogo.sql", "003_inventario.sql", "004_clasificacion.sql"):
            c.executescript((carpeta / nombre).read_text(encoding="utf-8"))
        c.execute("PRAGMA user_version = 4")
        obras, ediciones = ObraRepository(c), EdicionRepository(c)
        catalogo = CatalogoService(obras, ediciones, AutorRepository(c))
        clasificaciones = ClasificacionService(ClasificacionRepository(c), obras)
        sedes = SedeService(SedeRepository(c))
        socios = SocioService(SocioRepository(c))
        inventario = InventarioService(EjemplarRepository(c), ediciones, SedeRepository(c), obras)
        sede = sedes.registrar("Centro", "Dirección", "Contacto", "9 a 18")
        socio = socios.registrar("12345678", "Ana", "Contacto")
        socios.inhabilitar(socio.id)
        a = catalogo.registrar_autor("Autora")
        o = catalogo.registrar_obra("Original", [a.id])
        e = catalogo.registrar_edicion(o.id, "Español")
        copia = inventario.registrar("HZ-ANTES", e.id, sede.id)
        inventario.dar_de_baja(copia.id)
        sedes.dar_de_baja(sede.id)
        reglas = clasificaciones.preparar_reglas_iniciales()
        clasificaciones.procesar_materias(o.id, ["Fantasy fiction"], reglas)
        clasificaciones.revisar(o.id, reglas[0].termino_id, EstadoClasificacion.RECHAZADO, "Revisión que debe conservarse")
        tablas = [f[0] for f in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        return {t: [tuple(f) for f in c.execute(f'SELECT * FROM "{t}" ORDER BY 1, 2')] for t in tablas}


def comprobar_datos(c, anteriores):
    for tabla, filas in anteriores.items():
        assert [tuple(f) for f in c.execute(f'SELECT * FROM "{tabla}" ORDER BY 1, 2')] == filas


def test_actualizacion_desde_4_conserva_todas_las_filas_y_estados(ruta_db):
    antes = crear_version_4(ruta_db)
    with closing(conectar(ruta_db)) as c:
        migrar(c)
        migrar(c)
        comprobar_datos(c, antes)
        assert c.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA
        for tabla in ("evaluacion_importacion", "decision_importacion", "seguimiento_importacion"):
            assert c.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == 0
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_fallo_migracion_5_preserva_version_4_y_admite_reintento(ruta_db, monkeypatch):
    antes = crear_version_4(ruta_db)
    leer = Path.read_text
    def lectura(archivo, **kwargs):
        return "CREATE TABLE parcial (id INTEGER);\nFALLO;\n" if archivo.name == "005_importacion.sql" else leer(archivo, **kwargs)
    with closing(conectar(ruta_db)) as c:
        with monkeypatch.context() as m:
            m.setattr(Path, "read_text", lectura)
            with pytest.raises(ErrorPersistencia):
                migrar(c)
        comprobar_datos(c, antes)
        assert c.execute("PRAGMA user_version").fetchone()[0] == 4
        assert c.execute("SELECT name FROM sqlite_master WHERE name = 'parcial'").fetchall() == []
        migrar(c)
        assert c.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA


def test_clave_compuesta_impide_aplicar_decision_de_otra_edicion(importacion, candidato_ol, conexion):
    from biblioteca.importacion.modelos import CandidatoOpenLibrary
    primera = importacion.evaluar(candidato_ol)
    d = candidato_ol.datos
    d["edicion"]["id_openlibrary"] = "OL101M"
    d["detalle"] = None
    segunda = importacion.evaluar(CandidatoOpenLibrary.desde_datos(d))
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute("UPDATE seguimiento_importacion SET decision_id = ? WHERE edicion_ol = ?",
                         (primera.decision_id, segunda.edicion_ol))
    conexion.rollback()
