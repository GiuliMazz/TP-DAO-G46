"""Recorridos integrados: aceptación, catálogo, clasificación e inventario."""

from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

import pytest

from biblioteca.dominio.clasificacion import EstadoClasificacion
from biblioteca.errores import ErrorPersistencia, ErrorValidacion, PosibleDuplicado, RegistroNoEncontrado
from biblioteca.importacion.modelos import CandidatoOpenLibrary, EstadoImportacion as Estado
from biblioteca.importacion.validador_openlibrary import ValidadorOpenLibrary
from biblioteca.persistencia.base_datos import conectar
from biblioteca.repositorios.importacion_repository import ImportacionRepository
from biblioteca.servicios.importacion_service import ImportacionService
from biblioteca.servicios.procesador_materias import ProcesadorMaterias

FECHA = datetime(2026, 11, 3, 15, tzinfo=timezone.utc)


def modificar(candidato, **campos):
    datos = candidato.datos
    for campo, valor in campos.items():
        datos[campo] = valor
    return CandidatoOpenLibrary.desde_datos(datos)


def test_aceptacion_e_integracion_con_clasificacion_sin_copias(importacion, candidato_ol, clasificaciones, catalogo, inventario, conexion):
    reglas = clasificaciones.preparar_reglas_iniciales()
    r = importacion.evaluar(candidato_ol, fecha=FECHA)
    assert r.estado is Estado.VALIDADA and r.metodo == "AUTOMATICO"
    assert r.edicion_local_id is None
    edicion = importacion.integrar(r.edicion_ol, reglas, fecha=FECHA)
    detalle = catalogo.obtener_detalle(edicion.obra_id)
    assert detalle.titulo_mostrado == "Edición española de prueba"
    assert detalle.obra.id_openlibrary == "OL100W"
    assert detalle.autores[0].id_openlibrary == "OL100A"
    assert catalogo.listar_obras(genero_id=reglas[0].termino_id)[0].id == detalle.obra.id
    assert len(clasificaciones.materias(detalle.obra.id)) == 2
    assert inventario.listar(obra_id=detalle.obra.id) == []
    assert conexion.execute("SELECT COUNT(*) FROM ejemplar").fetchone()[0] == 0
    assert importacion.resumen()["obras_integradas"] == 1


def test_repetir_evaluacion_e_integracion_conserva_identidades_y_auditoria(importacion, candidato_ol, clasificaciones, conexion):
    reglas = clasificaciones.preparar_reglas_iniciales()
    ids = []
    for dia in range(3):
        registro = importacion.evaluar(candidato_ol, fecha=FECHA + timedelta(days=dia))
        edicion = importacion.integrar(registro.edicion_ol, reglas, fecha=FECHA + timedelta(days=dia))
        ids.append((edicion.id, edicion.obra_id))
    assert len(set(ids)) == 1
    assert len(importacion.evaluaciones(candidato_ol.clave)) == 1
    assert len(importacion.historial(candidato_ol.clave)) == 1
    for tabla in ("autor", "obra", "edicion"):
        assert conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == 1
    assert conexion.execute("SELECT COUNT(*) FROM evidencia_clasificacion").fetchone()[0] == 2


def test_importado_se_puede_usar_en_inventario_y_sede_inactiva_cambia_disponibilidad(importacion, candidato_ol, sedes, inventario):
    importacion.evaluar(candidato_ol)
    edicion = importacion.integrar(candidato_ol.clave)
    sede = sedes.registrar("Centro", "Dirección", "Contacto", "9 a 18")
    copia = inventario.registrar("HZ-IMPORTADO", edicion.id, sede.id)
    assert inventario.consultar_disponibilidad(edicion.obra_id)[0].disponibles == 1
    sedes.dar_de_baja(sede.id)
    assert inventario.consultar_disponibilidad(edicion.obra_id)[0].disponibles == 0
    assert inventario.obtener(copia.id).edicion_id == edicion.id


def test_reimportacion_conserva_correcciones_autoria_preferencia_y_copias(importacion, candidato_ol, catalogo, sedes, inventario):
    importacion.evaluar(candidato_ol)
    edicion = importacion.integrar(candidato_ol.clave)
    autor = catalogo.obtener_detalle(edicion.obra_id).autores[0]
    catalogo.modificar_autor(autor.id, "Nombre corregido manualmente")
    catalogo.modificar_obra(edicion.obra_id, "Obra corregida manualmente", [autor.id])
    catalogo.modificar_edicion(edicion.id, "Título corregido manualmente", descripcion_es="Sinopsis revisada")
    otra = catalogo.registrar_edicion(edicion.obra_id, "Otra edición local")
    catalogo.seleccionar_edicion_preferida(edicion.obra_id, otra.id)
    sede = sedes.registrar("Centro", "Dirección", "Contacto", "9 a 18")
    copia = inventario.registrar("HZ-CONSERVAR", edicion.id, sede.id)
    d = candidato_ol.datos
    d["detalle"]["obra"]["description"] = "Nueva fuente"
    importacion.evaluar(CandidatoOpenLibrary.desde_datos(d))
    importacion.integrar(candidato_ol.clave)
    detalle = catalogo.obtener_detalle(edicion.obra_id)
    assert detalle.obra.titulo_original == "Obra corregida manualmente"
    assert detalle.autores[0].nombre == "Nombre corregido manualmente"
    assert detalle.obra.edicion_preferida_id == otra.id
    assert catalogo.obtener_edicion(edicion.id).titulo == "Título corregido manualmente"
    assert catalogo.obtener_edicion(edicion.id).descripcion_es == "Sinopsis revisada"
    assert inventario.obtener(copia.id).edicion_id == edicion.id


def test_dos_ediciones_importadas_comparten_obra_sin_cambiar_preferencia(importacion, candidato_ol, catalogo, conexion):
    importacion.evaluar(candidato_ol)
    primera = importacion.integrar(candidato_ol.clave)
    d = candidato_ol.datos
    d["edicion"].update(id_openlibrary="OL101M", isbn_10=None, isbn_13="9788498382365")
    d["detalle"]["edicion"].update(key="/books/OL101M", isbn_10=[], isbn_13=["9788498382365"])
    c2 = CandidatoOpenLibrary.desde_datos(d)
    importacion.evaluar(c2)
    segunda = importacion.integrar(c2.clave)
    assert segunda.obra_id == primera.obra_id
    assert segunda.id != primera.id
    assert catalogo.obtener_obra(primera.obra_id).edicion_preferida_id == primera.id
    assert conexion.execute("SELECT COUNT(*) FROM obra").fetchone()[0] == 1


def test_rechazo_humano_persiste_ante_nueva_fuente_y_politica(importacion, candidato_ol, importacion_repository,
                                                            obra_repository, edicion_repository, autor_repository, clasificacion_repository):
    importacion.evaluar(candidato_ol)
    revision = importacion.revisar(candidato_ol.clave, Estado.RECHAZADA, "Autoría bibliográfica requiere revisión", fecha=FECHA)
    class OtraPolitica(ValidadorOpenLibrary):
        VERSION = "OL-test-2"
    servicio = ImportacionService(importacion_repository, obra_repository, edicion_repository, autor_repository,
                                   clasificacion_repository, validador=OtraPolitica())
    r = servicio.evaluar(modificar(candidato_ol, materias=["Otro tema"]))
    assert r.estado is Estado.RECHAZADA and r.metodo == "MANUAL"
    assert r.decision_id == revision.decision_id
    assert r.tiene_cambios_sin_revisar
    assert len(servicio.evaluaciones(r.edicion_ol)) == 2
    assert len(servicio.historial(r.edicion_ol)) == 2
    with pytest.raises(ErrorValidacion):
        servicio.integrar(r.edicion_ol)


def test_aprobacion_humana_no_se_extiende_a_una_instantanea_nueva(importacion, candidato_ol, catalogo, importacion_repository):
    importacion.evaluar(candidato_ol)
    aceptada = importacion.revisar(candidato_ol.clave, Estado.VALIDADA, "Revisada", titulo_edicion="Edición revisada")
    d = candidato_ol.datos
    d["detalle"]["edicion"]["title"] = "Título nuevo de la fuente"
    nueva = importacion.evaluar(CandidatoOpenLibrary.desde_datos(d))
    assert nueva.decision_id == aceptada.decision_id
    assert nueva.tiene_cambios_sin_revisar
    edicion = importacion.integrar(candidato_ol.clave)
    assert catalogo.obtener_edicion(edicion.id).titulo == "Edición revisada"
    original = importacion_repository.obtener_evaluacion(nueva.ultima_evaluacion_id)
    assert original.candidato.datos["detalle"]["edicion"]["title"] == "Título nuevo de la fuente"


def test_revision_puede_aceptar_alerta_con_correccion_explicita(importacion, candidato_ol, catalogo):
    d = candidato_ol.datos
    d["detalle"]["edicion"].update(title="Meow", full_title="Título español completo")
    c = CandidatoOpenLibrary.desde_datos(d)
    assert importacion.evaluar(c).estado is Estado.ENRIQUECIDA
    importacion.revisar(c.clave, Estado.VALIDADA, "Contraste bibliográfico documentado en prueba", titulo_edicion="Título español completo")
    edicion = importacion.integrar(c.clave)
    assert edicion.titulo == "Título español completo"
    assert json.loads(importacion.historial(c.clave)[-1]["correcciones_json"]) == {"titulo_edicion": "Título español completo"}


@pytest.mark.parametrize("tipo", ["incompleta", "contradictoria"])
def test_revision_humana_no_omite_controles_tecnicos(importacion, candidato_ol, tipo):
    d = candidato_ol.datos
    if tipo == "incompleta":
        d["detalle"] = None
    else:
        d["edicion"]["portada_edicion_id"] = 999
    c = CandidatoOpenLibrary.desde_datos(d)
    importacion.evaluar(c)
    with pytest.raises(ErrorValidacion, match="controles técnicos"):
        importacion.revisar(c.clave, Estado.VALIDADA, "No puede saltarse")
    assert len(importacion.historial(c.clave)) == 1


def test_fallo_de_clasificacion_revierte_todo_el_alta_pero_no_auditoria(importacion, candidato_ol, clasificaciones, clasificacion_repository, conexion, monkeypatch):
    reglas = clasificaciones.preparar_reglas_iniciales()
    importacion.evaluar(candidato_ol)
    def fallo(*args):
        raise ErrorPersistencia("Fallo simulado de evidencia")
    monkeypatch.setattr(clasificacion_repository, "registrar_evidencia", fallo)
    with pytest.raises(ErrorPersistencia):
        importacion.integrar(candidato_ol.clave, reglas)
    for tabla in ("autor", "obra", "edicion", "obra_autor", "materia_original", "clasificacion_obra", "decision_clasificacion"):
        assert conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == 0
    assert importacion.obtener(candidato_ol.clave).edicion_local_id is None
    assert len(importacion.historial(candidato_ol.clave)) == 1


def test_reimportacion_preserva_rechazo_humano_de_genero(importacion, candidato_ol, clasificaciones, catalogo):
    reglas = clasificaciones.preparar_reglas_iniciales()
    importacion.evaluar(candidato_ol)
    edicion = importacion.integrar(candidato_ol.clave, reglas)
    clasificaciones.revisar(edicion.obra_id, reglas[0].termino_id, EstadoClasificacion.RECHAZADO, "Revisión humana")
    importacion.integrar(candidato_ol.clave, reglas)
    assert catalogo.listar_obras(genero_id=reglas[0].termino_id) == []
    assert len(clasificaciones.historial(edicion.obra_id, reglas[0].termino_id)) == 2


def test_no_promueve_clasificacion_exploratoria_ni_confunde_ciencia_con_ficcion(importacion, candidato_ol, clasificaciones, catalogo):
    d = candidato_ol.datos
    d["materias"] = ["Science fiction, fantasy, horror", "Science", "Whales"]
    d["detalle"]["obra"]["subjects"] = d["materias"]
    d["generos_provisorios"] = ["Fantasía", "Ciencias", "Ciencia ficción"]
    reglas = clasificaciones.preparar_reglas_iniciales()
    c = CandidatoOpenLibrary.desde_datos(d)
    importacion.evaluar(c)
    edicion = importacion.integrar(c.clave, reglas)
    assert clasificaciones.listar(edicion.obra_id) == []
    assert len(clasificaciones.materias(edicion.obra_id)) == 3
    assert catalogo.listar_obras(genero_id=reglas[0].termino_id) == []


def test_isbn_coincidente_exige_revision_y_no_deja_autores_huerfanos(importacion, candidato_ol, catalogo, conexion):
    a = catalogo.registrar_autor("Autor de otra obra")
    o = catalogo.registrar_obra("Otra obra", [a.id])
    catalogo.registrar_edicion(o.id, "Otra edición", isbn_13="9780306406157")
    importacion.evaluar(candidato_ol)
    with pytest.raises(PosibleDuplicado):
        importacion.integrar(candidato_ol.clave)
    assert conexion.execute("SELECT COUNT(*) FROM autor").fetchone()[0] == 1
    assert conexion.execute("SELECT COUNT(*) FROM obra").fetchone()[0] == 1
    nueva = importacion.integrar(candidato_ol.clave, confirmar_distinta=True)
    assert nueva.obra_id != o.id


def test_titulo_autor_coincidente_no_se_fusiona_automaticamente(importacion, candidato_ol, catalogo):
    autor = catalogo.registrar_autor("Autora de prueba", id_openlibrary="OL100A")
    catalogo.registrar_obra("Original de prueba", [autor.id])
    importacion.evaluar(candidato_ol)
    with pytest.raises(PosibleDuplicado):
        importacion.integrar(candidato_ol.clave)


def test_edicion_no_se_reasigna_a_otra_obra(importacion, candidato_ol, catalogo):
    a = catalogo.registrar_autor("Autor")
    o = catalogo.registrar_obra("Obra distinta", [a.id])
    catalogo.registrar_edicion(o.id, "Edición registrada", id_openlibrary="OL100M")
    importacion.evaluar(candidato_ol)
    with pytest.raises(ErrorValidacion, match="reasignar"):
        importacion.integrar(candidato_ol.clave, confirmar_distinta=True)


def test_rechazar_fuente_posteriormente_no_borra_catalogo_o_copias(importacion, candidato_ol, sedes, inventario, catalogo):
    importacion.evaluar(candidato_ol)
    e = importacion.integrar(candidato_ol.clave)
    s = sedes.registrar("Centro", "Dirección", "Contacto", "9 a 18")
    copia = inventario.registrar("HZ-HISTORIA", e.id, s.id)
    importacion.revisar(candidato_ol.clave, Estado.RECHAZADA, "Revisión de la fuente posterior al alta")
    assert catalogo.obtener_edicion(e.id).id == e.id
    assert inventario.obtener(copia.id).id == copia.id
    with pytest.raises(ErrorValidacion):
        importacion.integrar(candidato_ol.clave)


def test_evaluaciones_y_revision_persisten_al_reabrir(importacion, candidato_ol, ruta_db):
    importacion.evaluar(candidato_ol, fecha=FECHA)
    r = importacion.revisar(candidato_ol.clave, Estado.RECHAZADA, "Revisada", fecha=FECHA)
    otra = conectar(ruta_db)
    try:
        recuperada = ImportacionRepository(otra).obtener(candidato_ol.clave)
        assert recuperada.decision_id == r.decision_id
        assert recuperada.estado is Estado.RECHAZADA and recuperada.metodo == "MANUAL"
    finally:
        otra.close()


def test_consultas_y_estados_se_validan_y_se_paginan(importacion, candidato_ol):
    importacion.evaluar(candidato_ol)
    d = candidato_ol.datos
    d["edicion"]["id_openlibrary"] = "OL101M"
    d["detalle"] = None
    importacion.evaluar(CandidatoOpenLibrary.desde_datos(d))
    assert len(importacion.listar(estado=Estado.VALIDADA)) == 1
    assert importacion.listar(limite=1, desplazamiento=1)[0].edicion_ol == "OL101M"
    for consulta in (lambda: importacion.listar(estado="VALIDADA"), lambda: importacion.listar(limite=101),
                     lambda: importacion.historial(candidato_ol.clave, desplazamiento=-1),
                     lambda: importacion.evaluaciones(candidato_ol.clave, limite=True),
                     lambda: importacion.evaluar(candidato_ol, fecha=datetime(2026, 11, 3)),
                     lambda: importacion.integrar(candidato_ol.clave, confirmar_distinta=1)):
        with pytest.raises(ErrorValidacion):
            consulta()
    with pytest.raises(RegistroNoEncontrado):
        importacion.obtener("OL999M")


def test_no_permite_repositorios_de_conexiones_distintas(importacion_repository, obra_repository, edicion_repository,
                                                      autor_repository, clasificacion_repository, ruta_db):
    otra = conectar(ruta_db)
    try:
        with pytest.raises(ErrorValidacion):
            ImportacionService(ImportacionRepository(otra), obra_repository, edicion_repository, autor_repository, clasificacion_repository)
    finally:
        otra.close()


def test_procesador_de_materias_exige_transaccion(clasificacion_repository, obra_repository):
    with pytest.raises(ErrorPersistencia):
        ProcesadorMaterias(clasificacion_repository, obra_repository).procesar(uuid4(), [], [])


def test_evidencia_permite_comparar_fuente_nueva_con_decision_humana(importacion, candidato_ol):
    importacion.evaluar(candidato_ol)
    importacion.revisar(candidato_ol.clave, Estado.VALIDADA, "Revisada")
    importacion.evaluar(modificar(candidato_ol, materias=["Otro tema"]))
    assert importacion.evidencia(candidato_ol.clave).candidato.datos["materias"] == ["Otro tema"]
    assert importacion.evidencia(candidato_ol.clave, de_decision=True).candidato.datos["materias"] == candidato_ol.datos["materias"]


def test_cambiar_politica_sin_version_no_reinterpreta_evidencia(importacion, candidato_ol, monkeypatch):
    from dataclasses import replace
    original = importacion.evaluar(candidato_ol)
    evaluar = ValidadorOpenLibrary.evaluar
    def otra_evaluacion(self, candidata):
        return replace(evaluar(self, candidata), estado=Estado.RECHAZADA)
    monkeypatch.setattr(ValidadorOpenLibrary, "evaluar", otra_evaluacion)
    with pytest.raises(ErrorValidacion, match="versión nueva"):
        importacion.evaluar(candidato_ol)
    assert importacion.obtener(candidato_ol.clave).decision_id == original.decision_id
    assert len(importacion.evaluaciones(candidato_ol.clave)) == 1
