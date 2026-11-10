"""La aceptación exige evidencia exacta, no el estado declarado en preparación."""

import pytest

from biblioteca.errores import ErrorValidacion
from biblioteca.importacion.modelos import CandidatoOpenLibrary, EstadoImportacion as Estado
from biblioteca.importacion.validador_openlibrary import ValidadorOpenLibrary


def evaluar(datos):
    return ValidadorOpenLibrary().evaluar(CandidatoOpenLibrary.desde_datos(datos))


def test_control_completo_acepta_sin_revision_individual(candidato_ol):
    resultado = ValidadorOpenLibrary().evaluar(candidato_ol)
    assert resultado.estado is Estado.VALIDADA
    assert resultado.politica == "OL-1"
    assert all(resultado.controles.values())
    assert resultado.puede_aprobar()
    assert resultado.normalizados["edicion"]["isbn_13"] == "9780306406157"


def test_instantanea_inmutable_huella_reproducible_y_datos_independientes(candidato_ol):
    datos = candidato_ol.datos
    datos["edicion"]["titulo"] = "Cambio"
    assert candidato_ol.datos["edicion"]["titulo"] != "Cambio"
    assert CandidatoOpenLibrary.desde_datos(candidato_ol.datos).huella == candidato_ol.huella
    assert CandidatoOpenLibrary.desde_datos(datos).huella != candidato_ol.huella
    with pytest.raises(ErrorValidacion):
        CandidatoOpenLibrary("[]")


@pytest.mark.parametrize("tipo,sufijo", [("obra", "M"), ("edicion", "W")])
def test_id_de_tipo_incorrecto_rechazado(candidato_ol, tipo, sufijo):
    datos = candidato_ol.datos
    datos[tipo]["id_openlibrary"] = "OL100" + sufijo
    r = evaluar(datos)
    assert r.estado is Estado.RECHAZADA
    assert not r.puede_aprobar()


@pytest.mark.parametrize("cambio", ["obra_preparada", "obra_detalle", "edicion_detalle", "relacion_detalle", "autoria"])
def test_contradicciones_de_identidad_y_relaciones_no_aprobables(candidato_ol, cambio):
    d = candidato_ol.datos
    if cambio == "obra_preparada":
        d["edicion"]["obra_id"] = "OL999W"
    elif cambio == "obra_detalle":
        d["detalle"]["obra"]["key"] = "/works/OL999W"
    elif cambio == "edicion_detalle":
        d["detalle"]["edicion"]["key"] = "/books/OL999M"
    elif cambio == "relacion_detalle":
        d["detalle"]["edicion"]["works"] = [{"key": "/works/OL999W"}]
    else:
        d["detalle"]["obra"]["authors"] = [{"author": {"key": "/authors/OL999A"}}]
    r = evaluar(d)
    assert r.estado is Estado.RECHAZADA
    assert not r.puede_aprobar()


def test_estado_preparado_no_sustituye_detalle_y_no_inventa_datos(candidato_ol):
    d = candidato_ol.datos
    d["edicion"]["estado_validacion"] = "VALIDADA"
    d["detalle"] = None
    r = evaluar(d)
    assert r.estado is Estado.PENDIENTE
    assert not r.controles["detalle"]
    assert not r.puede_aprobar()


@pytest.mark.parametrize("idiomas,estado", [([], Estado.PENDIENTE), ([{"key": "/languages/eng"}], Estado.RECHAZADA),
                                         ([{"key": "/languages/spa"}, {"key": "/languages/eng"}], Estado.ENRIQUECIDA)])
def test_idioma_se_contrasta_con_json_de_edicion(candidato_ol, idiomas, estado):
    d = candidato_ol.datos
    d["detalle"]["edicion"]["languages"] = idiomas
    assert evaluar(d).estado is estado


@pytest.mark.parametrize("valor", [True, -1, 0, "501"])
def test_portada_de_obra_no_suple_portada_de_edicion(candidato_ol, valor):
    d = candidato_ol.datos
    d["edicion"]["portada_edicion_id"] = None
    d["detalle"]["edicion"]["covers"] = [valor]
    r = evaluar(d)
    assert not r.controles["portada"]
    assert r.estado is Estado.PENDIENTE


@pytest.mark.parametrize("isbn", ["abc9780306406157", "9780306406158", 9780306406157, True])
def test_isbn_invalido_no_se_repara_quitando_letras(candidato_ol, isbn):
    d = candidato_ol.datos
    d["edicion"]["isbn_10"] = d["edicion"]["isbn_13"] = None
    d["detalle"]["edicion"]["isbn_10"] = []
    d["detalle"]["edicion"]["isbn_13"] = [isbn]
    r = evaluar(d)
    assert not r.controles["isbn"]
    assert r.estado is Estado.RECHAZADA


def test_solo_isbn10_valido_es_suficiente(candidato_ol):
    d = candidato_ol.datos
    d["edicion"]["isbn_13"] = None
    d["detalle"]["edicion"]["isbn_13"] = []
    assert evaluar(d).estado is Estado.VALIDADA


def test_varios_isbn_no_equivalentes_requieren_revision(candidato_ol):
    d = candidato_ol.datos
    d["detalle"]["edicion"]["isbn_13"].append("9788498382365")
    r = evaluar(d)
    assert r.estado is Estado.ENRIQUECIDA
    assert "isbn_multiples_revisar" in r.alertas


@pytest.mark.parametrize("campo,valor", [("portada_edicion_id", 999), ("isbn_13", "9788498382365")])
def test_dato_preparado_sin_respaldo_en_detalle_se_rechaza(candidato_ol, campo, valor):
    d = candidato_ol.datos
    d["edicion"][campo] = valor
    r = evaluar(d)
    assert r.estado is Estado.RECHAZADA
    assert not r.puede_aprobar()


@pytest.mark.parametrize("titulo,full", [("Mort", None), ("Meow", "Haunting Adeline Nunca te dejaré")])
def test_titulo_dudoso_se_senala_sin_inventar_correccion(candidato_ol, titulo, full):
    d = candidato_ol.datos
    d["detalle"]["edicion"]["title"] = titulo
    d["detalle"]["edicion"]["full_title"] = full
    r = evaluar(d)
    assert r.estado is Estado.ENRIQUECIDA
    assert r.puede_aprobar()
    assert r.normalizados["edicion"]["titulo"] == titulo


def test_colaboradores_de_edicion_no_se_mezclan_con_autoria(candidato_ol):
    d = candidato_ol.datos
    d["detalle"]["edicion"]["authors"] = [{"key": "/authors/OL999A"}]
    r = evaluar(d)
    assert r.estado is Estado.VALIDADA
    assert r.normalizados["autores"] == d["autores"]


def test_muchos_autores_es_alerta_y_no_se_eliminan_arbitrariamente(candidato_ol):
    d = candidato_ol.datos
    d["autores"] = [{"id_openlibrary": f"OL{n}A", "nombre": f"Autor {n}"} for n in range(6)]
    d["detalle"]["obra"]["authors"] = [{"author": {"key": "/authors/" + a["id_openlibrary"]}} for a in d["autores"]]
    r = evaluar(d)
    assert r.estado is Estado.ENRIQUECIDA
    assert "muchos_autores_revisar_creditos" in r.alertas
    assert len(r.normalizados["autores"]) == 6


def test_no_infiere_descripcion_es_o_anio_de_fecha_compleja(candidato_ol):
    d = candidato_ol.datos
    d["detalle"]["edicion"].update(description="The original description", publish_date="Nov 10, 2021",
                                    number_of_pages=True)
    r = evaluar(d)
    assert r.estado is Estado.VALIDADA
    assert r.normalizados["edicion"]["anio_publicacion"] is None
    assert r.normalizados["edicion"]["numero_paginas"] is None
    assert "descripcion_es" not in r.normalizados["edicion"]
    assert r.candidato.datos["detalle"]["edicion"]["description"] == "The original description"


@pytest.mark.parametrize("dato", [{}, {"edicion": None}, {"obra": [], "edicion": {"id_openlibrary": "OL9M"}}])
def test_estructura_malformada_produce_rechazo_auditable(dato):
    r = evaluar(dato)
    assert r.estado is Estado.RECHAZADA
    assert r.candidato.clave
