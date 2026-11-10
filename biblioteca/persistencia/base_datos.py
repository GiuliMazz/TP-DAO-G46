"""Infraestructura SQLite; no contiene políticas de circulación."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from biblioteca.errores import ErrorPersistencia, RegistroDuplicado

MIGRACIONES = ("001_sedes_socios.sql", "002_catalogo.sql", "003_inventario.sql",
               "004_clasificacion.sql", "005_importacion.sql", "006_indices_consultas.sql")
VERSION_ESQUEMA = len(MIGRACIONES)


def conectar(ruta: str | Path) -> sqlite3.Connection:
    try:
        conexion = sqlite3.connect(str(ruta), isolation_level="DEFERRED")
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys = ON")
        return conexion
    except sqlite3.Error as error:
        raise ErrorPersistencia("No se pudo abrir la base de datos.") from error


@contextmanager
def transaccion(conexion: sqlite3.Connection) -> Iterator[None]:
    """Un caso de uso confirma todo o revierte todo; no anida transacciones."""
    if conexion.in_transaction:
        raise ErrorPersistencia("Ya hay una transacción activa en esta conexión.")
    try:
        # Serializar escritores antes de comprobar unicidad y modificar datos.
        conexion.execute("BEGIN IMMEDIATE")
        yield
        conexion.commit()
    except sqlite3.Error as error:
        conexion.rollback()
        raise ErrorPersistencia("No se pudo completar la operación en la base de datos.") from error
    except BaseException:
        conexion.rollback()
        raise


def ejecutar(
    conexion: sqlite3.Connection,
    sql: str,
    parametros: tuple[object, ...] = (),
) -> sqlite3.Cursor:
    """Ejecutar SQL del repositorio y traducir fallos a errores de aplicación."""
    try:
        return conexion.execute(sql, parametros)
    except sqlite3.IntegrityError as error:
        if error.sqlite_errorcode in (
            sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY,
        ):
            raise RegistroDuplicado("El identificador o dato único ya está registrado.") from error
        raise ErrorPersistencia("Los datos no cumplen las restricciones de la base.") from error
    except sqlite3.Error as error:
        raise ErrorPersistencia("No se pudo consultar o guardar el registro.") from error


@contextmanager
def lectura_consistente(conexion: sqlite3.Connection) -> Iterator[None]:
    """Una instantánea para varias consultas; no adquiere bloqueo de escritor.

    Respeta una transacción ya iniciada por el llamador. Una lectura independiente
    se cierra con rollback, sin confirmar escrituras ajenas.
    """
    propia = not conexion.in_transaction
    try:
        if propia:
            ejecutar(conexion, "BEGIN")
        yield
    finally:
        if propia:
            conexion.rollback()


def migrar(conexion: sqlite3.Connection) -> None:
    """Preparar sólo la base operativa; nunca reconstruir ni borrar datos."""
    with transaccion(conexion):
        version = conexion.execute("PRAGMA user_version").fetchone()[0]
        if version > VERSION_ESQUEMA:
            raise ErrorPersistencia("La base usa una versión de esquema más nueva que la aplicación.")
        if version == VERSION_ESQUEMA:
            return
        if version < 0:
            raise ErrorPersistencia("La versión de esquema no es válida.")
        if version == 0:
            tablas = conexion.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            if tablas:
                raise ErrorPersistencia(
                    "La base contiene tablas sin versión operativa. Use una base nueva; "
                    "las muestras de Open Library se integran por separado."
                )
        for numero, nombre in enumerate(MIGRACIONES, start=1):
            if numero > version:
                _aplicar_migracion(conexion, nombre)
                conexion.execute(f"PRAGMA user_version = {numero}")


def _aplicar_migracion(conexion: sqlite3.Connection, nombre: str) -> None:
    archivo = Path(__file__).parent / "migraciones" / nombre
    try:
        esquema = archivo.read_text(encoding="utf-8")
    except OSError as error:
        raise ErrorPersistencia("No se pudo leer la migración del esquema.") from error
    # executescript confirma transacciones previas; mantener DDL y versión juntos.
    sentencia = ""
    for linea in esquema.splitlines(keepends=True):
        sentencia += linea
        if sqlite3.complete_statement(sentencia):
            conexion.execute(sentencia)
            sentencia = ""
    if sentencia.strip():
        raise ErrorPersistencia("La migración contiene una sentencia SQL incompleta.")
