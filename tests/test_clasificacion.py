"""Clasificación explicable, revisiones preservadas y catálogo sin duplicados."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from biblioteca.dominio.clasificacion import (
    ClasificacionObra, DecisionClasificacion, EstadoClasificacion as Estado,
    Etiqueta, Genero, MetodoClasificacion as Metodo, PublicoDestinatario,
    TerminoClasificacion, TipoClasificacion as Tipo,
)
from biblioteca.errores import ErrorPersistencia, ErrorValidacion, RegistroDuplicado, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import conectar, transaccion
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.servicios.clasificacion_service import ClasificacionService
from biblioteca.servicios.reglas_clasificacion import ReglaClasificacion

FECHA = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


@pytest.fixture
def obra(catalogo):
    autor = catalogo.registrar_autor("Autora de prueba")
    obra = catalogo.registrar_obra("Original", [autor.id])
    catalogo.registrar_edicion(obra.id, "Título español")
    return obra


@pytest.fixture
def reglas(clasificaciones):
    return clasificaciones.preparar_reglas_iniciales()


@pytest.mark.parametrize("clase,tipo", [(Genero, Tipo.GENERO), (Etiqueta, Tipo.ETIQUETA), (PublicoDestinatario, Tipo.PUBLICO)])
def test_vocabularios_validan_nombre_y_no_permiten_cambiar_tipo(clase, tipo):
    termino = clase("  Nombre   válido  ")
    assert termino.nombre == "Nombre válido"
    assert termino.tipo is tipo
    with pytest.raises(FrozenInstanceError):
        termino.tipo = Tipo.ETIQUETA
    with pytest.raises(ErrorValidacion):
        clase(" ")
    with pytest.raises(ErrorValidacion):
        clase("Nombre", id="no-es-uuid")


def test_termino_base_no_es_otro_vocabulario():
    with pytest.raises(ErrorValidacion):
        TerminoClasificacion("Sin tipo")


@pytest.mark.parametrize("cambio", [
    {"estado": "APROBADO"}, {"metodo": "MANUAL"}, {"motivo": " "},
    {"fecha": datetime(2026, 11, 3)}, {"regla_id": "regla"},
    {"metodo": Metodo.AUTOMATICO},
    {"metodo": Metodo.AUTOMATICO, "regla_id": "r", "regla_version": "1", "estado": Estado.RECHAZADO},
])
def test_decisiones_invalidas_no_se_admiten(cambio):
    datos = dict(estado=Estado.PROPUESTO, metodo=Metodo.MANUAL, motivo="Motivo", fecha=FECHA)
    datos.update(cambio)
    with pytest.raises(ErrorValidacion):
        DecisionClasificacion(**datos)


def test_revision_invalida_es_atomica_y_fecha_se_normaliza():
    d = DecisionClasificacion(Estado.PROPUESTO, Metodo.MANUAL, "Propuesta", FECHA)
    c = ClasificacionObra(uuid4(), Genero("Fantasía"), d)
    with pytest.raises(ErrorValidacion):
        c.revisar(Estado.APROBADO, " ", FECHA)
    assert c.decision is d
    with pytest.raises(ErrorValidacion):
        c.revisar(Estado.PROPUESTO, "No resuelve", FECHA)
    c.revisar(Estado.APROBADO, "Bibliografía consultada", FECHA.astimezone(timezone(timedelta(hours=-3))))
    assert c.decision.fecha == FECHA
    assert c.decision.fecha.tzinfo is timezone.utc


def test_nombre_unico_dentro_del_tipo_no_entre_vocabularios(clasificaciones):
    g = clasificaciones.registrar_termino(Tipo.GENERO, "  Fantasía ")
    e = clasificaciones.registrar_termino(Tipo.ETIQUETA, "Fantasía")
    assert g.id != e.id
    with pytest.raises(RegistroDuplicado):
        clasificaciones.registrar_termino(Tipo.GENERO, "FANTASÍA")
    assert len(clasificaciones.listar_terminos(Tipo.GENERO)) == 1
    with pytest.raises(ErrorValidacion):
        clasificaciones.registrar_termino("GENERO", "Algo")


def test_reglas_iniciales_son_optativas_e_idempotentes(clasificaciones, conexion):
    assert conexion.execute("SELECT COUNT(*) FROM termino_clasificacion").fetchone()[0] == 0
    primera = clasificaciones.preparar_reglas_iniciales()
    assert primera == clasificaciones.preparar_reglas_iniciales()
    assert conexion.execute("SELECT COUNT(*) FROM termino_clasificacion").fetchone()[0] == 4
    assert conexion.execute("SELECT COUNT(*) FROM clasificacion_obra").fetchone()[0] == 0
    assert all(t.nombre != "Adulto" for t in clasificaciones.listar_terminos(Tipo.PUBLICO))


def test_correspondencias_exactas_aprueban_tres_conceptos_diferentes(obra, reglas, clasificaciones, catalogo):
    materias = ["Fantasy fiction", "Magic -- Fiction", "Children's fiction"]
    clasificaciones.procesar_materias(obra.id, materias, reglas, fecha=FECHA)
    resultado = clasificaciones.listar(obra.id)
    assert {c.termino.tipo for c in resultado} == set(Tipo)
    assert all(c.decision.estado is Estado.APROBADO and c.decision.metodo is Metodo.AUTOMATICO for c in resultado)
    assert catalogo.listar_obras(genero_id=reglas[0].termino_id)[0].id == obra.id
    assert catalogo.listar_obras(etiqueta_id=reglas[1].termino_id)[0].id == obra.id
    assert catalogo.listar_obras(publico_id=reglas[2].termino_id)[0].id == obra.id
    assert catalogo.listar_obras(genero_id=reglas[1].termino_id) == []


def test_originales_se_conservan_incluso_sin_correspondencia(obra, reglas, clasificaciones):
    textos = ["  FANTASY   FICTION  ", "Science fiction, fantasy, horror", "No fantasy fiction", "Materia desconocida"]
    clasificaciones.procesar_materias(obra.id, textos, reglas, fecha=FECHA)
    assert [m["texto"] for m in clasificaciones.materias(obra.id)] == textos
    assert len(clasificaciones.listar(obra.id)) == 1
    evidencia = clasificaciones.evidencias(obra.id, reglas[0].termino_id)[0]
    assert evidencia["texto"] == textos[0]
    assert evidencia["fuente"] == "Open Library"
    assert evidencia["regla_id"] == reglas[0].id
    assert evidencia["regla_version"] == "1"
    assert evidencia["motivo"]
    assert evidencia["fecha"] == FECHA.isoformat()
    assert "Materia desconocida" in evidencia["contexto"]


@pytest.mark.parametrize("contexto", ["History and criticism", "Literary criticism", "Crítica literaria", "Study and teaching", "Adaptations"])
def test_contexto_dudoso_mantiene_propuesta_y_no_aparece_en_filtro(obra, reglas, clasificaciones, catalogo, contexto):
    clasificaciones.procesar_materias(obra.id, ["Fantasy fiction", contexto], reglas, fecha=FECHA)
    assert clasificaciones.obtener(obra.id, reglas[0].termino_id).decision.estado is Estado.PROPUESTO
    assert catalogo.listar_obras(genero_id=reglas[0].termino_id) == []


def test_contexto_guardado_en_lote_previo_tambien_bloquea(obra, reglas, clasificaciones):
    clasificaciones.procesar_materias(obra.id, ["History and criticism"], [], fecha=FECHA)
    clasificaciones.procesar_materias(obra.id, ["Fantasy fiction"], reglas, fecha=FECHA)
    assert clasificaciones.obtener(obra.id, reglas[0].termino_id).decision.estado is Estado.PROPUESTO


def test_contexto_nuevo_devuelve_aprobacion_automatica_a_revision(obra, reglas, clasificaciones, catalogo):
    r = reglas[0]
    clasificaciones.procesar_materias(obra.id, [r.materia], reglas, fecha=FECHA)
    clasificaciones.procesar_materias(obra.id, ["History and criticism"], reglas,
                                     fecha=FECHA + timedelta(days=1))
    assert clasificaciones.obtener(obra.id, r.termino_id).decision.estado is Estado.PROPUESTO
    assert catalogo.listar_obras(genero_id=r.termino_id) == []
    assert [d.estado for d in clasificaciones.historial(obra.id, r.termino_id)] == [Estado.APROBADO, Estado.PROPUESTO]
    assert len(clasificaciones.evidencias(obra.id, r.termino_id)) == 2


def test_contexto_nuevo_respeta_aprobacion_humana(obra, reglas, clasificaciones):
    r = reglas[0]
    clasificaciones.procesar_materias(obra.id, [r.materia], reglas, fecha=FECHA)
    clasificaciones.revisar(obra.id, r.termino_id, Estado.APROBADO, "Verificada", fecha=FECHA)
    clasificaciones.procesar_materias(obra.id, ["History and criticism"], reglas)
    assert clasificaciones.obtener(obra.id, r.termino_id).decision.metodo is Metodo.MANUAL
    assert clasificaciones.evidencias(obra.id, r.termino_id)[-1]["resultado"] == "PROPUESTO"


def test_misma_materia_de_dos_fuentes_conserva_ambas_evidencias(obra, reglas, clasificaciones):
    for fuente in ("Open Library", "Revisión de catálogo"):
        clasificaciones.procesar_materias(obra.id, ["Fantasy fiction"], reglas, fuente=fuente, fecha=FECHA)
    assert len(clasificaciones.materias(obra.id)) == 2
    assert {e["fuente"] for e in clasificaciones.evidencias(obra.id, reglas[0].termino_id)} == {"Open Library", "Revisión de catálogo"}
    assert len(clasificaciones.historial(obra.id, reglas[0].termino_id)) == 1


def test_clasificacion_no_modifica_datos_bibliograficos_ni_inventario(obra, reglas, clasificaciones, inventario, sedes, conexion):
    sede = sedes.registrar("Centro", "Dirección", "Contacto", "9 a 18")
    edicion_id = conexion.execute("SELECT id FROM edicion WHERE obra_id = ?", (str(obra.id),)).fetchone()[0]
    inventario.registrar("HZ-PRUEBA", edicion_id, sede.id)
    tablas = ("autor", "obra", "obra_autor", "edicion", "sede", "ejemplar")
    antes = {t: [tuple(f) for f in conexion.execute(f"SELECT * FROM {t} ORDER BY 1")] for t in tablas}
    clasificaciones.procesar_materias(obra.id, [r.materia for r in reglas], reglas)
    assert {t: [tuple(f) for f in conexion.execute(f"SELECT * FROM {t} ORDER BY 1")] for t in tablas} == antes


def test_candidato_explicito_puede_exigir_revision_manual(obra, reglas, clasificaciones, catalogo):
    r = ReglaClasificacion("fantasia-dudosa", "1", "Fantasy", reglas[0].termino_id, False)
    clasificaciones.procesar_materias(obra.id, ["Fantasy"], [r], fecha=FECHA)
    assert clasificaciones.obtener(obra.id, r.termino_id).decision.estado is Estado.PROPUESTO
    clasificaciones.revisar(obra.id, r.termino_id, Estado.APROBADO, "Verificada en la edición", fecha=FECHA)
    assert len(catalogo.listar_obras(genero_id=r.termino_id)) == 1
    assert [d.estado for d in clasificaciones.historial(obra.id, r.termino_id)] == [Estado.PROPUESTO, Estado.APROBADO]


@pytest.mark.parametrize("estado", [Estado.RECHAZADO, Estado.APROBADO])
def test_decision_humana_prevalece_al_reprocesar_y_cambiar_version(obra, reglas, clasificaciones, catalogo, estado):
    r = reglas[0]
    clasificaciones.procesar_materias(obra.id, ["Fantasy fiction"], [r], fecha=FECHA)
    revision = clasificaciones.revisar(obra.id, r.termino_id, estado, "Revisión humana", fecha=FECHA)
    nueva = ReglaClasificacion(r.id, "2", r.materia, r.termino_id)
    clasificaciones.procesar_materias(obra.id, [r.materia], [nueva], fecha=FECHA + timedelta(days=1))
    assert clasificaciones.obtener(obra.id, r.termino_id).decision == revision.decision
    assert len(clasificaciones.historial(obra.id, r.termino_id)) == 2
    assert len(clasificaciones.evidencias(obra.id, r.termino_id)) == 2
    assert len(catalogo.listar_obras(genero_id=r.termino_id)) == (1 if estado is Estado.APROBADO else 0)


def test_repeticion_no_duplica_materias_evidencias_ni_decisiones(obra, reglas, clasificaciones, conexion):
    for dia in range(3):
        clasificaciones.procesar_materias(obra.id, ["Fantasy fiction", "Fantasy fiction"], reglas,
                                         fecha=FECHA + timedelta(days=dia))
    for tabla in ("materia_original", "evidencia_clasificacion", "clasificacion_obra", "decision_clasificacion"):
        assert conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == 1
    assert clasificaciones.historial(obra.id, reglas[0].termino_id)[0].fecha == FECHA


def test_dos_evidencias_una_relacion_y_aprobacion_no_se_pierde_por_candidata(obra, reglas, clasificaciones):
    r = reglas[0]
    candidata = ReglaClasificacion("otra", "1", "Fantasy", r.termino_id, False)
    clasificaciones.procesar_materias(obra.id, [r.materia, candidata.materia], [r, candidata], fecha=FECHA)
    assert len(clasificaciones.listar(obra.id)) == 1
    assert clasificaciones.obtener(obra.id, r.termino_id).decision.estado is Estado.APROBADO
    assert len(clasificaciones.evidencias(obra.id, r.termino_id)) == 2


def test_version_de_regla_es_inmutable_y_fallo_revierte_todo(obra, reglas, clasificaciones, conexion):
    r = reglas[0]
    modificada = ReglaClasificacion(r.id, r.version, "Otro texto", r.termino_id)
    with pytest.raises(ErrorValidacion, match="versión"):
        clasificaciones.procesar_materias(obra.id, ["Otro texto"], [modificada])
    assert clasificaciones.materias(obra.id) == []
    assert conexion.execute("SELECT COUNT(*) FROM clasificacion_obra").fetchone()[0] == 0


def test_nueva_version_puede_aprobar_propuesta_automatica(obra, reglas, clasificaciones):
    r = ReglaClasificacion("candidata", "1", "Fantasy", reglas[0].termino_id, False)
    clasificaciones.procesar_materias(obra.id, ["Fantasy"], [r], fecha=FECHA)
    r2 = ReglaClasificacion(r.id, "2", r.materia, r.termino_id, True)
    clasificaciones.procesar_materias(obra.id, ["Fantasy"], [r2], fecha=FECHA)
    assert [d.estado for d in clasificaciones.historial(obra.id, r.termino_id)] == [Estado.PROPUESTO, Estado.APROBADO]


def test_propuesta_manual_y_revision_rechazo_conservan_historial(obra, reglas, clasificaciones):
    r = reglas[0]
    propuesta = clasificaciones.proponer(obra.id, r.termino_id, "Sugerencia", fecha=FECHA)
    assert propuesta.decision.estado is Estado.PROPUESTO
    clasificaciones.revisar(obra.id, r.termino_id, Estado.RECHAZADO, "No corresponde", fecha=FECHA)
    assert clasificaciones.proponer(obra.id, r.termino_id, "Otra sugerencia").decision.estado is Estado.RECHAZADO
    assert len(clasificaciones.historial(obra.id, r.termino_id)) == 2
    assert len(clasificaciones.listar(obra.id, estado=Estado.RECHAZADO)) == 1


@pytest.mark.parametrize("materias", ["Fantasy fiction", [None], [" "], [123]])
def test_lote_invalido_no_guarda_nada(obra, reglas, clasificaciones, materias):
    with pytest.raises(ErrorValidacion):
        clasificaciones.procesar_materias(obra.id, materias, reglas)
    assert clasificaciones.materias(obra.id) == []


def test_referencias_inexistentes_no_dejan_datos(obra, reglas, clasificaciones):
    with pytest.raises(RegistroNoEncontrado):
        clasificaciones.procesar_materias(uuid4(), ["Fantasy fiction"], reglas)
    with pytest.raises(RegistroNoEncontrado):
        clasificaciones.procesar_materias(obra.id, ["Fantasy fiction"], [ReglaClasificacion("x", "1", "Fantasy fiction", uuid4())])
    assert clasificaciones.materias(obra.id) == []
    with pytest.raises(RegistroNoEncontrado):
        clasificaciones.revisar(obra.id, reglas[0].termino_id, Estado.APROBADO, "Sin propuesta")


def test_fallo_evidencia_revierte_asociacion_materia_e_historia(obra, reglas, clasificaciones, clasificacion_repository, monkeypatch, conexion):
    def fallar(*args):
        raise ErrorPersistencia("Fallo de escritura simulado")
    monkeypatch.setattr(clasificacion_repository, "registrar_evidencia", fallar)
    with pytest.raises(ErrorPersistencia):
        clasificaciones.procesar_materias(obra.id, ["Fantasy fiction"], reglas)
    for tabla in ("materia_original", "evidencia_clasificacion", "decision_clasificacion", "clasificacion_obra"):
        assert conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] == 0


def test_repositorio_no_confirma_y_reapertura_conserva_revision(obra, reglas, clasificaciones, clasificacion_repository, conexion, ruta_db):
    clasificaciones.proponer(obra.id, reglas[0].termino_id, "Candidata", fecha=FECHA)
    c = clasificaciones.obtener(obra.id, reglas[0].termino_id)
    with pytest.raises(RuntimeError):
        with transaccion(conexion):
            c.revisar(Estado.RECHAZADO, "Debe revertirse", FECHA)
            clasificacion_repository.guardar(c, nueva=False)
            raise RuntimeError()
    assert clasificaciones.obtener(obra.id, reglas[0].termino_id).decision.estado is Estado.PROPUESTO
    otra = conectar(ruta_db)
    try:
        assert ClasificacionRepository(otra).obtener(obra.id, reglas[0].termino_id).decision.estado is Estado.PROPUESTO
    finally:
        otra.close()


def test_repositorios_de_distinta_conexion_se_rechazan(clasificacion_repository, obra_repository, ruta_db):
    otra = conectar(ruta_db)
    try:
        with pytest.raises(ErrorValidacion):
            ClasificacionService(ClasificacionRepository(otra), obra_repository)
    finally:
        otra.close()


def test_filtros_combinados_y_paginacion_no_duplican_obras(catalogo, reglas, clasificaciones):
    autores = [catalogo.registrar_autor(n) for n in ("Autor uno", "Autora dos")]
    ids = []
    for n in range(4):
        o = catalogo.registrar_obra(f"Original {n}", [a.id for a in autores])
        catalogo.registrar_edicion(o.id, f"Libro {n}")
        catalogo.registrar_edicion(o.id, f"Traducción {n}")
        clasificaciones.procesar_materias(o.id, [r.materia for r in reglas], reglas, fecha=FECHA)
        ids.append(o.id)
    filtros = dict(genero_id=reglas[0].termino_id, etiqueta_id=reglas[1].termino_id, publico_id=reglas[2].termino_id)
    assert [f.id for f in catalogo.listar_obras(**filtros, titulo="Traducción", autor="dos")] == ids
    assert [catalogo.listar_obras(**filtros, limite=1, desplazamiento=n)[0].id for n in range(4)] == ids
    assert catalogo.listar_obras(**filtros, limite=1, desplazamiento=4) == []


def test_auditoria_paginada_y_limites(obra, reglas, clasificaciones):
    clasificaciones.procesar_materias(obra.id, [r.materia for r in reglas], reglas, fecha=FECHA)
    todas = clasificaciones.listar(obra.id)
    assert len(todas) == 4
    assert [clasificaciones.listar(obra.id, limite=1, desplazamiento=n)[0].termino.id for n in range(4)] == [c.termino.id for c in todas]
    assert len(clasificaciones.materias(obra.id, limite=1, desplazamiento=3)) == 1
    for consulta in (lambda: clasificaciones.listar(obra.id, limite=101),
                     lambda: clasificaciones.materias(obra.id, desplazamiento=-1),
                     lambda: clasificaciones.evidencias(obra.id, reglas[0].termino_id, limite=True),
                     lambda: clasificaciones.historial(obra.id, reglas[0].termino_id, limite=0)):
        with pytest.raises(ErrorValidacion):
            consulta()
