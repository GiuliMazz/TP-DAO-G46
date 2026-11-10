"""Actualizar versión 1 preserva los registros ya existentes y es reversible ante fallos."""

from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest

from biblioteca.errores import ErrorPersistencia
from biblioteca.persistencia.base_datos import VERSION_ESQUEMA, conectar, migrar


def crear_base_version_1(ruta):
    # Usar el SQL histórico, no generar una base v2 y bajar artificialmente su versión.
    sql = Path("biblioteca/persistencia/migraciones/001_sedes_socios.sql").read_text(encoding="utf-8")
    sede_id, socio_id = str(uuid4()), str(uuid4())
    with closing(conectar(ruta)) as conexion:
        conexion.executescript(sql)
        conexion.execute("INSERT INTO sede VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (sede_id, "Centro", "centro", "Calle 1", "Contacto", "9 a 18", 0))
        conexion.execute("INSERT INTO socio VALUES (?, ?, ?, ?, ?, ?)",
                         (socio_id, "00123456", "Ana", "ana", "Contacto", "INHABILITADO"))
        conexion.execute("PRAGMA user_version = 1")
        conexion.commit()
    return sede_id, socio_id


def test_actualizar_version_1_preserva_todos_los_datos(ruta_db):
    sede_id, socio_id = crear_base_version_1(ruta_db)
    with closing(conectar(ruta_db)) as conexion:
        antes_sede = tuple(conexion.execute("SELECT * FROM sede").fetchone())
        antes_socio = tuple(conexion.execute("SELECT * FROM socio").fetchone())
        migrar(conexion)
        migrar(conexion)
        assert tuple(conexion.execute("SELECT * FROM sede WHERE id = ?", (sede_id,)).fetchone()) == antes_sede
        assert tuple(conexion.execute("SELECT * FROM socio WHERE id = ?", (socio_id,)).fetchone()) == antes_socio
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA
        assert conexion.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conexion.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_fallo_de_migracion_2_conserva_base_1_y_permite_reintentar(ruta_db, monkeypatch):
    crear_base_version_1(ruta_db)
    leer = Path.read_text

    def lectura_con_fallo(archivo, **kwargs):
        if archivo.name == "002_catalogo.sql":
            return "CREATE TABLE parcial (id INTEGER);\nERROR INTENCIONAL;\n"
        return leer(archivo, **kwargs)

    with closing(conectar(ruta_db)) as conexion:
        with monkeypatch.context() as parche:
            parche.setattr(Path, "read_text", lectura_con_fallo)
            with pytest.raises(ErrorPersistencia):
                migrar(conexion)
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conexion.execute("SELECT COUNT(*) FROM socio").fetchone()[0] == 1
        assert conexion.execute("SELECT name FROM sqlite_master WHERE name = 'parcial'").fetchone() is None
        assert conexion.execute("SELECT name FROM sqlite_master WHERE name = 'obra'").fetchone() is None
        migrar(conexion)
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA
