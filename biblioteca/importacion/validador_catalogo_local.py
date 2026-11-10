"""Política OL-2-LOCAL: ausencias permitidas, evidencia e identidades obligatorias."""

from dataclasses import replace

from biblioteca.errores import ErrorValidacion
from biblioteca.importacion.modelos import EstadoImportacion
from biblioteca.importacion.validador_openlibrary import ValidadorOpenLibrary


class ValidadorCatalogoLocal(ValidadorOpenLibrary):
    VERSION = "OL-2-LOCAL"
    EXIGIR_ISBN_PORTADA = False
    RECHAZAR_ISBN_INVALIDOS = True

    def _detalle_obra(self, detalle):
        if "obra" in detalle:
            return detalle["obra"]
        busqueda = detalle["busqueda"]
        autores = self._autores_busqueda(busqueda)
        # Proyección interna de Search, no una supuesta respuesta del endpoint Works.
        # La instantánea persiste el documento Search original, sin transformarlo.
        return {"key": busqueda["key"], "title": busqueda["title"],
                "authors": [{"author": {"key": "/authors/" + a[0]}} for a in autores],
                "subjects": busqueda.get("subject", [])}

    def evaluar(self, candidato):
        evaluacion = super().evaluar(candidato)
        detalle = candidato.datos.get("detalle")
        if isinstance(detalle, dict) and "busqueda" in detalle:
            try:
                if detalle["busqueda"]["key"] != "/works/" + candidato.datos["obra"]["id_openlibrary"]:
                    raise ErrorValidacion("La búsqueda corresponde a otra obra.")
                reales = self._autores_busqueda(detalle["busqueda"])
                preparados = [(a["id_openlibrary"], a["nombre"]) for a in candidato.datos["autores"]]
                if preparados != reales:
                    raise ErrorValidacion("La autoría preparada difiere de Search.")
                nombres = [" ".join(nombre.split()).casefold() for _, nombre in reales]
                if len(nombres) != len(set(nombres)) and evaluacion.estado is EstadoImportacion.VALIDADA:
                    evaluacion = replace(evaluacion, estado=EstadoImportacion.ENRIQUECIDA,
                        alertas=(*evaluacion.alertas, "autores_con_mismo_nombre_revisar"))
            except (ErrorValidacion, KeyError, TypeError, ValueError):
                evaluacion = replace(evaluacion, estado=EstadoImportacion.RECHAZADA,
                    controles={**evaluacion.controles, "autores": False},
                    alertas=(*evaluacion.alertas, "autores_preparados_sin_respaldo"))
        return evaluacion

    def _autores_busqueda(self, busqueda):
        ids, nombres = busqueda["author_key"], busqueda["author_name"]
        if not isinstance(ids, list) or not isinstance(nombres, list) or not ids or len(ids) != len(nombres):
            raise ErrorValidacion("Search debe identificar cada autor con su nombre.")
        if any(not isinstance(nombre, str) or not nombre.strip() for nombre in nombres):
            raise ErrorValidacion("Cada autor debe tener un nombre usable.")
        return [(self._id(id, "A"), nombre) for id, nombre in zip(ids, nombres, strict=True)]
