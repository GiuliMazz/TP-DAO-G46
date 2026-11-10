"""Recorrido integrado y protección de consultas de volumen, sin aserciones de tiempo."""

from contextlib import closing
from hashlib import sha256
from pathlib import Path

import pytest

from biblioteca.demo_etapa2 import demostrar
from biblioteca.importacion.fuente_openlibrary import FuenteOpenLibrary
from biblioteca.persistencia.base_datos import VERSION_ESQUEMA, conectar, migrar
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.errores import ErrorPersistencia
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from herramientas.catalogo_sintetico import generar_catalogo, id_sintetico
from herramientas.medir_etapa2 import _medir, medir_catalogo

RAIZ = Path(__file__).resolve().parents[1]


def test_recorrido_real_con_operaciones_simuladas_preserva_etapa1_y_fuentes(tmp_path, base_prevalidacion):
    base = base_prevalidacion
    detalles = RAIZ / "datos/openlibrary/respuestas_originales.json"
    antes = [sha256(p.read_bytes()).hexdigest() for p in (base, detalles)]
    ruta = tmp_path / "recorrido.db"
    resultado = demostrar(ruta, FuenteOpenLibrary(base, detalles))
    assert resultado["reimportacion_conserva_datos"] and resultado["persistencia_tras_reabrir"]
    assert resultado["disponibilidad_inicial"] == {"Centro": 1, "Norte": 1, "Sur": 0}
    assert resultado["disponibilidad_final"] == {"Centro": 0, "Norte": 0, "Sur": 0}
    assert resultado["socio"] == "INHABILITADO"
    assert [sha256(p.read_bytes()).hexdigest() for p in (base, detalles)] == antes
    with closing(conectar(ruta)) as c:
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert c.execute("SELECT COUNT(*) FROM obra").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM edicion").fetchone()[0] == 2


def test_fixture_sintetica_es_reproducible_y_no_sobrescribe_destinos(tmp_path):
    rutas = [tmp_path / n for n in ("uno.db", "dos.db")]
    for ruta in rutas:
        resumen = generar_catalogo(ruta, 40, lote=7)
        assert resumen["filas"]["obra"] == 40
        assert resumen["filas"]["edicion"] == 48
        assert resumen["filas"]["obra_autor"] == 44
    with closing(conectar(rutas[0])) as a, closing(conectar(rutas[1])) as b:
        for tabla in ("obra", "edicion", "autor", "obra_autor", "ejemplar", "clasificacion_obra"):
            assert [tuple(f) for f in a.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2")] == [tuple(f) for f in b.execute(f"SELECT * FROM {tabla} ORDER BY 1, 2")]
        assert a.execute("SELECT COUNT(*) FROM obra WHERE id_openlibrary IS NOT NULL").fetchone()[0] == 0
    with pytest.raises(ValueError):
        generar_catalogo(rutas[0], 40)


def test_herramienta_mide_servicios_y_captura_su_sql(tmp_path):
    ruta = tmp_path / "carga.db"
    generar_catalogo(ruta, 40)
    informe = medir_catalogo(ruta, 40, 1)
    assert len(informe["escenarios"]) == 15
    assert all(not s.get("interrumpida") for s in informe["escenarios"].values())
    assert informe["escenarios"]["combinados"]["filas_resultado"] > 0
    assert informe["escenarios"]["titulo_alternativo"]["filas_resultado"] == 1
    assert informe["escenarios"]["primera_pagina"]["consultas_sql"] == 2
    assert informe["escenarios"]["primera_pagina"]["planes"][0]["plan"]


def test_medicion_conserva_interrupcion_en_una_muestra_y_limpia_callback(conexion):
    llamadas = [0]
    def operacion():
        llamadas[0] += 1
        if llamadas[0] == 1:
            return ejecutar(conexion, "SELECT 1").fetchall()
        return ejecutar(conexion, """WITH RECURSIVE numeros(n) AS (
            SELECT 1 UNION ALL SELECT n + 1 FROM numeros WHERE n < 100000)
            SELECT SUM(n) FROM numeros""").fetchall()
    resultado, medida = _medir(conexion, operacion, 2, limite_segundos=0)
    assert resultado is None
    assert medida["interrumpida"] and medida["fase"] == "muestra 1"
    assert ejecutar(conexion, "SELECT 2").fetchone()[0] == 2


def test_pagina_disponible_por_sede_no_recorre_producto_de_obras_y_copias(tmp_path):
    ruta = tmp_path / "carga.db"
    generar_catalogo(ruta, 1000)
    with closing(conectar(ruta)) as c:
        pasos = [0]
        def presupuesto():
            pasos[0] += 1000
            return int(pasos[0] > 500_000)
        c.set_progress_handler(presupuesto, 1000)
        try:
            filas = EjemplarRepository(c).listar(sede_actual_id=id_sintetico("sede"), solo_disponibles=True)
        finally:
            c.set_progress_handler(None, 0)
        # Presupuesto amplio de instrucciones SQLite, independiente de velocidad CPU.
        assert len(filas) == 50
        assert all(e.esta_disponible() for e in filas)


@pytest.mark.parametrize("fallo", [False, True])
def test_indice_se_agrega_sin_perder_datos_y_fallo_revierte_la_migracion(tmp_path, monkeypatch, fallo, base_prevalidacion):
    base = base_prevalidacion
    detalles = RAIZ / "datos/openlibrary/respuestas_originales.json"
    ruta = tmp_path / "anterior.db"
    demostrar(ruta, FuenteOpenLibrary(base, detalles))
    with closing(conectar(ruta)) as c:
        # El esquema 6 sólo agrega este índice: retirarlo reconstruye el esquema 5.
        c.execute("DROP INDEX ix_ejemplar_sede_estado_codigo")
        c.execute("PRAGMA user_version = 5")
        tablas = [f[0] for f in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        antes = {t: [tuple(f) for f in c.execute(f'SELECT * FROM "{t}" ORDER BY 1, 2')] for t in tablas}
        if fallo:
            leer = Path.read_text
            def lectura(archivo, **kwargs):
                contenido = leer(archivo, **kwargs)
                return contenido + "\nFALLO;\n" if archivo.name == "006_indices_consultas.sql" else contenido
            with monkeypatch.context() as m:
                m.setattr(Path, "read_text", lectura)
                with pytest.raises(ErrorPersistencia):
                    migrar(c)
            assert c.execute("PRAGMA user_version").fetchone()[0] == 5
            assert c.execute("SELECT name FROM sqlite_master WHERE name = 'ix_ejemplar_sede_estado_codigo'").fetchall() == []
        migrar(c)
        migrar(c)
        assert c.execute("PRAGMA user_version").fetchone()[0] == VERSION_ESQUEMA == 6
        assert c.execute("SELECT name FROM sqlite_master WHERE name = 'ix_ejemplar_sede_estado_codigo'").fetchone()
        for tabla, filas in antes.items():
            assert [tuple(f) for f in c.execute(f'SELECT * FROM "{tabla}" ORDER BY 1, 2')] == filas
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
