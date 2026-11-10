"""La clasificación se agrega a una base versión 3 sin reconstruir el inventario."""

from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from biblioteca.dominio.ejemplar import CondicionFisica
from biblioteca.errores import ErrorPersistencia
from biblioteca.persistencia.base_datos import VERSION_ESQUEMA, conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.inventario_service import InventarioService
from biblioteca.servicios.sede_service import SedeService
from biblioteca.servicios.socio_service import SocioService


def instantanea(conexion):
    tablas = ("sede", "socio", "autor", "obra", "edicion", "obra_autor", "ejemplar")
    return {tabla: [tuple(f) for f in conexion.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2")]
            for tabla in tablas}


def crear_version_3(ruta):
    with closing(conectar(ruta)) as conexion:
        carpeta = Path("biblioteca/persistencia/migraciones")
        for nombre in ("001_sedes_socios.sql", "002_catalogo.sql", "003_inventario.sql"):
            conexion.executescript((carpeta / nombre).read_text(encoding="utf-8"))
        conexion.execute("PRAGMA user_version = 3")
        sedes = SedeService(SedeRepository(conexion))
        socios = SocioService(SocioRepository(conexion))
        obras = ObraRepository(conexion)
        ediciones = EdicionRepository(conexion)
        catalogo = CatalogoService(obras, ediciones, AutorRepository(conexion))
        inventario = InventarioService(EjemplarRepository(conexion), ediciones, SedeRepository(conexion), obras)
        sede = sedes.registrar("Centro", "Dirección", "Contacto", "9 a 18")
        socio = socios.registrar("12345678", "Ana", "Contacto")
        socios.inhabilitar(socio.id)
        autor = catalogo.registrar_autor("Autora", id_openlibrary="OL1A")
        obra = catalogo.registrar_obra("Original", [autor.id], id_openlibrary="OL1W")
        edicion = catalogo.registrar_edicion(obra.id, "Español", id_openlibrary="OL1M")
        copia = inventario.registrar("HZ-001", edicion.id, sede.id)
        inventario.registrar_condicion(copia.id, CondicionFisica.DANIADO)
        inventario.dar_de_baja(copia.id)
        sedes.dar_de_baja(sede.id)
        return instantanea(conexion)


def test_migracion_desde_3_preserva_inventario_y_catalogo(ruta_db):
    antes = crear_version_3(ruta_db)
    with closing(conectar(ruta_db)) as conexion:
        migrar(conexion)
        migrar(conexion)
        assert instantanea(conexion) == antes
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA
        for tabla in ("termino_clasificacion", "clasificacion_obra", "materia_original",
                      "decision_clasificacion", "evidencia_clasificacion", "regla_clasificacion"):
            assert conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == 0
        assert conexion.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conexion.execute("PRAGMA foreign_key_check").fetchall() == []


def test_fallo_migracion_4_revierte_ddl_version_y_preserva_datos(ruta_db, monkeypatch):
    antes = crear_version_3(ruta_db)
    leer = Path.read_text

    def lectura(archivo, **kwargs):
        if archivo.name == "004_clasificacion.sql":
            return "CREATE TABLE parcial (id INTEGER);\nFALLO INTENCIONAL;\n"
        return leer(archivo, **kwargs)

    with closing(conectar(ruta_db)) as conexion:
        with monkeypatch.context() as parche:
            parche.setattr(Path, "read_text", lectura)
            with pytest.raises(ErrorPersistencia):
                migrar(conexion)
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == 3
        assert instantanea(conexion) == antes
        assert conexion.execute("SELECT name FROM sqlite_master WHERE name = 'parcial'").fetchall() == []
        migrar(conexion)
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA


def test_base_impide_mezclar_genero_con_publico_y_estados_invalidos(conexion, catalogo, clasificaciones):
    autor = catalogo.registrar_autor("Autor")
    obra = catalogo.registrar_obra("Obra", [autor.id])
    regla = clasificaciones.preparar_reglas_iniciales()[0]
    for tipo, estado in (("PUBLICO", "APROBADO"), ("GENERO", "INVENTADO")):
        with pytest.raises(sqlite3.IntegrityError):
            conexion.execute("""INSERT INTO clasificacion_obra (obra_id, termino_id, tipo, estado, metodo, motivo, fecha)
                              VALUES (?, ?, ?, ?, 'MANUAL', 'Motivo', '2026-11-03T12:00:00+00:00')""",
                             (str(obra.id), str(regla.termino_id), tipo, estado))
        conexion.rollback()


def test_evidencia_no_puede_usar_materia_de_otra_obra(conexion, catalogo, clasificaciones):
    autor = catalogo.registrar_autor("Autor")
    obras = [catalogo.registrar_obra(n, [autor.id]) for n in ("Uno", "Dos")]
    reglas = clasificaciones.preparar_reglas_iniciales()
    for obra in obras:
        clasificaciones.procesar_materias(obra.id, ["Fantasy fiction"], reglas)
    materia_ajena = clasificaciones.materias(obras[1].id)[0]["id"]
    with pytest.raises(sqlite3.IntegrityError):
        conexion.execute("""UPDATE evidencia_clasificacion SET materia_id = ? WHERE obra_id = ?""",
                         (materia_ajena, str(obras[0].id)))
    conexion.rollback()
