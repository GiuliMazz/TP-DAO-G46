"""Política OL-1: controles objetivos y alertas bibliográficas independientes."""

import re
from uuid import uuid4

from biblioteca.dominio.autor import Autor
from biblioteca.dominio.bibliografia import id_openlibrary, normalizar_isbn, isbn13_desde_isbn10
from biblioteca.dominio.edicion import Edicion
from biblioteca.dominio.obra import Obra
from biblioteca.dominio.validacion import texto_obligatorio
from biblioteca.errores import ErrorValidacion
from biblioteca.importacion.modelos import CandidatoOpenLibrary, EstadoImportacion as Estado, EvaluacionOpenLibrary


class ValidadorOpenLibrary:
    VERSION = "OL-1"
    EXIGIR_ISBN_PORTADA = True
    RECHAZAR_ISBN_INVALIDOS = False

    def evaluar(self, candidato: CandidatoOpenLibrary) -> EvaluacionOpenLibrary:
        datos = candidato.datos
        controles = dict.fromkeys(("identidades", "relaciones", "autores", "detalle", "idioma", "isbn", "portada", "campos"), False)
        alertas: list[str] = []
        normalizados = None
        contradictorio = bool(datos.get("detalle_ambiguo"))
        if contradictorio:
            alertas.append("detalles_contradictorios")
        try:
            obra, edicion = datos["obra"], datos["edicion"]
            wid = self._id(obra["id_openlibrary"], "W")
            eid = self._id(edicion["id_openlibrary"], "M")
            controles["identidades"] = True
            controles["relaciones"] = edicion.get("obra_id") == wid
            contradictorio |= not controles["relaciones"]
            autores = datos["autores"]
            if not isinstance(autores, list) or not autores:
                raise ErrorValidacion("Faltan autores identificados.")
            for autor in autores:
                Autor(autor["nombre"], id_openlibrary=self._id(autor["id_openlibrary"], "A"))
            autor_ids = [a["id_openlibrary"] for a in autores]
            controles["autores"] = len(set(autor_ids)) == len(autor_ids)
            if len(autores) > 5:
                alertas.append("muchos_autores_revisar_creditos")
            if edicion.get("estado_validacion") == "RECHAZADA":
                alertas.append("rechazo_en_fuente")
            detalle = datos.get("detalle")
            if detalle is None:
                titulo = edicion.get("titulo", "")
                if isinstance(titulo, str) and len(titulo.strip()) <= 4:
                    alertas.append("titulo_breve_revisar")
                return self._resultado(candidato, controles, alertas, None, contradictorio)
            w, e = self._detalle_obra(detalle), detalle["edicion"]
            controles["detalle"] = w.get("key") == "/works/" + wid and e.get("key") == "/books/" + eid
            obras_edicion = [self._key(o) for o in self._lista(e.get("works"))]
            controles["relaciones"] &= obras_edicion == ["/works/" + wid]
            contradictorio |= not controles["detalle"] or not controles["relaciones"]
            autores_obra = [self._key(a.get("author")) for a in self._lista(w.get("authors")) if isinstance(a, dict)]
            controles["autores"] &= (set(autores_obra) == {"/authors/" + a for a in autor_ids}
                                       and len(autores_obra) == len(set(autores_obra)))
            if not controles["autores"]:
                alertas.append("autoria_no_coincide_con_obra")
                contradictorio = True
            idiomas = [self._key(i) for i in self._lista(e.get("languages"))]
            controles["idioma"] = "/languages/spa" in idiomas
            if idiomas and not controles["idioma"]:
                contradictorio = True
            if controles["idioma"] and set(idiomas) != {"/languages/spa"}:
                alertas.append("edicion_multilingue_revisar")
            i10, i13, isbn_alertas = self._isbn(e)
            alertas.extend(isbn_alertas)
            controles["isbn"] = bool(i10 or i13) or not self.EXIGIR_ISBN_PORTADA
            contradictorio |= bool(isbn_alertas) and not bool(i10 or i13)
            contradictorio |= self.RECHAZAR_ISBN_INVALIDOS and "isbn_invalidos_en_fuente" in isbn_alertas
            covers = [c for c in self._lista(e.get("covers")) if type(c) is int and c > 0]
            controles["portada"] = bool(covers) or not self.EXIGIR_ISBN_PORTADA
            # Un dato preparado no sustituye la evidencia de la edición original.
            for campo, largo, elegidos in (("isbn_10", 10, self._lista(e.get("isbn_10"))), ("isbn_13", 13, self._lista(e.get("isbn_13")))):
                if edicion.get(campo):
                    valor = normalizar_isbn(edicion[campo], largo)
                    validos = self._isbn_validos(elegidos, largo)[0]
                    if valor not in validos:
                        contradictorio = True
                        alertas.append("isbn_preparado_sin_respaldo")
            if edicion.get("portada_edicion_id") is not None and edicion["portada_edicion_id"] not in covers:
                contradictorio = True
                alertas.append("portada_preparada_sin_respaldo")
            titulo = texto_obligatorio(e.get("title"), "Título de edición")
            titulo_obra = texto_obligatorio(w.get("title"), "Título original")
            if len(titulo) <= 4:
                alertas.append("titulo_breve_revisar")
            if e.get("full_title") and self._nombre(e["full_title"]) != self._nombre(titulo):
                alertas.append("titulo_y_titulo_completo_difieren")
            if self._nombre(edicion.get("titulo")) != self._nombre(titulo):
                alertas.append("titulo_preparado_difiere_del_original")
            materias = datos.get("materias", [])
            originales = w.get("subjects", [])
            if not isinstance(materias, list) or not isinstance(originales, list):
                raise ErrorValidacion("Materias mal formadas.")
            materias = list(dict.fromkeys([*materias, *originales]))
            if any(not isinstance(m, str) or not m.strip() for m in materias):
                raise ErrorValidacion("Materia sin texto.")
            anio = obra.get("anio_primera_publicacion")
            portada_obra = obra.get("portada_obra_id")
            if type(anio) is not int or anio <= 0:
                anio = None
            if type(portada_obra) is not int or portada_obra <= 0:
                portada_obra = None
            fecha = e.get("publish_date")
            anio_edicion = int(fecha) if isinstance(fecha, str) and re.fullmatch(r"[1-9][0-9]{3}", fecha) else None
            editoriales = self._lista(e.get("publishers"))
            editorial = next((p.strip() for p in editoriales if isinstance(p, str) and p.strip()), None)
            paginas = e.get("number_of_pages")
            if type(paginas) is not int or paginas <= 0:
                paginas = None
            desc = w.get("description")
            if isinstance(desc, dict):
                desc = desc.get("value")
            desc = desc if isinstance(desc, str) else None
            autores_por_id = {a["id_openlibrary"]: a for a in autores}
            autores_ordenados = ([autores_por_id[key.removeprefix("/authors/")] for key in autores_obra]
                                 if controles["autores"] else autores)
            normalizados = {
                "obra": {"titulo_original": titulo_obra, "id_openlibrary": wid, "descripcion_original": desc,
                         "anio_primera_publicacion": anio, "portada_obra_id": portada_obra},
                "edicion": {"titulo": titulo, "id_openlibrary": eid, "idioma": "spa", "isbn_10": i10, "isbn_13": i13,
                            "editorial": editorial, "anio_publicacion": anio_edicion, "numero_paginas": paginas,
                            "portada_edicion_id": covers[0] if covers else None},
                "autores": autores_ordenados, "materias": materias,
            }
            # Reutilizar invariantes operativas; no guardar estas identidades de prueba.
            o = Obra(autor_ids=[uuid4() for _ in autores], **normalizados["obra"])
            Edicion(o.id, **normalizados["edicion"])
            controles["campos"] = True
        except (ErrorValidacion, KeyError, TypeError, AttributeError, ValueError):
            alertas.append("estructura_o_campos_invalidos")
            contradictorio = True
        return self._resultado(candidato, controles, alertas, normalizados, contradictorio)

    def _resultado(self, candidato, controles, alertas, normalizados, contradictorio):
        completa = all(controles.values()) and normalizados is not None
        estado = Estado.RECHAZADA if contradictorio else (
            Estado.VALIDADA if completa and not alertas else Estado.ENRIQUECIDA if completa else Estado.PENDIENTE)
        return EvaluacionOpenLibrary(candidato, self.VERSION, estado, controles, tuple(dict.fromkeys(alertas)), normalizados)

    def _detalle_obra(self, detalle):
        return detalle["obra"]

    @staticmethod
    def _id(valor, sufijo):
        id = id_openlibrary(valor, sufijo)
        if id is None:
            raise ErrorValidacion("Falta identidad OL.")
        return id

    @staticmethod
    def _key(valor):
        return valor.get("key") if isinstance(valor, dict) else None

    @staticmethod
    def _lista(valor):
        if valor is None:
            return []
        if not isinstance(valor, list):
            raise ErrorValidacion("Se requiere una lista en el detalle.")
        return valor

    @staticmethod
    def _nombre(valor):
        return " ".join(valor.split()).casefold() if isinstance(valor, str) else ""

    @staticmethod
    def _isbn_validos(valores, largo):
        validos, invalidos = [], False
        for valor in valores:
            try:
                isbn = normalizar_isbn(valor, largo)
                if isbn and isbn not in validos:
                    validos.append(isbn)
                invalidos |= isbn is None
            except ErrorValidacion:
                invalidos = True
        return validos, invalidos

    def _isbn(self, edicion):
        i13, malos13 = self._isbn_validos(self._lista(edicion.get("isbn_13")), 13)
        i10, malos10 = self._isbn_validos(self._lista(edicion.get("isbn_10")), 10)
        canonicos = set(i13) | {isbn13_desde_isbn10(i) for i in i10}
        alertas = []
        if malos13 or malos10:
            alertas.append("isbn_invalidos_en_fuente")
        if len(canonicos) > 1:
            alertas.append("isbn_multiples_revisar")
        elegido13 = i13[0] if i13 else None
        elegido10 = next((i for i in i10 if elegido13 is None or isbn13_desde_isbn10(i) == elegido13), None)
        return elegido10, elegido13, alertas
