"""Regresiones con los archivos disponibles y ejecución offline completa."""

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from biblioteca.errores import ErrorValidacion
from biblioteca.importacion.fuente_openlibrary import FuenteOpenLibrary
from biblioteca.importacion.modelos import EstadoImportacion as Estado
from biblioteca.importacion.validador_openlibrary import ValidadorOpenLibrary

RAIZ = Path(__file__).resolve().parents[1]
DETALLES = RAIZ / "datos/openlibrary/respuestas_originales.json"


def test_fuente_es_solo_lectura_y_no_atribuye_detalle_de_otra_edicion(base_prevalidacion):
    antes = {p: sha256(p.read_bytes()).hexdigest() for p in (base_prevalidacion, DETALLES)}
    candidatas = list(FuenteOpenLibrary(base_prevalidacion, DETALLES).iterar())
    assert len(candidatas) == 1000
    completas = [c for c in candidatas if c.datos["detalle"] is not None]
    assert len(completas) == 7
    for c in completas:
        assert c.datos["detalle"]["edicion"]["key"] == "/books/" + c.clave
    assert {p: sha256(p.read_bytes()).hexdigest() for p in (base_prevalidacion, DETALLES)} == antes


def test_regresiones_reales_meow_mort_y_dracula(base_prevalidacion):
    candidatas = list(FuenteOpenLibrary(base_prevalidacion, DETALLES).iterar())
    v = ValidadorOpenLibrary()
    indice = {c.clave: c for c in candidatas}
    meow = v.evaluar(indice["OL46535310M"])
    mort = v.evaluar(indice["OL9144662M"])
    dracula = v.evaluar(indice["OL42827765M"])
    assert meow.estado is Estado.ENRIQUECIDA
    assert meow.normalizados["edicion"]["titulo"] == "Meow"
    assert "titulo_y_titulo_completo_difieren" in meow.alertas
    assert mort.estado is Estado.ENRIQUECIDA and "titulo_breve_revisar" in mort.alertas
    assert dracula.estado is Estado.PENDIENTE
    assert "muchos_autores_revisar_creditos" in dracula.alertas
    assert sum(v.evaluar(c).estado is Estado.VALIDADA for c in candidatas) == 5


def test_detalles_con_mismo_id_y_contenido_distinto_no_se_eligen_arbitrariamente(tmp_path, base_prevalidacion):
    originales = json.loads(DETALLES.read_text())
    duplicado = json.loads(json.dumps(originales[0]))
    duplicado["edicion"]["title"] = "Otro título contradictorio"
    destino = tmp_path / "detalles.json"
    destino.write_text(json.dumps([originales[0], duplicado]), encoding="utf-8")
    candidatas = list(FuenteOpenLibrary(base_prevalidacion, destino).iterar())
    c = next(c for c in candidatas if c.clave == originales[0]["edicion"]["key"].removeprefix("/books/"))
    assert c.datos["detalle_ambiguo"]
    assert ValidadorOpenLibrary().evaluar(c).estado is Estado.RECHAZADA


def test_sin_detalles_no_hay_aceptacion_automatica_y_limite_se_valida(base_prevalidacion):
    fuente = FuenteOpenLibrary(base_prevalidacion)
    candidatas = list(fuente.iterar(limite=3))
    assert len(candidatas) == 3
    assert all(ValidadorOpenLibrary().evaluar(c).estado is Estado.PENDIENTE for c in candidatas)
    with pytest.raises(ErrorValidacion):
        list(fuente.iterar(limite=True))
    with pytest.raises(ErrorValidacion):
        list(FuenteOpenLibrary(base_prevalidacion.parent / "inexistente.db").iterar())


def test_cli_integra_y_repite_la_muestra_real_sin_duplicar(tmp_path, base_prevalidacion):
    destino = tmp_path / "operativa.db"
    comando = [sys.executable, "-m", "biblioteca.importacion", "--fuente", str(base_prevalidacion),
               "--detalles", str(DETALLES), "--destino", str(destino)]
    identidades = None
    for vuelta in range(2):
        resultado = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True, check=True)
        informe = json.loads(resultado.stdout)
        assert informe["estados"] == {"PENDIENTE": 993, "ENRIQUECIDA": 2, "VALIDADA": 5, "RECHAZADA": 0}
        assert informe["ediciones_integradas"] == informe["obras_integradas"] == 5
        assert informe["conflictos_integracion"] == []
        with sqlite3.connect(destino) as c:
            actuales = c.execute("SELECT id, obra_id, id_openlibrary FROM edicion ORDER BY id").fetchall()
            if vuelta == 0:
                identidades = actuales
            else:
                assert actuales == identidades
            assert c.execute("SELECT COUNT(*) FROM ejemplar").fetchone()[0] == 0
            assert c.execute("SELECT COUNT(*) FROM evaluacion_importacion").fetchone()[0] == 1000
            assert c.execute("SELECT COUNT(*) FROM decision_importacion").fetchone()[0] == 1000
            assert c.execute("PRAGMA foreign_key_check").fetchall() == []


def test_cli_impide_usar_la_fuente_como_destino(base_prevalidacion):
    antes = sha256(base_prevalidacion.read_bytes()).hexdigest()
    r = subprocess.run([sys.executable, "-m", "biblioteca.importacion", "--fuente", str(base_prevalidacion), "--destino", str(base_prevalidacion)],
                       cwd=RAIZ, capture_output=True, text=True)
    assert r.returncode == 2
    assert "distinto" in r.stderr
    assert sha256(base_prevalidacion.read_bytes()).hexdigest() == antes


def test_cli_solo_evaluar_no_crea_catalogo(tmp_path, base_prevalidacion):
    destino = tmp_path / "solo_evaluacion.db"
    r = subprocess.run([sys.executable, "-m", "biblioteca.importacion", "--fuente", str(base_prevalidacion), "--detalles", str(DETALLES),
                        "--destino", str(destino), "--solo-evaluar", "--limite", "10"],
                       cwd=RAIZ, capture_output=True, text=True, check=True)
    assert json.loads(r.stdout)["ediciones_evaluadas"] == 10
    with sqlite3.connect(destino) as c:
        assert c.execute("SELECT COUNT(*) FROM obra").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM termino_clasificacion").fetchone()[0] == 0
