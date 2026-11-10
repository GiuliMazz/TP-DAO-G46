"""Integridad SQLite, transacciones compartidas y migraciones no destructivas."""

from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest

from biblioteca.dominio.sede import Sede
from biblioteca.dominio.socio import Socio
from biblioteca.errores import ErrorPersistencia, RegistroDuplicado, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import VERSION_ESQUEMA, conectar, migrar, transaccion
from biblioteca.repositorios.sede_repository import SedeRepository


def test_conexion_habilita_claves_foraneas_y_versiona_esquema(conexion):
    assert conexion.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA
    assert conexion.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conexion.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_migracion_repetida_preserva_los_registros(conexion, sedes, socios):
    sede = sedes.registrar("Centro", "Calle 1", "Contacto", "9 a 18")
    socio = socios.registrar("12345678", "Ana Pérez", "Contacto")
    migrar(conexion)
    migrar(conexion)
    assert sedes.obtener(sede.id).nombre == "Centro"
    assert socios.obtener(socio.id).documento == "12345678"


def test_no_se_modifica_una_base_ajena_sin_version(ruta_db):
    with closing(conectar(ruta_db)) as conexion:
        conexion.execute("CREATE TABLE obra (titulo TEXT)")
        conexion.execute("INSERT INTO obra VALUES ('Muestra del importador')")
        conexion.commit()
        with pytest.raises(ErrorPersistencia, match="base nueva"):
            migrar(conexion)
        assert conexion.execute("SELECT titulo FROM obra").fetchone()[0] == "Muestra del importador"
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conexion.execute("SELECT name FROM sqlite_master WHERE name = 'sede'").fetchone() is None


def test_version_futura_se_rechaza_sin_retroceder(conexion):
    conexion.execute("PRAGMA user_version = 99")
    with pytest.raises(ErrorPersistencia, match="más nueva"):
        migrar(conexion)
    assert conexion.execute("PRAGMA user_version").fetchone()[0] == 99


@pytest.mark.parametrize(
    "sql",
    ["CREATE TABLE parcial (id INTEGER);\nESTO NO ES SQL;\n",
     "CREATE TABLE parcial (id INTEGER);\nCREATE TABLE incompleta ("],
)
def test_migracion_con_fallo_revierte_incluso_el_ddl(ruta_db, monkeypatch, sql):
    with closing(conectar(ruta_db)) as conexion:
        with monkeypatch.context() as parche:
            parche.setattr(Path, "read_text", lambda self, **kwargs: sql)
            with pytest.raises(ErrorPersistencia):
                migrar(conexion)
        assert conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == 0
        migrar(conexion)
        assert conexion.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA


def test_unique_de_base_impide_duplicados_sin_pasar_por_servicios(
    conexion, sede_repository, socio_repository
):
    with transaccion(conexion):
        sede_repository.agregar(Sede("Centro", "Calle 1", "Contacto", "9 a 18"))
        socio_repository.agregar(Socio("12.345.678", "Ana", "Contacto"))
    with pytest.raises(RegistroDuplicado):
        with transaccion(conexion):
            sede_repository.agregar(Sede(" CENTRO ", "Calle 2", "Contacto", "9 a 18"))
    with pytest.raises(RegistroDuplicado):
        with transaccion(conexion):
            socio_repository.agregar(Socio("12345678", "Otra persona", "Contacto"))
    assert len(sede_repository.listar()) == 1
    assert len(socio_repository.listar()) == 1


def test_repositorios_no_confirman_por_su_cuenta_y_se_revierten_juntos(
    conexion, sede_repository, socio_repository, ruta_db
):
    with pytest.raises(RuntimeError, match="fallo posterior"):
        with transaccion(conexion):
            sede_repository.agregar(Sede("Centro", "Calle 1", "Contacto", "9 a 18"))
            socio_repository.agregar(Socio("12345678", "Ana", "Contacto"))
            with closing(conectar(ruta_db)) as observador:
                assert observador.execute("SELECT COUNT(*) FROM sede").fetchone()[0] == 0
                assert observador.execute("SELECT COUNT(*) FROM socio").fetchone()[0] == 0
            raise RuntimeError("fallo posterior a ambas escrituras")
    assert sede_repository.listar() == []
    assert socio_repository.listar() == []


def test_no_se_confirma_una_transaccion_ajena_al_intentar_anidar(conexion, sede_repository):
    sede = Sede("Centro", "Calle 1", "Contacto", "9 a 18")
    with transaccion(conexion):
        sede_repository.agregar(sede)
        with pytest.raises(ErrorPersistencia, match="activa"):
            with transaccion(conexion):
                pass
        assert conexion.in_transaction
    assert sede_repository.obtener(sede.id) is not None


def test_repositorios_no_hacen_upsert_implicito(sede_repository, socio_repository):
    assert sede_repository.obtener(uuid4()) is None
    assert socio_repository.obtener(uuid4()) is None
    with pytest.raises(RegistroNoEncontrado):
        sede_repository.actualizar(Sede("Centro", "Calle 1", "Contacto", "9 a 18"))
    sede_repository.conexion.rollback()
    with pytest.raises(RegistroNoEncontrado):
        socio_repository.actualizar(Socio("12345678", "Ana", "Contacto"))
    socio_repository.conexion.rollback()


def test_errores_sql_no_salen_como_excepciones_sqlite_crudas(ruta_db):
    with closing(conectar(ruta_db)) as conexion:
        with pytest.raises(ErrorPersistencia, match="consultar"):
            SedeRepository(conexion).obtener(uuid4())
