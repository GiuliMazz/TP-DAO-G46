"""Lecturas reales, límites de concurrencia y estado gráfico ante resultados tardíos."""

import asyncio
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import threading
from types import SimpleNamespace
from uuid import uuid4

import flet as ft
import pytest

from biblioteca.consultas_locales import ConsultasCatalogoLocal
from biblioteca.errores import ErrorPersistencia
from biblioteca.interfaz.aplicacion import AplicacionHorizonte
from biblioteca.interfaz.catalogo_local_view import CatalogoLocalView, LibroPagina
from biblioteca.interfaz.lector_asincrono import LectorAsincrono, ConsultaReemplazada
from biblioteca.resultados_catalogo import EntradaCatalogo, FichaObra, PaginaCatalogo


class Pagina:
    width, height, web = 1440, 960, False

    def __init__(self):
        self.window = SimpleNamespace()
        self.actualizaciones = 0
        self.dialogo = None
        self.tareas = []

    def run_task(self, funcion, *args):
        tarea = asyncio.create_task(funcion(*args))
        self.tareas.append(tarea)
        return tarea

    def update(self):
        self.actualizaciones += 1

    def add(self, control):
        self.control = control

    def show_dialog(self, dialogo):
        self.dialogo = dialogo

    def pop_dialog(self):
        self.dialogo = None


def pagina_resultado(titulo="Título español", total=1):
    ficha = FichaObra(uuid4(), titulo, "Original", uuid4(), ("Autora",), 1)
    return PaginaCatalogo((EntradaCatalogo(ficha, None, (), 0),), total, 24, 0, None)


class LectorControlado:
    def __init__(self):
        self.peticiones = []

    async def ejecutar(self, destino, funcion, *args, **kwargs):
        futuro = asyncio.get_running_loop().create_future()
        self.peticiones.append((futuro, destino, args, kwargs))
        return await futuro


def vista_controlada():
    pagina, lector = Pagina(), LectorControlado()
    vista = CatalogoLocalView(pagina, ConsultasCatalogoLocal(), lector)
    vista.configurar(SimpleNamespace(tipo="DEMOSTRACION", sedes=(), generos=()))
    return vista, pagina, lector


def test_base_ausente_no_se_crea_ni_migra(tmp_path):
    ruta = tmp_path / "inexistente.db"
    with pytest.raises(ErrorPersistencia):
        ConsultasCatalogoLocal(ruta).consultar_pagina()
    assert not ruta.exists()


def test_esquema_incompatible_no_se_migra(tmp_path):
    ruta = tmp_path / "antigua.db"
    with sqlite3.connect(ruta) as c:
        c.execute("PRAGMA user_version=1")
    antes = ruta.read_bytes()
    with pytest.raises(ErrorPersistencia):
        ConsultasCatalogoLocal(ruta).consultar_pagina()
    assert ruta.read_bytes() == antes


def test_consultas_usan_servicios_sin_escrituras_y_conexion_propia(ruta_db, conexion, catalogo, sedes, inventario):
    autora = catalogo.registrar_autor("Autora de integración")
    obra = catalogo.registrar_obra("Original", [autora.id])
    edicion = catalogo.registrar_edicion(obra.id, "Edición española")
    sede = sedes.registrar("Centro", "Dirección", "Contacto", "9 a 18")
    inventario.registrar("TEST-1", edicion.id, sede.id)
    ruta_db.with_suffix(".db.tipo.json").write_text(json.dumps({"version": 1, "tipo": "DEMOSTRACION"}))
    antes = sha256(ruta_db.read_bytes()).hexdigest()
    conexiones = []
    class ConsultaObservada(ConsultasCatalogoLocal):
        def _abrir(self):
            c = super()._abrir()
            conexiones.append((c, threading.get_ident()))
            return c
    consulta = ConsultaObservada(ruta_db)
    async def recorrido():
        lector = LectorAsincrono()
        try:
            config = await lector.ejecutar("configuracion", consulta.configuracion)
            pagina = await lector.ejecutar("catalogo", consulta.consultar_pagina, texto="española")
            ficha = await lector.ejecutar("ficha", consulta.ficha, obra.id)
            assert config.tipo == "DEMOSTRACION"
            assert pagina.total == 1 and pagina.obras[0].disponibles == 1
            assert ficha.ediciones[0].id == edicion.id
            assert ficha.existencias[0].total_propios == 1
            # Verificar el cierre desde el mismo hilo que creó las conexiones.
            def verificar_cierres():
                for c, _ in conexiones:
                    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
                        c.execute("SELECT 1")
            await lector.ejecutar("configuracion", verificar_cierres)
        finally:
            lector.cerrar()
    asyncio.run(recorrido())
    assert len(conexiones) == 3 and len({id(c) for c, _ in conexiones}) == 3
    assert all(hilo != threading.get_ident() for _, hilo in conexiones)
    assert sha256(ruta_db.read_bytes()).hexdigest() == antes


def test_un_trabajador_coalesce_esperas_y_cancelar_no_libera_sqlite():
    async def recorrido():
        lector = LectorAsincrono()
        inicio, liberar = threading.Event(), threading.Event()
        ejecutadas = []
        def lenta():
            inicio.set()
            assert liberar.wait(3)
            ejecutadas.append("primera")
        def rapida(nombre):
            ejecutadas.append(nombre)
            return nombre
        primera = asyncio.create_task(lector.ejecutar("catalogo", lenta))
        try:
            while not inicio.is_set():
                await asyncio.sleep(0.001)
            primera.cancel()
            with pytest.raises(asyncio.CancelledError):
                await primera
            segunda = asyncio.create_task(lector.ejecutar("catalogo", rapida, "segunda"))
            await asyncio.sleep(0)
            tercera = asyncio.create_task(lector.ejecutar("catalogo", rapida, "tercera"))
            await asyncio.sleep(0)
            with pytest.raises(ConsultaReemplazada):
                await segunda
            # El bucle sigue respondiendo, pero el segundo SQL no empieza aún.
            assert ejecutadas == [] and len(lector._pendientes) == 1
            liberar.set()
            assert await tercera == "tercera"
            assert ejecutadas == ["primera", "tercera"]
        finally:
            liberar.set()
            lector.cerrar()
    asyncio.run(recorrido())


def test_cerrar_descarta_pendientes_y_rechaza_nuevas():
    async def recorrido():
        lector = LectorAsincrono()
        inicio, liberar = threading.Event(), threading.Event()
        primera = asyncio.create_task(lector.ejecutar("catalogo", lambda: (inicio.set(), liberar.wait(3))))
        try:
            while not inicio.is_set():
                await asyncio.sleep(0.001)
            pendiente = asyncio.create_task(lector.ejecutar("ficha", lambda: pytest.fail("No debe ejecutarse")))
            await asyncio.sleep(0)
            lector.cerrar()
            with pytest.raises(ConsultaReemplazada):
                await pendiente
            with pytest.raises(ConsultaReemplazada):
                await lector.ejecutar("catalogo", lambda: None)
        finally:
            liberar.set()
            await primera
            lector.cerrar()
    asyncio.run(recorrido())


@pytest.mark.parametrize("error_antiguo", [False, True])
def test_resultado_o_error_tardio_no_pisa_busqueda_nueva(error_antiguo):
    async def recorrido():
        vista, pagina, lector = vista_controlada()
        primera = asyncio.create_task(vista.cargar())
        await asyncio.sleep(0)
        vista.busqueda.value = "Nueva"
        segunda = asyncio.create_task(vista.cargar(reiniciar=True))
        await asyncio.sleep(0)
        lector.peticiones[1][0].set_result(pagina_resultado("Nueva"))
        await segunda
        actualizaciones = pagina.actualizaciones
        if error_antiguo:
            lector.peticiones[0][0].set_exception(ErrorPersistencia("Error viejo"))
        else:
            lector.peticiones[0][0].set_result(pagina_resultado("Vieja"))
        await primera
        assert vista._pagina_resultado.obras[0].ficha.titulo_mostrado == "Nueva"
        assert not vista._cargando and pagina.actualizaciones == actualizaciones
    asyncio.run(recorrido())


def test_salida_y_debounce_invalidan_busquedas():
    async def recorrido():
        vista, pagina, lector = vista_controlada()
        primera = asyncio.create_task(vista._buscar())
        await asyncio.sleep(0)
        segunda = asyncio.create_task(vista._buscar())
        await asyncio.sleep(0)
        vista.activar(False)
        actualizaciones = pagina.actualizaciones
        await asyncio.gather(primera, segunda)
        assert lector.peticiones == [] and pagina.actualizaciones == actualizaciones
    asyncio.run(recorrido())


def test_error_y_reintento_recuperan_catalogo_con_filtros_sql():
    async def recorrido():
        vista, pagina, lector = vista_controlada()
        vista.sede.value = str(uuid4())
        vista.disponibilidad.value = "Disponibles"
        vista.pagina = 2
        primera = asyncio.create_task(vista.cargar())
        await asyncio.sleep(0)
        assert lector.peticiones[0][3]["desplazamiento"] == 48
        assert lector.peticiones[0][3]["sede_id"] == vista.sede.value
        assert lector.peticiones[0][3]["disponibles"] is True
        lector.peticiones[0][0].set_exception(ErrorPersistencia("Base ocupada"))
        await primera
        assert vista._pagina_resultado is None and vista.siguiente.disabled
        segunda = asyncio.create_task(vista.cargar())
        await asyncio.sleep(0)
        lector.peticiones[1][0].set_result(replace(pagina_resultado(), total=49, desplazamiento=48))
        await segunda
        assert vista.contador.value.startswith("49–49 de 49")
        vista._cambiar_vista(True)
        assert vista.tabla and vista.sede.value == lector.peticiones[0][3]["sede_id"]
    asyncio.run(recorrido())


def test_ficha_cerrada_no_recibe_datos_tardios():
    async def recorrido():
        vista, pagina, lector = vista_controlada()
        tarea = asyncio.create_task(vista._abrir_ficha(LibroPagina(pagina_resultado().obras[0])))
        await asyncio.sleep(0)
        pagina.dialogo.actions[0].on_click(None)
        actualizaciones = pagina.actualizaciones
        lector.peticiones[0][0].set_result(None)
        await tarea
        assert pagina.dialogo is None and pagina.actualizaciones == actualizaciones
    asyncio.run(recorrido())


def test_portada_ausente_y_error_de_imagen_tienen_cubierta_ilustrativa(monkeypatch):
    obra = LibroPagina(pagina_resultado().obras[0])
    control = CatalogoLocalView.portada(obra)
    assert not isinstance(control.content, ft.Image)
    assert "Portada ilustrativa" in control.content.tooltip
    assert obra.entrada.portada_edicion_id is None
    monkeypatch.setattr(ConsultasCatalogoLocal, "portada_local", lambda id: "no-existe.jpg")
    control = CatalogoLocalView.portada(obra)
    assert isinstance(control.content, ft.Image) and control.content.error_content is not None
    assert "Portada ilustrativa" in control.content.error_content.tooltip


def test_inicio_real_no_inventa_socios_ni_copias_si_falta_base(tmp_path):
    async def recorrido():
        ruta = tmp_path / "ausente.db"
        pagina = Pagina()
        app = AplicacionHorizonte(pagina, consultas=ConsultasCatalogoLocal(ruta))
        try:
            await app._inicializar()
            assert app.socios is None and "Socios" not in app.vistas
            assert not ruta.exists() and app.aviso_base.value == "Base local no disponible"
        finally:
            await app._desconectar()
    asyncio.run(recorrido())


def test_reconexion_espera_al_trabajador_anterior_sin_bloquear():
    async def recorrido():
        consultas = SimpleNamespace(base=Path("demo.db"), configuracion=lambda:
            SimpleNamespace(tipo="DEMOSTRACION", sedes=(), generos=()))
        app = AplicacionHorizonte(Pagina(), consultas=consultas)
        previo = app.lector
        inicio, liberar = threading.Event(), threading.Event()
        activa = asyncio.create_task(previo.ejecutar("catalogo", lambda: (inicio.set(), liberar.wait(3))))
        try:
            while not inicio.is_set():
                await asyncio.sleep(0.001)
            await app._desconectar()
            reconexion = asyncio.create_task(app._reconectar())
            await asyncio.sleep(0)
            assert app._cerrada and app.lector is previo
            liberar.set()
            await activa
            await reconexion
            assert not app._cerrada and app.lector is not previo
        finally:
            liberar.set()
            await activa
            await app._desconectar()
    asyncio.run(recorrido())
