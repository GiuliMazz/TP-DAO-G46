"""Composición de Horizonte. La maqueta sólo se activa con datos explícitos."""

import flet as ft

from biblioteca.interfaz.catalogo_view import CatalogoView
from biblioteca.interfaz.componentes import BORDE, FONDO, PETROLEO, SECUNDARIO, SEMILLA, SUPERFICIE, TINTA, etiqueta, selector
from biblioteca.interfaz.datos_prototipo import SEDES
from biblioteca.interfaz.inicio_view import InicioView
from biblioteca.interfaz.socios_view import SociosView
from biblioteca.consultas_locales import BASE_DEMO, ConsultasCatalogoLocal
from biblioteca.administracion_local import AdministracionLocal
from biblioteca.interfaz.escritor_asincrono import EscritorAsincrono
from biblioteca.interfaz.socios_local_view import SociosLocalView
from biblioteca.interfaz.sedes_local_view import SedesLocalView
from biblioteca.interfaz.inventario_local_view import InventarioLocalView
from biblioteca.interfaz.catalogo_local_view import CatalogoLocalView
from biblioteca.interfaz.lector_asincrono import LectorAsincrono, ConsultaReemplazada


class AplicacionHorizonte:
    MODULOS = (
        ("Inicio", ft.Icons.SPACE_DASHBOARD_OUTLINED),
        ("Catálogo", ft.Icons.AUTO_STORIES_OUTLINED),
        ("Préstamos", ft.Icons.BOOK_OUTLINED),
        ("Reservas", ft.Icons.BOOKMARK_BORDER),
        ("Remitos", ft.Icons.LOCAL_SHIPPING_OUTLINED),
        ("Socios", ft.Icons.PEOPLE_OUTLINE),
        ("Sedes", ft.Icons.LOCATION_ON_OUTLINED),
        ("Reportes", ft.Icons.BAR_CHART_OUTLINED),
    )

    def __init__(self, page, datos=None, *, consultas=None):
        self.page = page
        self.prototipo = datos is not None
        self.datos = datos
        self.consultas = consultas if consultas is not None else ConsultasCatalogoLocal()
        self.lector = None if self.prototipo else LectorAsincrono()
        self.escritor = None if self.prototipo else EscritorAsincrono()
        self.administracion = None if self.prototipo else AdministracionLocal(getattr(self.consultas, "base", BASE_DEMO))
        self._configuracion = None
        self._cerrada = False
        self._revision_inicio = 0
        self.destino = "Inicio"
        self.sede = "Centro"
        self.compacta = (page.width or 1280) < 1100
        self.inicio = InicioView(self.datos, self.navegar) if self.prototipo else None
        self.catalogo = (CatalogoView(page, self.datos) if self.prototipo else
                         CatalogoLocalView(page, self.consultas, self.lector))
        self.catalogo.activar(False)
        self.socios = SociosView(page, self.datos) if self.prototipo else None
        self.sedes = self.inventario = None
        self.inicio_control = (self.inicio.control if self.prototipo else
                              ft.Column([ft.ProgressRing(), ft.Text("Abriendo catálogo local…")]))
        self.vistas = {"Inicio": self.inicio if self.prototipo else self.inicio_control, "Catálogo": self.catalogo}
        if self.prototipo:
            self.vistas["Socios"] = self.socios
        self.menu = ft.Column(spacing=6)
        self.lateral = ft.Container(width=224, bgcolor=SUPERFICIE, padding=20,
                                    border=ft.Border(right=ft.BorderSide(1, BORDE)))
        self.ruta = ft.Text("Espacio de trabajo / Inicio", color=SECUNDARIO, size=12)
        self.selector_sede = selector("Sede de trabajo", list(SEDES), self.sede,
                                     self._cambiar_sede, width=190)
        if not self.prototipo:
            self.selector_sede.options = []
            self.selector_sede.value = None
            self.selector_sede.disabled = True
            self.sede = None
        self.boton_tema = ft.IconButton(icon=ft.Icons.DARK_MODE_OUTLINED, tooltip="Activar modo oscuro",
                                       on_click=self._alternar_tema, icon_color=PETROLEO)
        self.contenido = ft.Container(self.inicio_control, expand=True, padding=26)
        self.aviso_base = ft.Text("Prototipo visual · datos de muestra · los cambios no se guardan" if self.prototipo else
                                  "Catálogo local · verificando tipo de base…", color=SECUNDARIO, size=11)
        self.control = ft.Row([
            self.lateral,
            ft.Column([
                ft.Container(ft.Row([self.ruta, ft.Container(expand=True), self.boton_tema, self.selector_sede], spacing=12),
                             bgcolor=SUPERFICIE, padding=ft.Padding.symmetric(horizontal=26, vertical=14),
                             border=ft.Border(bottom=ft.BorderSide(1, BORDE))),
                self.contenido,
                ft.Container(self.aviso_base, padding=ft.Padding.only(left=26, bottom=12)),
            ], expand=True, spacing=0),
        ], spacing=0, height=max(page.height or 960, 700))
        self._dibujar_menu()

    def montar(self):
        self.page.title = "Horizonte · Administración bibliotecaria"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(color_scheme_seed=SEMILLA, use_material3=True,
                                   scaffold_bgcolor=FONDO)
        self.page.dark_theme = ft.Theme(color_scheme_seed=SEMILLA, use_material3=True,
                                        scaffold_bgcolor=FONDO)
        self.page.bgcolor = FONDO
        self.page.padding = 0
        self.page.spacing = 0
        self.page.scroll = ft.ScrollMode.AUTO
        if not self.page.web:
            self.page.window.width = 1440
            self.page.window.height = 960
            self.page.window.min_width = 900
            self.page.window.min_height = 700
        self.page.on_resize = self._redimensionar
        self.page.add(self.control)
        if not self.prototipo:
            self.page.on_disconnect = self._desconectar
            self.page.on_connect = self._reconectar
            self.page.run_task(self._inicializar)

    async def _inicializar(self):
        self._revision_inicio += 1
        revision = self._revision_inicio
        try:
            configuracion = await self.lector.ejecutar("configuracion", self.consultas.configuracion)
        except ConsultaReemplazada:
            return
        except Exception as error:
            if not self._cerrada and revision == self._revision_inicio:
                self.inicio_control.controls = [ft.Text("No se pudo abrir la base seleccionada", size=23, color=TINTA),
                    self.catalogo._error(error, lambda e: self.page.run_task(self._inicializar)),
                    ft.Text("La aplicación no crea ni prepara bases al iniciar. Prepará los datos con la herramienta explícita.",
                            color=SECUNDARIO, size=12)]
                self.aviso_base.value = "Base local no disponible"
                self.catalogo.resumen.value = "Base local no disponible"
                self.catalogo.resultados.content = self.catalogo._error(
                    error, lambda e: self.page.run_task(self._inicializar))
                self.page.update()
            return
        if self._cerrada or revision != self._revision_inicio:
            return
        self._configuracion = configuracion
        self.catalogo.configurar(configuracion)
        self._configurar_sedes(configuracion)
        self._habilitar_administracion(configuracion)
        tipo = configuracion.tipo
        avisos = {
            "DEMOSTRACION": "DEMOSTRACIÓN · bibliografía real · datos operativos ficticios · ",
            "OPERATIVA": "OPERATIVA · datos de la base seleccionada · ",
            "RENDIMIENTO": "RENDIMIENTO · bibliografía y existencias SINTÉTICAS · ",
        }
        nombres_base = {"DEMOSTRACION": "Base de demostración", "OPERATIVA": "Base operativa",
                        "RENDIMIENTO": "Prueba de escala · datos sintéticos"}
        self.aviso_base.value = avisos[tipo] + self.consultas.base.name
        self.inicio_control.controls = [
            ft.Text("Panel principal", size=27, weight=ft.FontWeight.W_600, color=TINTA),
            ft.Text("Red de Bibliotecas Horizonte", size=20, color=TINTA),
            etiqueta(nombres_base[tipo], disponible=False),
            ft.Text("Buscá por título original, edición española o autor. Consultá ediciones y disponibilidad en cada sede.",
                    color=SECUNDARIO),
            ft.FilledButton("Explorar catálogo", icon=ft.Icons.AUTO_STORIES_OUTLINED,
                            style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=PETROLEO),
                            on_click=lambda e: self.navegar("Catálogo")),
            ft.Text("Socios y sedes se administran desde el menú. El alta de ejemplares está en la ficha de cada obra. "
                    "Préstamos, reservas y remitos se habilitarán con sus procesos." if tipo != "RENDIMIENTO" else
                    "Base sintética para medición: la administración está deshabilitada.",
                    color=SECUNDARIO, size=13),
        ]
        self.inicio_control.spacing = 22
        self._dibujar_menu()
        self.page.update()
        if self.destino == "Catálogo":
            await self.catalogo.cargar()

    def _configurar_sedes(self, configuracion):
        activas = [s for s in configuracion.sedes if s.activa]
        self.selector_sede.options = [ft.DropdownOption(key=str(s.id), text=s.nombre) for s in activas]
        ids = {str(s.id) for s in activas}
        if self.sede not in ids:
            self.sede = str(activas[0].id) if activas else None
        self.selector_sede.value = self.sede
        self.selector_sede.disabled = not activas

    def _habilitar_administracion(self, configuracion):
        if configuracion.tipo not in {"OPERATIVA", "DEMOSTRACION"}:
            return
        if self.socios is None:
            self.socios = SociosLocalView(self.page, self.administracion, self.lector, self.escritor, self._al_guardar)
            self.sedes = SedesLocalView(self.page, self.administracion, self.lector, self.escritor, self._al_guardar)
            self.inventario = InventarioLocalView(self.page, self.administracion, self.lector, self.escritor, self._al_guardar)
            self.inventario.control.controls.insert(0, ft.TextButton("Volver al catálogo", icon=ft.Icons.ARROW_BACK,
                on_click=lambda e: self.navegar("Catálogo")))
            self.vistas.update({"Socios": self.socios, "Sedes": self.sedes, "Ejemplares": self.inventario})
        self.catalogo.al_inventario = self._abrir_inventario

    def _abrir_inventario(self, obra, ficha):
        self.catalogo._invalidar_ficha()
        self.page.pop_dialog()
        self.inventario.configurar(ficha.detalle.obra.id, obra.titulo, ficha.ediciones, self._configuracion.sedes)
        self.navegar("Ejemplares")

    async def _al_guardar(self, entidad):
        if entidad == "sedes":
            configuracion = await self.lector.ejecutar("configuracion", self.consultas.configuracion)
            if self._cerrada:
                return
            self._configuracion = configuracion
            self._configurar_sedes(configuracion)
            self.catalogo.configurar(configuracion)
            if self.inventario.obra_id is not None:
                self.inventario.configurar(self.inventario.obra_id, self.inventario.contexto.value,
                                          self.inventario.ediciones, configuracion.sedes)
            self.page.update()

    async def _desconectar(self, e=None):
        self._cerrada = True
        self._revision_inicio += 1
        self.catalogo.cerrar()
        self.lector.cerrar()
        self.escritor.cerrar()
        for vista in (self.socios, self.sedes, self.inventario):
            if vista:
                vista.cerrar()

    async def _reconectar(self, e=None):
        if self._cerrada:
            revision = self._revision_inicio
            await self.lector.esperar_cierre()
            await self.escritor.esperar_cierre()
            if revision != self._revision_inicio or not self._cerrada:
                return
            self._cerrada = False
            self.lector = LectorAsincrono()
            self.escritor = EscritorAsincrono()
            self.catalogo.lector = self.lector
            self.catalogo._cerrada = False
            self.catalogo._activa = self.destino == "Catálogo"
            for nombre in ("Socios", "Sedes", "Ejemplares"):
                vista = self.vistas.get(nombre)
                if vista:
                    vista.lector, vista.escritor = self.lector, self.escritor
                    if vista.formulario:
                        vista.formulario.dialogo.open = False
                        vista.formulario = None
                    vista.cerrada = False
                    vista.activar(self.destino == nombre)
            await self._inicializar()

    def _dibujar_menu(self):
        self.lateral.width = 80 if self.compacta else 224
        self.lateral.padding = 12 if self.compacta else 20
        self.menu.controls = []
        for nombre, icono in self.MODULOS:
            habilitado = nombre in self.vistas
            activo = nombre == self.destino
            color = PETROLEO if activo else SECUNDARIO
            self.menu.controls.append(ft.Container(
                ft.Row([ft.Icon(icono, color=color, size=21),
                        *([] if self.compacta else [ft.Text(nombre, color=color, size=13, expand=True),
                          *([] if habilitado else [ft.Icon(ft.Icons.LOCK_OUTLINE, size=13, color=SECUNDARIO)])])],
                       alignment=ft.MainAxisAlignment.CENTER if self.compacta else ft.MainAxisAlignment.START,
                       spacing=12),
                bgcolor=ft.Colors.PRIMARY_CONTAINER if activo else None, border_radius=8, height=44,
                padding=ft.Padding.symmetric(horizontal=12), opacity=1 if habilitado else 0.5,
                tooltip=nombre if habilitado else f"{nombre} · Próximamente",
                on_click=(lambda e, d=nombre: self.navegar(d)) if habilitado else None))
        marca = ft.Row([ft.Container(ft.Icon(ft.Icons.AUTO_STORIES_OUTLINED, color=ft.Colors.ON_PRIMARY, size=23),
                                    bgcolor=PETROLEO, padding=10, border_radius=10),
                        *([] if self.compacta else [ft.Column([
                            ft.Text("Horizonte", color=TINTA, size=21, weight=ft.FontWeight.W_600),
                            ft.Text("Gestión bibliotecaria", color=SECUNDARIO, size=10)], spacing=2)])], spacing=10)
        self.lateral.content = ft.Column([
            marca, ft.Container(height=24),
            *([] if self.compacta else [ft.Text("ESPACIO DE TRABAJO", color=SECUNDARIO, size=10)]),
            self.menu, ft.Container(expand=True),
            *([] if self.compacta else [etiqueta("Prototipo · etapa 3A" if self.prototipo else "Horizonte · etapa 3C", disponible=False),
                                        ft.Text("Red de Bibliotecas Horizonte", size=10, color=SECUNDARIO)]),
        ], spacing=12)

    def navegar(self, destino):
        if destino not in self.vistas:
            return
        self.destino = destino
        self.catalogo.activar(destino == "Catálogo")
        if not self.prototipo:
            for nombre in ("Socios", "Sedes", "Ejemplares"):
                vista = self.vistas.get(nombre)
                if vista:
                    vista.activar(destino == nombre)
        self.contenido.content = self.inicio_control if destino == "Inicio" else self.vistas[destino].control
        self.ruta.value = f"Espacio de trabajo / {destino}"
        self._dibujar_menu()
        self.page.update()

    def _cambiar_sede(self, e=None):
        self.sede = self.selector_sede.value
        if self.prototipo:
            self.inicio.actualizar(self.sede)
        self.page.update()

    def _alternar_tema(self, e=None):
        oscuro = self.page.theme_mode != ft.ThemeMode.DARK
        self.page.theme_mode = ft.ThemeMode.DARK if oscuro else ft.ThemeMode.LIGHT
        self.boton_tema.icon = ft.Icons.LIGHT_MODE_OUTLINED if oscuro else ft.Icons.DARK_MODE_OUTLINED
        self.boton_tema.tooltip = "Activar modo claro" if oscuro else "Activar modo oscuro"
        self.page.update()

    def _redimensionar(self, e=None):
        self.control.height = max(self.page.height or 960, 700)
        compacta = (self.page.width or 1280) < 1100
        if compacta != self.compacta:
            self.compacta = compacta
            self._dibujar_menu()
        self.page.update()
