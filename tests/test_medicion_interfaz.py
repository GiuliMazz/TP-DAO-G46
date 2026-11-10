"""Aislamiento de la fixture y evidencia de consultas del mismo backend."""

from contextlib import closing
import json
import sqlite3

import pytest

from biblioteca.consultas_locales import ConsultasCatalogoLocal
from biblioteca.errores import ErrorValidacion
from herramientas.medir_interfaz import ConsultasMedidas, RegistroMedicion, exigir_sintetica, preparar
from herramientas.catalogo_sintetico import id_sintetico


def test_fixture_identificada_y_repeticion_no_sobrescribe(tmp_path):
    base = tmp_path / "sintetica.db"
    carga = preparar(base, 30)
    assert carga["filas"]["obra"] == 30
    assert exigir_sintetica(base)["cantidad_obras"] == 30
    assert ConsultasCatalogoLocal(base).configuracion().tipo == "RENDIMIENTO"
    antes = base.read_bytes()
    with pytest.raises(ErrorValidacion):
        preparar(base, 30)
    assert base.read_bytes() == antes
    with closing(sqlite3.connect(base)) as c:
        assert c.execute("SELECT COUNT(*) FROM socio").fetchone()[0] == 0


@pytest.mark.parametrize("tipo", ["OPERATIVA", "DEMOSTRACION"])
def test_servidor_de_medicion_no_adopta_otra_base(tmp_path, tipo):
    base = tmp_path / "otra.db"
    base.with_suffix(".db.tipo.json").write_text(json.dumps({"tipo": tipo}))
    with pytest.raises(ErrorValidacion):
        exigir_sintetica(base)
    assert not base.exists()


def test_medicion_registra_backend_real_sin_presentarlo_como_render(tmp_path):
    base = tmp_path / "sintetica.db"
    preparar(base, 30)
    registro = RegistroMedicion(base, tmp_path / "servidor.json")
    consulta = ConsultasMedidas(base, registro)
    pagina = consulta.consultar_pagina(texto="Original sintético 000011", limite=24)
    assert pagina.total == 1
    registro.guardar()
    datos = json.loads(registro.destino.read_text())
    inicio, fin = datos["eventos"]
    assert inicio["tipo"] == "consulta_inicio" and fin["tipo"] == "consulta_fin"
    assert fin["consulta"] == inicio["id"] and fin["filas"] == 1
    assert fin["instante_ns"] >= inicio["instante_ns"]
    assert datos["demora_artificial_ms"] == 0 and fin["duracion_ms"] >= 0


def test_disponibilidad_local_no_reexplora_toda_la_sede_por_obra(tmp_path):
    base = tmp_path / "sintetica.db"
    preparar(base, 1000)
    with closing(ConsultasCatalogoLocal(base)._abrir()) as c:
        # Presupuesto de trabajo SQLite, independiente de velocidad de CPU/disco.
        # La consulta correlacionada anterior superaba este presupuesto; una
        # búsqueda por identidades procesa el inventario una vez por sentencia.
        pasos = [0]
        def limite():
            pasos[0] += 1000
            return int(pasos[0] > 750000)
        c.set_progress_handler(limite, 1000)
        for disponible, total in ((True, 159), (False, 841)):
            pasos[0] = 0
            pagina = ConsultasCatalogoLocal._catalogo(c).consultar_pagina(
                texto="sintético", sede_id=id_sintetico("sede", 1), disponibles=disponible)
            assert pagina.total == total and len(pagina.obras) == 24
        c.set_progress_handler(None, 0)
