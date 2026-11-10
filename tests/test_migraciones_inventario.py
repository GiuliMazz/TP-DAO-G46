"""Actualizar una base auténtica de versión 2, sin perder catálogo ni administración."""

from contextlib import closing
from pathlib import Path

import pytest

from biblioteca.errores import ErrorPersistencia
from biblioteca.persistencia.base_datos import VERSION_ESQUEMA, conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.sede_service import SedeService
from biblioteca.servicios.socio_service import SocioService


def crear_version_2(ruta):
    carpeta = Path("biblioteca/persistencia/migraciones")
    with closing(conectar(ruta)) as conexion:
        for nombre in ("001_sedes_socios.sql", "002_catalogo.sql"):
            conexion.executescript((carpeta / nombre).read_text(encoding="utf-8"))
        conexion.execute("PRAGMA user_version = 2")
        sedes = SedeService(SedeRepository(conexion))
        socios = SocioService(SocioRepository(conexion))
        catalogo = CatalogoService(ObraRepository(conexion), EdicionRepository(conexion),
                                   AutorRepository(conexion))
        sede = sedes.registrar("Centro", "Calle 1", "Contacto", "9 a 18")
        sedes.dar_de_baja(sede.id)
        socio = socios.registrar("00123456", "Ana", "Contacto")
        socios.inhabilitar(socio.id)
        autor = catalogo.registrar_autor("Autora", id_openlibrary="OL10A")
        obra = catalogo.registrar_obra("Original", [autor.id], id_openlibrary="OL20W")
        catalogo.registrar_edicion(obra.id, "Español", id_openlibrary="OL30M",
                                   isbn_13="9780306406157")
        tablas = ("sede", "socio", "autor", "obra", "obra_autor", "edicion")
        return {tabla: [tuple(fila) for fila in conexion.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2")]
                for tabla in tablas}


def test_migracion_2_a_3_conserva_datos_identidades_relaciones_y_preferencia(ruta_db):
    antes = crear_version_2(ruta_db)
    with closing(conectar(ruta_db)) as conexion:
        migrar(conexion)
        migrar(conexion)
        for tabla, filas in antes.items():
            assert [tuple(fila) for fila in conexion.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2")] == filas
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA
        assert conexion.execute("SELECT COUNT(*) FROM ejemplar").fetchone()[0] == 0
        assert conexion.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conexion.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_fallo_de_migracion_3_conserva_version_2_y_su_datos(ruta_db, monkeypatch):
    antes = crear_version_2(ruta_db)
    leer = Path.read_text

    def fallo_en_tercera(archivo, **kwargs):
        if archivo.name == "003_inventario.sql":
            return "CREATE TABLE parcial (id INTEGER);\nFALLO INTENCIONAL;\n"
        return leer(archivo, **kwargs)

    with closing(conectar(ruta_db)) as conexion:
        with monkeypatch.context() as parche:
            parche.setattr(Path, "read_text", fallo_en_tercera)
            with pytest.raises(ErrorPersistencia):
                migrar(conexion)
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == 2
        assert conexion.execute("SELECT name FROM sqlite_master WHERE name IN ('parcial', 'ejemplar')").fetchall() == []
        for tabla, filas in antes.items():
            assert [tuple(fila) for fila in conexion.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2")] == filas
        migrar(conexion)
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA
