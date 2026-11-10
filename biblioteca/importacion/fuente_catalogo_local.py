"""Manifiesto local verificable: JSON de Search/ediciones y portadas ya capturadas."""

from hashlib import sha256
import json
from pathlib import Path

from biblioteca.errores import ErrorValidacion
from biblioteca.importacion.modelos import CandidatoOpenLibrary, json_canonico


def candidato_desde_respuestas(busqueda: dict, edicion: dict, obra: dict | None = None,
                               *, origen: dict | None = None) -> CandidatoOpenLibrary:
    """Adaptar evidencia sin modificar los documentos originales ni inventar detalle."""
    wid = busqueda["key"].removeprefix("/works/")
    eid = edicion["key"].removeprefix("/books/")
    ids, nombres = busqueda["author_key"], busqueda["author_name"]
    if len(ids) != len(nombres):
        raise ErrorValidacion("La respuesta no identifica todos los autores.")
    detalle = {"busqueda": busqueda, "edicion": edicion}
    if obra is not None:
        detalle["obra"] = obra
    return CandidatoOpenLibrary.desde_datos({
        "obra": {"id_openlibrary": wid, "titulo_original": busqueda["title"],
                 "anio_primera_publicacion": busqueda.get("first_publish_year"),
                 "portada_obra_id": busqueda.get("cover_i")},
        "edicion": {"id_openlibrary": eid, "obra_id": wid, "titulo": edicion["title"]},
        "autores": [{"id_openlibrary": id, "nombre": nombre}
                    for id, nombre in zip(ids, nombres, strict=True)],
        "materias": busqueda.get("subject", []), "detalle": detalle,
        "origen": origen or {"tipo": "captura_local"},
    })


class FuenteCatalogoLocal:
    def __init__(self, manifiesto: str | Path):
        self.ruta = Path(manifiesto).resolve()
        self.raiz = self.ruta.parent
        try:
            self.datos = json.loads(self.ruta.read_text(encoding="utf-8"))
            if self.datos["version"] != 1 or self.datos["politica"] != "OL-2-LOCAL":
                raise ValueError("Versión o política no soportada")
            registros = self.datos["registros"]
            if not isinstance(registros, list) or not 1 <= len(registros) <= 150:
                raise ValueError("Se requiere una selección acotada de 1 a 150 obras")
            obras = [r["obra_id"] for r in registros]
            ediciones = [r["edicion_id"] for r in registros]
            if len(set(obras)) != len(obras) or len(set(ediciones)) != len(ediciones):
                raise ValueError("Identidades repetidas en la selección")
            self.fuentes = {}
            for nombre, huella in self.datos["fuentes"].items():
                contenido = self._verificar_archivo(nombre, huella)
                self.fuentes[nombre] = json.loads(contenido)
            self.portadas = {}
            for p in self.datos["portadas"]:
                if type(p["id"]) is not int or p["id"] <= 0 or p["id"] in self.portadas:
                    raise ValueError("Identidad de portada inválida o repetida")
                self._verificar_archivo(p["archivo"], p["sha256"])
                self.portadas[p["id"]] = self._ruta_local(p["archivo"])
            self.coleccion = sha256(json_canonico(sorted(zip(obras, ediciones))).encode()).hexdigest()
            # Construir todo antes de que un preparador pueda abrir una base destino.
            self.candidatos = tuple(self._candidato(r) for r in registros)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise ErrorValidacion(f"No se pudo verificar el catálogo local: {error}") from error

    def _ruta_local(self, nombre):
        ruta = (self.raiz / nombre).resolve()
        if not ruta.is_relative_to(self.raiz) or ruta == self.ruta:
            raise ValueError("Una fuente no puede salir de la carpeta del catálogo")
        return ruta

    def _verificar_archivo(self, nombre, huella):
        contenido = self._ruta_local(nombre).read_bytes()
        if sha256(contenido).hexdigest() != huella:
            raise ValueError(f"La huella no coincide: {nombre}")
        return contenido

    def _candidato(self, registro):
        wid, eid = registro["obra_id"], registro["edicion_id"]
        b = self.fuentes["fuentes/busquedas.json"][wid]
        e = self.fuentes["fuentes/ediciones.json"][eid]
        w = self.fuentes["fuentes/obras.json"].get(wid)
        if b["datos"]["key"] != "/works/" + wid or e["datos"]["key"] != "/books/" + eid:
            raise ValueError("La identidad de una captura no corresponde a la selección")
        origen = {"tipo": "catalogo_local_v1", "busqueda_url": b["url"], "edicion_url": e["url"],
                  "obra_url": w["url"] if w else None,
                  "busqueda_sha256": sha256(json_canonico(b["datos"]).encode()).hexdigest(),
                  "edicion_sha256": sha256(json_canonico(e["datos"]).encode()).hexdigest(),
                  "edicion_captura_utc": e.get("captura_utc")}
        return candidato_desde_respuestas(b["datos"], e["datos"], w["datos"] if w else None, origen=origen)

    def iterar(self):
        return iter(self.candidatos)
