"""Adaptador del contrato de preparación existente. Nunca escribe la fuente."""

from collections.abc import Iterator
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from biblioteca.errores import ErrorValidacion
from biblioteca.importacion.modelos import CandidatoOpenLibrary, json_canonico


class FuenteOpenLibrary:
    def __init__(self, base: str | Path, detalles: str | Path | None = None) -> None:
        self.base = Path(base).resolve()
        self.detalles = Path(detalles).resolve() if detalles is not None else None
        self._detalles: dict[str, list[dict]] = {}
        if self.detalles is not None:
            try:
                registros = json.loads(self.detalles.read_text(encoding="utf-8"))
                if not isinstance(registros, list):
                    raise ValueError("Se requiere una lista de registros originales.")
                for registro in registros:
                    if not isinstance(registro, dict) or not isinstance(registro.get("edicion"), dict):
                        raise ValueError("Registro de detalle mal formado.")
                    key = registro["edicion"].get("key")
                    if not isinstance(key, str) or not key.startswith("/books/"):
                        raise ValueError("Detalle sin clave de edición.")
                    lista = self._detalles.setdefault(key.removeprefix("/books/"), [])
                    if all(json_canonico(r) != json_canonico(registro) for r in lista):
                        lista.append(registro)
            except (OSError, ValueError, TypeError) as error:
                raise ErrorValidacion("No se pudieron leer los detalles originales de Open Library.") from error

    def iterar(self, *, limite: int | None = None) -> Iterator[CandidatoOpenLibrary]:
        if limite is not None and (type(limite) is not int or limite < 1):
            raise ErrorValidacion("El límite de importación debe ser un entero positivo.")
        try:
            with closing(sqlite3.connect(self.base.as_uri() + "?mode=ro", uri=True)) as conexion:
                conexion.row_factory = sqlite3.Row
                conexion.execute("PRAGMA query_only = ON")
                columnas = {f["name"] for f in conexion.execute("PRAGMA table_info(edicion)")}
                if "estado_validacion" not in columnas or "obra_id" not in columnas:
                    raise ErrorValidacion("La fuente no tiene el esquema de preparación esperado.")
                consulta = "SELECT * FROM edicion ORDER BY id_openlibrary"
                cursor = conexion.execute(consulta + (" LIMIT ?" if limite is not None else ""),
                                          (limite,) if limite is not None else ())
                for edicion in cursor:
                    obra = conexion.execute("SELECT * FROM obra WHERE id_openlibrary = ?", (edicion["obra_id"],)).fetchone()
                    autores = conexion.execute(
                        """SELECT a.* FROM autor a JOIN obra_autor oa ON oa.autor_id = a.id_openlibrary
                           WHERE oa.obra_id = ? ORDER BY a.id_openlibrary""", (edicion["obra_id"],)).fetchall()
                    materias = conexion.execute(
                        """SELECT m.texto FROM materia_original m
                           JOIN obra_materia_original om ON om.materia_id = m.id
                           WHERE om.obra_id = ? ORDER BY m.id""", (edicion["obra_id"],)).fetchall()
                    detalles = self._detalles.get(edicion["id_openlibrary"], [])
                    yield CandidatoOpenLibrary.desde_datos({
                        "obra": dict(obra) if obra else {}, "edicion": dict(edicion),
                        "autores": [dict(a) for a in autores], "materias": [m["texto"] for m in materias],
                        "detalle": detalles[0] if len(detalles) == 1 else None,
                        "detalle_ambiguo": len(detalles) > 1,
                        "origen": {"base": str(self.base), "detalles": str(self.detalles) if self.detalles else None},
                    })
        except sqlite3.Error as error:
            raise ErrorValidacion("No se pudo consultar la fuente bibliográfica en modo de sólo lectura.") from error
