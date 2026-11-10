"""Reglas bibliográficas. Los ISBN son ejemplos de cálculo, no atribuciones a títulos."""

from uuid import uuid4

import pytest

from biblioteca.dominio.autor import Autor
from biblioteca.dominio.bibliografia import isbn13_desde_isbn10, normalizar_isbn
from biblioteca.dominio.edicion import Edicion
from biblioteca.dominio.obra import Obra
from biblioteca.errores import ErrorValidacion


@pytest.mark.parametrize(("entrada", "longitud", "esperado"), [
    ("0-306-40615-2", 10, "0306406152"),
    ("0 8044 2957 x", 10, "080442957X"),
    ("978-0-306-40615-7", 13, "9780306406157"),
    ("9798890981615", 13, "9798890981615"),
    (None, 10, None), ("  ", 13, None),
])
def test_isbn_valida_formato_y_control_sin_perder_ceros(entrada, longitud, esperado):
    assert normalizar_isbn(entrada, longitud) == esperado


@pytest.mark.parametrize(("entrada", "longitud"), [
    ("0306406153", 10), ("9780306406158", 13), ("4006381333931", 13),
    ("ISBN 9780306406157", 13), ("abc0306406152", 10),
    ("978.0306406157", 13), ("-9780306406157", 13), ("9780306406157-", 13),
    ("X804429570", 10), ("08044295X7", 10), ("９７８０３０６４０６１５７", 13),
    (9780306406157, 13), (True, 10), ("1234", 10),
])
def test_isbn_invalido_no_se_arregla_eliminando_caracteres(entrada, longitud):
    with pytest.raises(ErrorValidacion):
        normalizar_isbn(entrada, longitud)


def test_edicion_admite_faltantes_y_no_contiene_estado_del_importador():
    edicion = Edicion(uuid4(), "  Título   español ")
    assert edicion.titulo == "Título español"
    assert edicion.isbn_10 is None and edicion.isbn_13 is None
    assert edicion.portada_edicion_id is None
    assert edicion.idioma == "spa"
    assert not hasattr(edicion, "estado_validacion")
    assert not hasattr(edicion, "idioma_verificado")


def test_isbn10_y_13_de_una_edicion_deben_corresponder():
    assert isbn13_desde_isbn10("0306406152") == "9780306406157"
    edicion = Edicion(uuid4(), "Título", isbn_10="0306406152", isbn_13="9780306406157")
    assert edicion.isbn_canonico == "9780306406157"
    with pytest.raises(ErrorValidacion, match="entre sí"):
        Edicion(uuid4(), "Título", isbn_10="0306406152", isbn_13="9788498382365")
    with pytest.raises(ErrorValidacion):
        Edicion(uuid4(), "Título", isbn_10="0306406152", isbn_13="9798890981615")


@pytest.mark.parametrize("idioma", ["eng", "es", "SPA", "", None, True])
def test_alcance_inicial_de_ediciones_es_espanol(idioma):
    with pytest.raises(ErrorValidacion):
        Edicion(uuid4(), "Título", idioma)


@pytest.mark.parametrize("campo", ["numero_paginas", "anio_publicacion", "portada_edicion_id"])
@pytest.mark.parametrize("valor", [True, 0, -1, 3.5, "20"])
def test_campos_numericos_no_admiten_booleanos_o_valores_invalidos(campo, valor):
    with pytest.raises(ErrorValidacion):
        Edicion(uuid4(), "Título", **{campo: valor})


@pytest.mark.parametrize(("crear", "valido", "invalido"), [
    (lambda id_ol: Autor("Nombre", id_openlibrary=id_ol), "OL12A", "OL12W"),
    (lambda id_ol: Obra("Obra", id_openlibrary=id_ol), "OL12W", "OL12M"),
    (lambda id_ol: Edicion(uuid4(), "Edición", id_openlibrary=id_ol), "OL12M", "/books/OL12M"),
])
def test_id_ol_se_valida_segun_tipo_sin_inventarlo(crear, valido, invalido):
    assert crear(None).id_openlibrary is None
    assert crear(valido).id_openlibrary == valido
    with pytest.raises(ErrorValidacion):
        crear(invalido)


def test_cambios_invalidos_de_edicion_no_dejan_cambios_parciales():
    edicion = Edicion(uuid4(), "Título original", editorial="Editorial", numero_paginas=200)
    with pytest.raises(ErrorValidacion):
        edicion.actualizar_datos("Título cambiado", editorial="Otra", numero_paginas=False)
    assert (edicion.titulo, edicion.editorial, edicion.numero_paginas) == ("Título original", "Editorial", 200)
    for campo in ("id", "obra_id", "id_openlibrary"):
        with pytest.raises(AttributeError):
            setattr(edicion, campo, uuid4())


def test_obra_conserva_autoria_sin_duplicar_y_protege_preferencia():
    a, b = uuid4(), uuid4()
    obra = Obra("A Wizard of Earthsea", [a, a])
    obra.vincular_autor(b)
    obra.vincular_autor(b)
    assert obra.autor_ids == (a, b)
    obra.desvincular_autor(a)
    with pytest.raises(ErrorValidacion):
        obra.desvincular_autor(b)
    preferida = Edicion(obra.id, "Un mago de Terramar")
    obra.seleccionar_edicion(preferida)
    with pytest.raises(ErrorValidacion):
        obra.seleccionar_edicion(Edicion(uuid4(), "Otra obra"))
    assert obra.edicion_preferida_id == preferida.id
    with pytest.raises(ErrorValidacion):
        obra.reemplazar_autores([a, "inválido"])
    assert obra.autor_ids == (b,)


def test_descripciones_conservan_parrafos_y_no_se_traducen():
    obra = Obra("Título", descripcion_original="First paragraph.\n\nSecond paragraph.")
    edicion = Edicion(obra.id, "Título español", descripcion_es="Primer párrafo.\n\nSegundo.")
    assert "\n\n" in obra.descripcion_original
    assert "\n\n" in edicion.descripcion_es
    assert Edicion(obra.id, "Otro título").descripcion_es is None


@pytest.mark.parametrize("crear", [lambda: Autor(" "), lambda: Obra(" "),
                                  lambda: Edicion(uuid4(), " ")])
def test_nombres_y_titulos_obligatorios(crear):
    with pytest.raises(ErrorValidacion):
        crear()
