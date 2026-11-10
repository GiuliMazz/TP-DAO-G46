"""Política local, insumos verificables y dos bases independientes reproducibles."""

from contextlib import closing
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from biblioteca.dominio.ejemplar import CondicionFisica
from biblioteca.errores import ErrorValidacion
from biblioteca.importacion.fuente_catalogo_local import FuenteCatalogoLocal
from biblioteca.importacion.modelos import CandidatoOpenLibrary, EstadoImportacion
from biblioteca.importacion.validador_catalogo_local import ValidadorCatalogoLocal
from biblioteca.importacion.validador_openlibrary import ValidadorOpenLibrary
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.importacion_repository import ImportacionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.importacion_service import ImportacionService
from biblioteca.servicios.inventario_service import InventarioService
from herramientas.preparar_catalogo_local import exportar_catalogo, preparar


def _guardar(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return sha256(ruta.read_bytes()).hexdigest()


def _servicio_importacion(conexion):
    return ImportacionService(ImportacionRepository(conexion), ObraRepository(conexion),
        EdicionRepository(conexion), AutorRepository(conexion), ClasificacionRepository(conexion),
        validador=ValidadorCatalogoLocal())


@pytest.fixture
def seleccion(tmp_path, candidato_ol):
    raiz = tmp_path / "insumos"
    b, e, w, registros = {}, {}, {}, []
    for i in (100, 101):
        wid, eid = f"OL{i}W", f"OL{i}M"
        b[wid] = {"datos": {"key": "/works/" + wid, "title": f"Original {i}",
            "author_key": ["OL100A"], "author_name": ["Autora de prueba"],
            "subject": ["Fantasy fiction"]}, "url": "https://openlibrary.org/search.json?q=prueba"}
        edicion = deepcopy(candidato_ol.datos["detalle"]["edicion"])
        edicion.update(key="/books/" + eid, works=[{"key": "/works/" + wid}], title=f"Español {i}")
        for campo in ("isbn_10", "isbn_13", "covers"):
            edicion.pop(campo, None)
        e[eid] = {"datos": edicion, "url": f"https://openlibrary.org/books/{eid}.json"}
        registros.append({"obra_id": wid, "edicion_id": eid})
    fuentes = {f"fuentes/{nombre}.json": _guardar(raiz / f"fuentes/{nombre}.json", datos)
               for nombre, datos in (("busquedas", b), ("ediciones", e), ("obras", w))}
    ruta = raiz / "seleccion.json"
    _guardar(ruta, {"version": 1, "politica": "OL-2-LOCAL", "registros": registros,
                    "fuentes": fuentes, "portadas": []})
    return ruta


@pytest.mark.parametrize("faltantes", [("isbn_10", "isbn_13"), ("covers",), ("isbn_10", "isbn_13", "covers")])
def test_local_permite_ausencias_sin_cambiar_ol1(candidato_ol, faltantes):
    datos = candidato_ol.datos
    for campo in faltantes:
        datos["detalle"]["edicion"].pop(campo, None)
        datos["edicion"].pop("portada_edicion_id" if campo == "covers" else campo, None)
    candidato = CandidatoOpenLibrary.desde_datos(datos)
    assert ValidadorOpenLibrary().evaluar(candidato).estado is EstadoImportacion.PENDIENTE
    local = ValidadorCatalogoLocal().evaluar(candidato)
    assert local.estado is EstadoImportacion.VALIDADA and local.puede_aprobar()
    assert local.politica == "OL-2-LOCAL"
    if "covers" in faltantes:
        assert local.normalizados["edicion"]["portada_edicion_id"] is None
    if "isbn_13" in faltantes:
        assert local.normalizados["edicion"]["isbn_13"] is None


@pytest.mark.parametrize("valor", ["9780306406158", "ISBN INVÁLIDO"])
def test_isbn_invalido_no_se_convierte_en_ausente(candidato_ol, valor):
    datos = candidato_ol.datos
    datos["detalle"]["edicion"]["isbn_13"].append(valor)
    evaluacion = ValidadorCatalogoLocal().evaluar(CandidatoOpenLibrary.desde_datos(datos))
    assert evaluacion.estado is EstadoImportacion.RECHAZADA
    assert "isbn_invalidos_en_fuente" in evaluacion.alertas
    assert not evaluacion.puede_aprobar()


@pytest.mark.parametrize("cambio", ["idioma", "relacion", "autor", "titulo", "detalle"])
def test_politica_local_no_omite_controles_ni_alertas(candidato_ol, cambio):
    datos = candidato_ol.datos
    if cambio == "idioma": datos["detalle"]["edicion"]["languages"] = [{"key": "/languages/eng"}]
    if cambio == "relacion": datos["detalle"]["edicion"]["works"] = [{"key": "/works/OL999W"}]
    if cambio == "autor": datos["detalle"]["obra"]["authors"] = []
    if cambio == "titulo": datos["detalle"]["edicion"]["full_title"] = "Otro título"
    if cambio == "detalle": datos["detalle"] = None
    resultado = ValidadorCatalogoLocal().evaluar(CandidatoOpenLibrary.desde_datos(datos))
    assert resultado.estado is not EstadoImportacion.VALIDADA
    if cambio != "titulo": assert not resultado.puede_aprobar()


def test_search_es_evidencia_explicita_y_no_fabrica_detalle_obra(seleccion):
    fuente = FuenteCatalogoLocal(seleccion)
    candidato = next(fuente.iterar())
    assert "obra" not in candidato.datos["detalle"]
    assert "busqueda" in candidato.datos["detalle"]
    evaluacion = ValidadorCatalogoLocal().evaluar(candidato)
    assert evaluacion.estado is EstadoImportacion.VALIDADA
    assert evaluacion.normalizados["obra"]["descripcion_original"] is None
    datos = candidato.datos
    datos["autores"][0]["nombre"] = "Nombre inventado"
    assert ValidadorCatalogoLocal().evaluar(CandidatoOpenLibrary.desde_datos(datos)).estado is EstadoImportacion.RECHAZADA


def test_autores_homonimos_de_search_quedan_para_revision(seleccion):
    datos = next(FuenteCatalogoLocal(seleccion).iterar()).datos
    datos["detalle"]["busqueda"]["author_key"].append("OL999A")
    datos["detalle"]["busqueda"]["author_name"].append("Autora de prueba")
    datos["autores"].append({"id_openlibrary": "OL999A", "nombre": "Autora de prueba"})
    evaluacion = ValidadorCatalogoLocal().evaluar(CandidatoOpenLibrary.desde_datos(datos))
    assert evaluacion.estado is EstadoImportacion.ENRIQUECIDA
    assert "autores_con_mismo_nombre_revisar" in evaluacion.alertas


def test_integracion_local_versiona_evidencia_y_conserva_correcciones(importacion, conexion, candidato_ol):
    importacion.evaluar(candidato_ol)
    local = _servicio_importacion(conexion)
    local.evaluar(candidato_ol)
    edicion = local.integrar(candidato_ol.clave)
    catalogo = CatalogoService(ObraRepository(conexion), EdicionRepository(conexion), AutorRepository(conexion))
    catalogo.modificar_edicion(edicion.id, "Título corregido manualmente")
    local.evaluar(candidato_ol)
    assert local.integrar(candidato_ol.clave).id == edicion.id
    assert catalogo.obtener_edicion(edicion.id).titulo == "Título corregido manualmente"
    politicas = {f[0] for f in conexion.execute("SELECT politica FROM evaluacion_importacion")}
    assert politicas == {"OL-1", "OL-2-LOCAL"}


def test_no_se_aprueba_manualmente_un_isbn_invalido(conexion, candidato_ol):
    datos = candidato_ol.datos
    datos["detalle"]["edicion"]["isbn_13"] = ["9780306406158"]
    candidato = CandidatoOpenLibrary.desde_datos(datos)
    servicio = _servicio_importacion(conexion)
    servicio.evaluar(candidato)
    with pytest.raises(ErrorValidacion):
        servicio.revisar(candidato.clave, EstadoImportacion.VALIDADA, "No debe omitir el control")


@pytest.mark.parametrize("cambio", ["fuente", "duplicado", "ruta", "politica", "portada"])
def test_insumos_invalidos_no_abren_destinos(seleccion, tmp_path, cambio):
    datos = json.loads(seleccion.read_text())
    if cambio == "fuente": (seleccion.parent / "fuentes/ediciones.json").write_text("{}")
    if cambio == "duplicado": datos["registros"].append(datos["registros"][0])
    if cambio == "ruta": datos["fuentes"]["../../fuera.json"] = "sin-huella"
    if cambio == "politica": datos["politica"] = "OL-1"
    if cambio == "portada": datos["portadas"] = [{"id": 123, "archivo": "portadas/123.jpg", "sha256": "x"}]
    _guardar(seleccion, datos)
    operativa, demo = tmp_path / "operativa.db", tmp_path / "demo.db"
    with pytest.raises(ErrorValidacion): preparar(seleccion, operativa, demo)
    assert not operativa.exists() and not demo.exists()


def test_bases_reproducibles_independientes_y_150_copias_sin_red(seleccion, tmp_path, monkeypatch):
    def sin_red(*a, **kw): raise AssertionError("La reproducción debe ser offline")
    monkeypatch.setattr("urllib.request.urlopen", sin_red)
    operativa, demo = tmp_path / "operativa.db", tmp_path / "demo.db"
    resultado = preparar(seleccion, operativa, demo)
    for tipo in ("OPERATIVA", "DEMOSTRACION"):
        assert resultado["bases"][tipo]["obra"] == resultado["bases"][tipo]["edicion"] == 2
    assert resultado["bases"]["OPERATIVA"]["ejemplar"] == 0
    assert resultado["bases"]["OPERATIVA"]["sede"] == 0
    assert resultado["bases"]["DEMOSTRACION"]["ejemplar"] == 150
    assert resultado["bases"]["DEMOSTRACION"]["ejemplares_por_sede_propietaria"] == {"Centro": 50, "Norte": 50, "Sur": 50}
    with closing(conectar(demo)) as c:
        antes = {f["codigo_inventario"]: f["id"] for f in c.execute("SELECT id, codigo_inventario FROM ejemplar")}
        inventario = InventarioService(EjemplarRepository(c), EdicionRepository(c), SedeRepository(c), ObraRepository(c))
        ejemplar = inventario.buscar_por_codigo("DEMO-0001")
        inventario.registrar_condicion(ejemplar.id, CondicionFisica.DANIADO)
        inventario.dar_de_baja(ejemplar.id)
        autor_id = c.execute("SELECT id FROM autor LIMIT 1").fetchone()[0]
        c.execute("UPDATE autor SET nombre = 'Corrección humana', nombre_normalizado = 'corrección humana' WHERE id = ?", (autor_id,))
        c.commit()
    # Reordenar el manifiesto no altera el plan estable de inventario.
    datos = json.loads(seleccion.read_text()); datos["registros"].reverse(); _guardar(seleccion, datos)
    repetido = preparar(seleccion, operativa, demo)
    assert repetido["bases"]["DEMOSTRACION"]["ejemplar"] == 150
    with closing(conectar(demo)) as c:
        assert {f["codigo_inventario"]: f["id"] for f in c.execute("SELECT id, codigo_inventario FROM ejemplar")} == antes
        assert EjemplarRepository(c).obtener(ejemplar.id).condicion_fisica is CondicionFisica.DANIADO
        assert c.execute("SELECT nombre FROM autor WHERE id = ?", (autor_id,)).fetchone()[0] == "Corrección humana"


def test_destino_sin_marcador_o_tipos_invertidos_no_es_modificado(seleccion, tmp_path):
    operativa, demo = tmp_path / "operativa.db", tmp_path / "demo.db"
    with closing(conectar(operativa)) as c: migrar(c)
    huella = sha256(operativa.read_bytes()).hexdigest()
    with pytest.raises(ErrorValidacion, match="existente"):
        preparar(seleccion, operativa, demo)
    assert sha256(operativa.read_bytes()).hexdigest() == huella and not demo.exists()


def test_no_se_invierten_tipos_de_bases(seleccion, tmp_path):
    op, demo = tmp_path / "op.db", tmp_path / "demo.db"
    preparar(seleccion, op, demo)
    antes = (sha256(op.read_bytes()).hexdigest(), sha256(demo.read_bytes()).hexdigest())
    with pytest.raises(ErrorValidacion, match="tipo"):
        preparar(seleccion, demo, op)
    assert antes == (sha256(op.read_bytes()).hexdigest(), sha256(demo.read_bytes()).hexdigest())


@pytest.mark.parametrize("vinculo", ["misma_ruta", "enlace"])
def test_no_se_usan_alias_del_mismo_archivo(seleccion, tmp_path, vinculo):
    op = tmp_path / "op.db"
    demo = op
    if vinculo == "enlace":
        op.touch(); demo = tmp_path / "demo.db"; os.link(op, demo)
    with pytest.raises(ErrorValidacion, match="independientes"):
        preparar(seleccion, op, demo)


def test_error_de_codigo_existente_no_reemplaza_la_copia(seleccion, tmp_path):
    op, demo = tmp_path / "op.db", tmp_path / "demo.db"
    preparar(seleccion, op, demo)
    with closing(conectar(demo)) as c:
        propietario = c.execute("SELECT sede_propietaria_id FROM ejemplar WHERE codigo_inventario='DEMO-0001'").fetchone()[0]
        otra = c.execute("SELECT id FROM sede WHERE id != ? LIMIT 1", (propietario,)).fetchone()[0]
        c.execute("UPDATE ejemplar SET sede_propietaria_id = ? WHERE codigo_inventario='DEMO-0001'", (otra,)); c.commit()
    with pytest.raises(ErrorValidacion, match="no se sobrescribe"):
        preparar(seleccion, op, demo)
    with closing(conectar(demo)) as c:
        assert c.execute("SELECT sede_propietaria_id FROM ejemplar WHERE codigo_inventario='DEMO-0001'").fetchone()[0] == otra


def test_sede_renombrada_e_inactiva_no_se_recrea_ni_reactiva(seleccion, tmp_path):
    op, demo = tmp_path / "op.db", tmp_path / "demo.db"
    preparar(seleccion, op, demo)
    with closing(conectar(demo)) as c:
        c.execute("UPDATE sede SET nombre='Centro renombrada', nombre_normalizado='centro renombrada', activa=0 WHERE nombre='Centro'")
        c.commit()
    preparar(seleccion, op, demo)
    with closing(conectar(demo)) as c:
        assert c.execute("SELECT COUNT(*) FROM sede").fetchone()[0] == 3
        assert c.execute("SELECT activa FROM sede WHERE nombre='Centro renombrada'").fetchone()[0] == 0


def test_rechazo_manual_no_es_sustituido_al_repetir_preparacion(seleccion, tmp_path):
    op, demo = tmp_path / "op.db", tmp_path / "demo.db"
    preparar(seleccion, op, demo)
    with closing(conectar(op)) as c:
        servicio = _servicio_importacion(c)
        decision = servicio.revisar("OL100M", EstadoImportacion.RECHAZADA, "Revisión humana posterior")
    resultado = preparar(seleccion, op, demo)
    assert len(resultado["bases"]["OPERATIVA"]["decisiones_manuales_conservadas_sin_integrar"]) == 1
    with closing(conectar(op)) as c:
        actual = _servicio_importacion(c).obtener("OL100M")
        assert actual.decision_id == decision.decision_id
        assert actual.estado is EstadoImportacion.RECHAZADA and actual.metodo == "MANUAL"
        # Rechazar la reimportación no borra la edición que ya estaba en catálogo.
        assert c.execute("SELECT COUNT(*) FROM edicion").fetchone()[0] == 2


def test_csv_auditable_conserva_identidades_links_y_ausencias(seleccion, tmp_path):
    import csv
    ruta = tmp_path / "catalogo.csv"
    exportar_catalogo(FuenteCatalogoLocal(seleccion), ruta)
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    assert len(filas) == 2
    assert filas[0]["edicion_ol"] == "OL100M"
    assert filas[0]["isbn_13"] == filas[0]["portada_local"] == ""
    assert filas[0]["url_edicion"] == "https://openlibrary.org/books/OL100M"


def test_paquete_real_incluido_es_verificable_y_no_depende_de_la_red():
    ruta = Path(__file__).resolve().parents[1] / "datos/catalogo_local/seleccion.json"
    fuente = FuenteCatalogoLocal(ruta)
    assert len(fuente.candidatos) == 100
    assert len({c.datos["obra"]["id_openlibrary"] for c in fuente.candidatos}) == 100
    assert len({c.clave for c in fuente.candidatos}) == 100
    evaluaciones = [ValidadorCatalogoLocal().evaluar(c) for c in fuente.candidatos]
    assert all(e.estado is EstadoImportacion.VALIDADA for e in evaluaciones)
    assert any(e.normalizados["edicion"]["isbn_13"] is None for e in evaluaciones)
    assert any(e.normalizados["edicion"]["portada_edicion_id"] is None for e in evaluaciones)
    assert all(p.read_bytes().startswith(b"\xff\xd8") for p in fuente.portadas.values())
