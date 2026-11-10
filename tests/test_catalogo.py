"""Casos de catálogo con datos sintéticos, sin afirmar metadatos reales de ediciones."""

from contextlib import closing
from uuid import UUID, uuid4

import pytest

from biblioteca.dominio.autor import Autor
from biblioteca.dominio.edicion import Edicion
from biblioteca.dominio.obra import Obra
from biblioteca.errores import (
    ErrorPersistencia, ErrorValidacion, PosibleDuplicado, RegistroDuplicado, RegistroNoEncontrado,
)
from biblioteca.persistencia.base_datos import conectar, transaccion
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.servicios.catalogo_service import CatalogoService


@pytest.fixture
def terramar(catalogo):
    autor = catalogo.registrar_autor("Ursula K. Le Guin")
    obra = catalogo.registrar_obra("A Wizard of Earthsea", [autor.id])
    primera = catalogo.registrar_edicion(obra.id, "Un mago de Terramar")
    segunda = catalogo.registrar_edicion(obra.id, "Historias de Terramar 1: el mago")
    return obra, autor, primera, segunda


def test_busca_titulo_original_y_todas_las_ediciones_espanolas(catalogo, terramar):
    obra, autor, primera, _ = terramar
    for consulta in ("Mago de Terramar", "Wizard", "HISTORIAS DE TERRAMAR"):
        fichas = catalogo.listar_obras(titulo=consulta)
        assert len(fichas) == 1
        assert fichas[0].id == obra.id
        assert fichas[0].titulo_mostrado == "Un mago de Terramar"
        assert fichas[0].titulo_original == "A Wizard of Earthsea"
        assert fichas[0].edicion_preferida_id == primera.id
        assert fichas[0].autores == (autor.nombre,)
        assert fichas[0].cantidad_ediciones == 2


def test_seleccion_y_edicion_del_titulo_preferido_se_reflejan_en_catalogo(catalogo, terramar):
    obra, _, primera, segunda = terramar
    catalogo.seleccionar_edicion_preferida(obra.id, segunda.id)
    assert catalogo.obtener_detalle(obra.id).titulo_mostrado == segunda.titulo
    assert catalogo.listar_obras(titulo=primera.titulo)[0].titulo_mostrado == segunda.titulo
    catalogo.modificar_edicion(segunda.id, "Título español corregido")
    assert catalogo.listar_obras(titulo="corregido")[0].titulo_mostrado == "Título español corregido"
    assert catalogo.listar_obras(titulo="Historias") == []


def test_titulo_original_como_respaldo_y_borrador_fuera_del_listado(catalogo):
    autor = catalogo.registrar_autor("Autor")
    obra = catalogo.registrar_obra("Título original", [autor.id])
    detalle = catalogo.obtener_detalle(obra.id)
    assert detalle.titulo_mostrado == "Título original"
    assert detalle.edicion_preferida is None
    assert detalle.cantidad_ediciones == 0
    assert catalogo.listar_obras() == []
    catalogo.registrar_edicion(obra.id, "Título español")
    assert catalogo.listar_obras()[0].titulo_mostrado == "Título español"


def test_no_puede_seleccionarse_edicion_de_otra_obra(catalogo, terramar):
    obra, autor, primera, _ = terramar
    otra = catalogo.registrar_obra("Otra obra", [autor.id])
    edicion = catalogo.registrar_edicion(otra.id, "Otra edición")
    with pytest.raises(ErrorValidacion):
        catalogo.seleccionar_edicion_preferida(obra.id, edicion.id)
    assert catalogo.obtener_obra(obra.id).edicion_preferida_id == primera.id


def test_base_tambien_impide_preferida_de_otra_obra(conexion, catalogo, terramar):
    obra, autor, primera, _ = terramar
    otra = catalogo.registrar_obra("Otra obra", [autor.id])
    edicion = catalogo.registrar_edicion(otra.id, "Otra edición")
    with pytest.raises(ErrorPersistencia):
        with transaccion(conexion):
            conexion.execute("UPDATE obra SET edicion_preferida_id = ? WHERE id = ?",
                             (str(edicion.id), str(obra.id)))
    assert catalogo.obtener_obra(obra.id).edicion_preferida_id == primera.id


def test_autores_homonimos_y_titulos_homonimos_son_identidades_distintas(catalogo):
    a = catalogo.registrar_autor("Alex")
    b = catalogo.registrar_autor("Alex")
    x = catalogo.registrar_obra("El libro", [a.id])
    y = catalogo.registrar_obra("El libro", [b.id])
    catalogo.registrar_edicion(x.id, "El libro")
    catalogo.registrar_edicion(y.id, "El libro")
    assert a.id != b.id and x.id != y.id
    assert len(catalogo.listar_obras(autor="alex")) == 2


def test_coincidencia_de_titulo_y_autoria_exige_revision_sin_fusionar(catalogo):
    a = catalogo.registrar_autor("Autor A")
    b = catalogo.registrar_autor("Autor B")
    original = catalogo.registrar_obra("El libro", [a.id, b.id])
    with pytest.raises(PosibleDuplicado):
        catalogo.registrar_obra(" EL   LIBRO ", [b.id, a.id])
    distinta = catalogo.registrar_obra("El libro", [a.id, b.id], confirmar_distinta=True)
    assert distinta.id != original.id
    assert catalogo.obtener_obra(original.id).autor_ids == (a.id, b.id)
    assert catalogo.modificar_obra(original.id, "El libro", [a.id, b.id],
                                   confirmar_distinta=True).id == original.id


def test_isbn_equivalentes_son_posible_duplicado_no_identidad_de_obra(catalogo):
    autor = catalogo.registrar_autor("Autor")
    obra = catalogo.registrar_obra("Obra", [autor.id])
    primera = catalogo.registrar_edicion(obra.id, "Primera", isbn_10="0306406152")
    with pytest.raises(PosibleDuplicado):
        catalogo.registrar_edicion(obra.id, "Segunda", isbn_13="9780306406157")
    segunda = catalogo.registrar_edicion(obra.id, "Segunda", isbn_13="9780306406157",
                                        confirmar_distinta=True)
    assert primera.id != segunda.id
    assert catalogo.obtener_detalle(obra.id).cantidad_ediciones == 2
    # La propia edición no entra en sus coincidencias al corregirla.
    catalogo.modificar_edicion(segunda.id, "Segunda corregida", isbn_13="9780306406157",
                               confirmar_distinta=True)


def test_fuente_ol_siempre_es_unica_aunque_se_confirme_distinta(catalogo):
    autor = catalogo.registrar_autor("Autor", id_openlibrary="OL10A")
    with pytest.raises(RegistroDuplicado):
        catalogo.registrar_autor("Otro nombre", id_openlibrary="OL10A")
    obra = catalogo.registrar_obra("Obra", [autor.id], id_openlibrary="OL20W")
    with pytest.raises(RegistroDuplicado):
        catalogo.registrar_obra("Otra obra", [autor.id], id_openlibrary="OL20W",
                                confirmar_distinta=True)
    catalogo.registrar_edicion(obra.id, "Edición", id_openlibrary="OL30M")
    with pytest.raises(RegistroDuplicado):
        catalogo.registrar_edicion(obra.id, "Otra edición", id_openlibrary="OL30M",
                                   confirmar_distinta=True)


def test_registro_y_modificacion_no_inventan_autores_o_relaciones(catalogo):
    with pytest.raises(ErrorValidacion):
        catalogo.registrar_obra("Obra", [])
    with pytest.raises(RegistroNoEncontrado):
        catalogo.registrar_obra("Obra", [uuid4()])
    autor = catalogo.registrar_autor("Autor")
    obra = catalogo.registrar_obra("Obra", [autor.id, autor.id])
    with pytest.raises(RegistroNoEncontrado):
        catalogo.modificar_obra(obra.id, "No debe quedar", [uuid4()])
    assert catalogo.obtener_obra(obra.id).titulo_original == "Obra"
    assert catalogo.obtener_obra(obra.id).autor_ids == (autor.id,)
    with pytest.raises(RegistroNoEncontrado):
        catalogo.registrar_edicion(uuid4(), "No existe la obra")


def test_alta_conjunta_es_atomica_y_no_modifica_objetos_del_llamador(catalogo):
    autor = catalogo.registrar_autor("Autor")
    obra = Obra("Original", [autor.id])
    edicion = Edicion(obra.id, "Español", editorial="Editorial", numero_paginas=200)
    detalle = catalogo.registrar_libro(obra, edicion)
    assert detalle.obra.id == obra.id
    assert detalle.edicion_preferida.id == edicion.id
    assert obra.edicion_preferida_id is None
    assert detalle.titulo_mostrado == "Español"
    assert detalle.edicion_preferida.isbn_13 is None


def test_fallo_despues_de_insertar_edicion_revierte_obra_y_relaciones(
    catalogo, edicion_repository, conexion, monkeypatch
):
    autor = catalogo.registrar_autor("Autor")
    obra = Obra("Original", [autor.id])
    edicion = Edicion(obra.id, "Español")
    agregar = edicion_repository.agregar

    def fallar(dato):
        agregar(dato)
        raise ErrorPersistencia("Fallo simulado después de insertar edición")

    with monkeypatch.context() as parche:
        parche.setattr(edicion_repository, "agregar", fallar)
        with pytest.raises(ErrorPersistencia):
            catalogo.registrar_libro(obra, edicion)
    for tabla in ("obra", "edicion", "obra_autor"):
        assert conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == 0
    assert catalogo.obtener_autor(autor.id).id == autor.id
    assert obra.edicion_preferida_id is None
    assert catalogo.registrar_libro(obra, edicion).obra.id == obra.id


def test_lectura_tras_reabrir_preserva_titulos_isbn_fuente_y_preferencia(catalogo, ruta_db):
    autor = catalogo.registrar_autor("Autor", id_openlibrary="OL10A")
    obra = catalogo.registrar_obra("Original", [autor.id], id_openlibrary="OL20W",
                                  descripcion_original="Original description", anio_primera_publicacion=1900)
    edicion = catalogo.registrar_edicion(obra.id, "Español", id_openlibrary="OL30M",
                                        isbn_10="0306406152", isbn_13="9780306406157",
                                        anio_publicacion=2000, numero_paginas=200,
                                        portada_edicion_id=45, descripcion_es="Sinopsis de prueba")
    with closing(conectar(ruta_db)) as conexion:
        servicio = CatalogoService(ObraRepository(conexion), EdicionRepository(conexion),
                                    AutorRepository(conexion))
        detalle = servicio.obtener_detalle(obra.id)
        assert detalle.obra.id_openlibrary == "OL20W"
        assert detalle.obra.anio_primera_publicacion == 1900
        assert detalle.autores[0].id == autor.id
        assert detalle.edicion_preferida.id == edicion.id
        assert detalle.edicion_preferida.isbn_10 == "0306406152"
        assert detalle.edicion_preferida.isbn_13 == "9780306406157"
        assert detalle.edicion_preferida.portada_edicion_id == 45
        assert detalle.edicion_preferida.anio_publicacion == 2000
        assert servicio.listar_obras(titulo="español")[0].id == obra.id


def test_filtros_de_titulo_y_autor_no_multiplican_filas(catalogo, terramar):
    obra, _, _, _ = terramar
    otro = catalogo.registrar_autor("Coautor de prueba")
    actual = catalogo.obtener_obra(obra.id)
    catalogo.modificar_obra(obra.id, actual.titulo_original, [*actual.autor_ids, otro.id])
    assert len(catalogo.listar_obras(titulo="Terramar", autor="prueba")) == 1
    assert len(catalogo.listar_obras()) == 1
    assert catalogo.listar_obras(titulo="Terramar", autor="inexistente") == []
    assert len(catalogo.listar_obras()[0].autores) == 2
    catalogo.modificar_autor(otro.id, "Nombre corregido")
    assert catalogo.listar_obras(autor="corregido")[0].id == obra.id


def test_orden_y_paginacion_por_titulo_mostrado_con_desempate(catalogo):
    autor = catalogo.registrar_autor("Autor")
    ids = []
    for original, espanol in [("A original", "Zeta"), ("Z original", "Alfa"), ("B original", "Alfa")]:
        obra = catalogo.registrar_obra(original, [autor.id])
        catalogo.registrar_edicion(obra.id, espanol)
        ids.append(obra.id)
    fichas = [catalogo.listar_obras(limite=1, desplazamiento=i)[0] for i in range(3)]
    assert [f.id for f in fichas] == sorted(ids[1:], key=str) + [ids[0]]
    assert catalogo.listar_obras(desplazamiento=10) == []
    for i in range(3):
        ediciones = catalogo.listar_ediciones(ids[i], limite=1)
        assert len(ediciones) == 1
        assert catalogo.listar_ediciones(ids[i], limite=1, desplazamiento=1) == []


def test_consulta_de_pagina_no_hace_una_consulta_de_autores_por_obra(conexion, catalogo):
    autor = catalogo.registrar_autor("Autor")
    for i in range(4):
        obra = catalogo.registrar_obra(f"Original {i}", [autor.id])
        catalogo.registrar_edicion(obra.id, f"Español {i}")
    consultas = []
    conexion.set_trace_callback(consultas.append)
    try:
        assert len(catalogo.listar_obras(limite=3)) == 3
    finally:
        conexion.set_trace_callback(None)
    assert len([sql for sql in consultas if sql.lstrip().upper().startswith(("SELECT", "WITH"))]) == 2


@pytest.mark.parametrize("parametros", [dict(limite=0), dict(limite=101), dict(limite=True),
                                        dict(desplazamiento=-1), dict(titulo=123), dict(autor=False)])
def test_busqueda_rechaza_parametros_invalidos(catalogo, parametros):
    with pytest.raises(ErrorValidacion):
        catalogo.listar_obras(**parametros)


def test_busqueda_es_literal_y_parametrizada(catalogo, terramar):
    assert catalogo.listar_obras(titulo="%") == []
    assert catalogo.listar_obras(autor="' OR 1=1 --") == []
    assert len(catalogo.listar_obras()) == 1


def test_repositorios_no_borran_ni_confirman_al_fallar(conexion, obra_repository, autor_repository):
    autor = Autor("Autor")
    with transaccion(conexion):
        autor_repository.agregar(autor)
    obra = Obra("Obra", [uuid4()])
    with pytest.raises(ErrorPersistencia):
        with transaccion(conexion):
            obra_repository.agregar(obra)
    assert obra_repository.obtener(obra.id) is None


def test_constructor_del_servicio_exige_una_sola_conexion(conexion):
    with closing(conectar(":memory:")) as otra:
        with pytest.raises(ErrorValidacion, match="misma conexión"):
            CatalogoService(ObraRepository(conexion), EdicionRepository(otra), AutorRepository(conexion))


def test_faltantes_y_confirmaciones_no_validas_se_comunican(catalogo):
    for obtener in (catalogo.obtener_autor, catalogo.obtener_obra, catalogo.obtener_edicion):
        with pytest.raises(RegistroNoEncontrado):
            obtener(uuid4())
        with pytest.raises(ErrorValidacion):
            obtener("inválido")
    autor = catalogo.registrar_autor("Autor")
    with pytest.raises(ErrorValidacion):
        catalogo.registrar_obra("Obra", [autor.id], confirmar_distinta="sí")


def test_fuente_y_obras_sin_edicion_no_cuentan_como_inventario(conexion, catalogo, terramar):
    tablas = {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert conexion.execute("SELECT COUNT(*) FROM ejemplar").fetchone()[0] == 0
    assert "remito" not in tablas
    assert "prestamo" not in tablas
    assert "estado_validacion" not in {
        fila[1] for fila in conexion.execute("PRAGMA table_info(edicion)")
    }


@pytest.mark.parametrize("filtros", [{}, dict(titulo="Original"), dict(titulo="Español"),
                                     dict(autor="prueba")])
def test_paginas_con_varios_autores_y_ediciones_no_repiten_obras(catalogo, filtros):
    a = catalogo.registrar_autor("Autor de prueba")
    b = catalogo.registrar_autor("Coautor de prueba")
    esperados = []
    for i in range(3):
        obra = catalogo.registrar_obra(f"Original {i}", [a.id, b.id])
        catalogo.registrar_edicion(obra.id, f"Español {i}")
        catalogo.registrar_edicion(obra.id, f"Español alternativo {i}")
        esperados.append(obra.id)
    paginas = [catalogo.listar_obras(limite=1, desplazamiento=i, **filtros) for i in range(4)]
    assert [[f.id for f in pagina] for pagina in paginas] == [[id] for id in esperados] + [[]]
