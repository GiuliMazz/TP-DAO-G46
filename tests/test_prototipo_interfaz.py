"""Estado de presentación: navegación, páginas y descarte de búsquedas obsoletas."""

import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest
import flet as ft

from biblioteca.interfaz.aplicacion import AplicacionHorizonte
from biblioteca.interfaz.catalogo_view import CatalogoView
from biblioteca.interfaz.datos_prototipo import DatosPrototipo
from biblioteca.interfaz.socios_view import SociosView


class PaginaPrueba:
    width = 1440
    height = 960
    web = False

    def __init__(self):
        self.actualizaciones = 0
        self.dialogo = None
        self.window = SimpleNamespace()

    def update(self):
        self.actualizaciones += 1

    def show_dialog(self, dialogo):
        self.dialogo = dialogo

    def pop_dialog(self):
        self.dialogo = None

    def add(self, control):
        self.control = control


@pytest.mark.parametrize("texto", ["Mago de Terramar", "Wizard of Earthsea", "Le Guin"])
def test_busqueda_unica_de_muestra_encuentra_una_obra(texto):
    # Es un filtro de maqueta; el buscador SQL se verificará al conectar 3B.
    obras = DatosPrototipo().buscar_obras(texto)
    assert [o.titulo for o in obras] == ["Un mago de Terramar"]


def test_filtros_y_cambio_de_vista_conservan_la_consulta():
    vista = CatalogoView(PaginaPrueba(), DatosPrototipo())
    vista.genero.value = "Fantasía épica"
    vista.sede.value = "Norte"
    vista.disponibilidad.value = "Disponibles"
    vista._filtrar()
    assert vista.resumen.value.startswith("2 obras")
    vista._cambiar_vista(True)
    assert vista.resumen.value.startswith("2 obras")
    assert vista.sede.value == "Norte"


def test_paginas_acotadas_y_reinicio_tras_filtrar():
    datos = DatosPrototipo()
    datos.obras = tuple(replace(datos.obras[0], titulo=f"Obra {i}") for i in range(49))
    vista = CatalogoView(PaginaPrueba(), datos)
    assert len(vista.resultados.content.controls) == 24
    vista._paginar(1)
    assert vista.contador.value.startswith("25–48 de 49")
    vista._paginar(1)
    assert len(vista.resultados.content.controls) == 1
    assert vista.siguiente.disabled
    vista.busqueda.value = "Obra 48"
    vista._filtrar()
    assert vista.pagina == 0
    assert vista.contador.value.startswith("1–1 de 1")
    assert vista.anterior.disabled and vista.siguiente.disabled


def test_busqueda_pendiente_no_actualiza_una_vista_abandonada(monkeypatch):
    pagina = PaginaPrueba()
    vista = CatalogoView(pagina, DatosPrototipo())
    async def salir_durante_espera(segundos):
        vista.activar(False)
    monkeypatch.setattr("biblioteca.interfaz.catalogo_view.asyncio.sleep", salir_durante_espera)
    asyncio.run(vista._buscar(None))
    assert pagina.actualizaciones == 0


def test_solo_ultima_busqueda_pendiente_actualiza(monkeypatch):
    pagina = PaginaPrueba()
    vista = CatalogoView(pagina, DatosPrototipo())
    async def recorrido():
        esperas = []
        async def esperar(segundos):
            listo = asyncio.Event()
            esperas.append(listo)
            await listo.wait()
        monkeypatch.setattr("biblioteca.interfaz.catalogo_view.asyncio.sleep", esperar)
        primera = asyncio.create_task(vista._buscar(None))
        await _ceder()
        segunda = asyncio.create_task(vista._buscar(None))
        await _ceder()
        vista.busqueda.value = "Terramar"
        esperas[1].set()
        await segunda
        esperas[0].set()
        await primera
    asyncio.run(recorrido())
    assert pagina.actualizaciones == 1
    assert vista.resumen.value.startswith("1 obra ·")


async def _ceder():
    # No usa sleep, para poder sustituir la espera de debounce.
    loop = asyncio.get_running_loop()
    turno = loop.create_future()
    loop.call_soon(turno.set_result, None)
    await turno


def test_navegacion_preserva_filtros_e_ignora_modulos_futuros():
    pagina = PaginaPrueba()
    app = AplicacionHorizonte(pagina, DatosPrototipo())
    app.montar()
    app.navegar("Catálogo")
    app.catalogo.busqueda.value = "Terramar"
    app.catalogo._filtrar()
    app.navegar("Socios")
    app.navegar("Remitos")
    assert app.destino == "Socios"
    app.navegar("Catálogo")
    assert app.catalogo.busqueda.value == "Terramar"
    assert app.catalogo.resumen.value.startswith("1 obra ·")
    pagina.width = 950
    app._redimensionar()
    assert app.compacta and app.destino == "Catálogo"


def test_sede_de_trabajo_no_restringe_socios_de_la_red():
    app = AplicacionHorizonte(PaginaPrueba(), DatosPrototipo())
    app.selector_sede.value = "Sur"
    app._cambiar_sede()
    assert app.inicio.sede == "Sur"
    assert app.socios.resumen.value.startswith("4 socios")
    assert app.catalogo.sede.value == "Todas"


def test_modo_oscuro_conserva_vista_filtros_y_sede_sin_reconstruir_controles():
    pagina = PaginaPrueba()
    app = AplicacionHorizonte(pagina, DatosPrototipo())
    app.montar()
    app.navegar("Catálogo")
    app.catalogo.busqueda.value = "Terramar"
    app.catalogo._filtrar()
    app.selector_sede.value = "Norte"
    app._cambiar_sede()
    control = app.contenido.content
    app._alternar_tema()
    assert pagina.theme_mode == ft.ThemeMode.DARK
    assert app.boton_tema.tooltip == "Activar modo claro"
    assert app.contenido.content is control
    assert app.destino == "Catálogo" and app.sede == "Norte"
    assert app.catalogo.busqueda.value == "Terramar"
    assert app.catalogo.resumen.value.startswith("1 obra ·")
    app._alternar_tema()
    assert pagina.theme_mode == ft.ThemeMode.LIGHT
    assert app.boton_tema.tooltip == "Activar modo oscuro"


def test_formulario_es_descartable_y_no_muta_datos_de_muestra():
    pagina = PaginaPrueba()
    datos = DatosPrototipo()
    vista = SociosView(pagina, datos)
    socio = datos.socios[0]
    vista.abrir_formulario(socio)
    campos = pagina.dialogo.content.content.controls
    campos[1].value = "Nombre editado"
    pagina.dialogo.actions[0].on_click(None)
    assert pagina.dialogo is None
    assert datos.socios[0] == socio
    assert socio.nombre == "Ana Martínez"
    vista.estado.value = "Inhabilitados"
    vista._mostrar()
    assert vista.resumen.value.startswith("1 socio ·")
