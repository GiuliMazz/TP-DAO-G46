"""Catálogo de muestra: estado visual y filtros locales, sin SQL ni préstamos."""

import asyncio

import flet as ft

from biblioteca.interfaz.componentes import (
    BORDE, PETROLEO, SECUNDARIO, TINTA, etiqueta, estado_vacio, panel, selector, titulo_pantalla,
)
from biblioteca.interfaz.datos_prototipo import SEDES


class CatalogoView:
    TAMANO_PAGINA = 24

    def __init__(self, page, datos):
        self.page, self.datos = page, datos
        self.pagina = 0
        self.tabla = False
        self._revision = 0
        self._activa = True
        self.busqueda = ft.TextField(hint_text="Buscar título original, título en español o autor…",
                                    prefix_icon=ft.Icons.SEARCH, on_change=self._buscar,
                                    on_submit=self._filtrar, expand=True, text_size=14,
                                    border_color=BORDE, border_radius=8, content_padding=14)
        self.genero = selector("Género", ["Todos", "Fantasía", "Fantasía épica"], "Todos", self._filtrar)
        self.sede = selector("Sede", ["Todas", *SEDES], "Todas", self._filtrar, width=145)
        self.disponibilidad = selector("Disponibilidad", ["Todas", "Disponibles", "Sin disponibles"],
                                      "Todas", self._filtrar, width=190)
        self.resumen = ft.Text(size=13, color=SECUNDARIO)
        self.resultados = ft.Container(expand=True)
        self.contador = ft.Text(size=12, color=SECUNDARIO)
        self.anterior = ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Página anterior",
                                      on_click=lambda e: self._paginar(-1))
        self.siguiente = ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Página siguiente",
                                       on_click=lambda e: self._paginar(1))
        self.numero = ft.Text("1", color=TINTA, size=13)
        self.boton_cuadricula = ft.IconButton(icon=ft.Icons.GRID_VIEW_OUTLINED, tooltip="Vista de portadas",
                                             on_click=lambda e: self._cambiar_vista(False))
        self.boton_tabla = ft.IconButton(icon=ft.Icons.VIEW_LIST_OUTLINED, tooltip="Vista de tabla",
                                        on_click=lambda e: self._cambiar_vista(True))
        self.control = ft.Column([
            titulo_pantalla("Catálogo bibliográfico", "Explorá las obras y su disponibilidad en la red."),
            panel(ft.Column([self.busqueda,
                ft.Row([self.genero, self.sede, self.disponibilidad,
                        ft.TextButton("Limpiar filtros", on_click=self._limpiar)], wrap=True, spacing=12)], spacing=14), padding=18),
            ft.Row([self.resumen, ft.Container(expand=True), self.boton_cuadricula, self.boton_tabla], spacing=4),
            self.resultados,
            ft.Row([self.contador, ft.Container(expand=True), self.anterior, self.numero, self.siguiente], spacing=6),
        ], expand=True, spacing=16)
        self._mostrar()

    async def _buscar(self, e):
        self._revision += 1
        revision = self._revision
        await asyncio.sleep(0.3)
        if self._activa and revision == self._revision:
            self.pagina = 0
            self._mostrar()
            self.page.update()

    def activar(self, activa):
        self._activa = activa
        self._revision += 1
        if activa:
            self._mostrar()

    def _filtrar(self, e=None):
        self._revision += 1
        self.pagina = 0
        self._mostrar()
        self.page.update()

    def _limpiar(self, e=None):
        self.busqueda.value = ""
        self.genero.value, self.sede.value, self.disponibilidad.value = "Todos", "Todas", "Todas"
        self._filtrar()

    def _cambiar_vista(self, tabla):
        self.tabla = tabla
        self._mostrar()
        self.page.update()

    def _paginar(self, delta):
        self.pagina = max(0, self.pagina + delta)
        self._mostrar()
        self.page.update()

    def _mostrar(self):
        obras = self.datos.buscar_obras(self.busqueda.value, self.genero.value,
                                        self.sede.value, self.disponibilidad.value)
        self.pagina = min(self.pagina, max(0, (len(obras) - 1) // self.TAMANO_PAGINA))
        inicio = self.pagina * self.TAMANO_PAGINA
        visibles = obras[inicio:inicio + self.TAMANO_PAGINA]
        self.resumen.value = f"{len(obras)} {'obra' if len(obras) == 1 else 'obras'} · datos de demostración"
        self.contador.value = (f"{inicio + 1}–{inicio + len(visibles)} de {len(obras)} · 24 por página"
                               if visibles else "Sin resultados")
        self.numero.value = str(self.pagina + 1)
        self.anterior.disabled = self.pagina == 0
        self.siguiente.disabled = inicio + len(visibles) >= len(obras)
        self.boton_cuadricula.bgcolor = None if self.tabla else ft.Colors.PRIMARY_CONTAINER
        self.boton_tabla.bgcolor = ft.Colors.PRIMARY_CONTAINER if self.tabla else None
        self._dibujar_resultados(visibles)

    def _dibujar_resultados(self, visibles):
        """Render compartido por la maqueta explícita y el catálogo conectado."""
        if not visibles:
            self.resultados.content = estado_vacio("No encontramos obras", "Probá con otro título, autor o combinación de filtros.")
        elif self.tabla:
            self.resultados.content = panel(ft.Column([ft.Row([ft.DataTable(
                columns=[ft.DataColumn(ft.Text(t)) for t in ("OBRA", "AUTOR", "GÉNERO", "DISPONIBILIDAD", "")],
                rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(o.titulo, size=13)),
                       ft.DataCell(ft.Text(o.autor, size=12)), ft.DataCell(ft.Text(o.genero, size=12)),
                       ft.DataCell(self._estado(o)), ft.DataCell(ft.TextButton("Ver ficha", on_click=lambda e, o=o: self.abrir_ficha(o)))])
                      for o in visibles], column_spacing=22, heading_row_height=42, data_row_min_height=60,
                heading_row_color=ft.Colors.SURFACE_CONTAINER_LOW, show_checkbox_column=False)], scroll=ft.ScrollMode.AUTO)],
                scroll=ft.ScrollMode.AUTO, expand=True), padding=8, expand=True)
        else:
            self.resultados.content = ft.GridView(controls=[self._tarjeta(o) for o in visibles],
                max_extent=340, child_aspect_ratio=0.65, spacing=18, run_spacing=18,
                build_controls_on_demand=True, padding=0, expand=True)

    def _estado(self, obra):
        cantidad = obra.cantidad_mostrada(self.sede.value)
        return etiqueta(f"{cantidad} disponibles" if cantidad else "Sin disponibles", disponible=cantidad > 0)

    @staticmethod
    def portada(obra):
        return ft.Container(ft.Stack([
            ft.Container(width=160, height=160, border_radius=80, border=ft.Border.all(1, obra.acento),
                         right=-35, top=32, opacity=0.35),
            ft.Container(width=120, height=120, border_radius=60, border=ft.Border.all(1, obra.acento),
                         right=-15, top=52, opacity=0.35),
            ft.Container(ft.Column([
                ft.Text(obra.autor.upper(), size=11, color=obra.acento, weight=ft.FontWeight.W_500),
                ft.Container(expand=True),
                ft.Icon(ft.Icons.AUTO_STORIES_OUTLINED, size=44, color=obra.acento),
                ft.Text(obra.titulo, size=26, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600, max_lines=4),
                ft.Container(height=8),
                ft.Text("PORTADA ILUSTRATIVA", size=8, color=obra.acento)], spacing=12), padding=24),
        ], expand=True), bgcolor=obra.color, expand=True, clip_behavior=ft.ClipBehavior.HARD_EDGE,
            border_radius=ft.BorderRadius.only(top_left=11, top_right=11))

    def _tarjeta(self, obra):
        cubierta = self.portada(obra)
        cubierta.on_click = lambda e: self.abrir_ficha(obra)
        cubierta.tooltip = f"Abrir ficha de {obra.titulo}"
        return ft.Container(ft.Column([cubierta,
            ft.Container(ft.Column([
                ft.Text(obra.titulo, size=15, color=TINTA, weight=ft.FontWeight.W_600,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=obra.titulo),
                ft.Text(obra.autor, size=12, color=SECUNDARIO, max_lines=1),
                ft.Row([self._estado(obra), ft.Container(expand=True),
                        ft.TextButton("Ver ficha", on_click=lambda e: self.abrir_ficha(obra))], spacing=2)
            ], spacing=5), padding=ft.Padding.symmetric(horizontal=14, vertical=10))], spacing=0, expand=True),
            bgcolor=ft.Colors.SURFACE, border=ft.Border.all(1, BORDE), border_radius=12, clip_behavior=ft.ClipBehavior.HARD_EDGE)

    def abrir_ficha(self, obra):
        cubierta = self.portada(obra)
        cubierta.expand = None
        cubierta.width, cubierta.height = 190, 275
        detalle = ft.Column([
            ft.Text(obra.titulo, color=TINTA, size=23, weight=ft.FontWeight.W_600),
            ft.Text(obra.autor, size=15, color=SECUNDARIO),
            ft.Text(f"Título original: {obra.original}", size=12, color=SECUNDARIO),
            ft.Row([etiqueta(obra.genero), etiqueta("Español", disponible=False)], wrap=True),
            ft.Text("Sobre esta obra", color=TINTA, weight=ft.FontWeight.W_600),
            ft.Text(obra.descripcion, size=13, color=SECUNDARIO),
        ], spacing=12, expand=True)
        self.page.show_dialog(ft.AlertDialog(title=ft.Text("Ficha de obra"), modal=True,
            content=ft.Container(ft.Column([
                ft.Row([cubierta, detalle], spacing=24, vertical_alignment=ft.CrossAxisAlignment.START),
                ft.Divider(), ft.Text("Disponibilidad de muestra por sede", weight=ft.FontWeight.W_500, color=TINTA),
                ft.Row([etiqueta(f"{sede}: {obra.cantidad_mostrada(sede)} disponibles",
                                disponible=obra.cantidad_mostrada(sede) > 0) for sede in SEDES], wrap=True),
                ft.Text("Cantidades, sinopsis y portada ilustrativas. No representan existencias reales.", size=11, color=SECUNDARIO),
            ], spacing=16, scroll=ft.ScrollMode.AUTO, tight=True), width=680),
            actions=[ft.TextButton("Cerrar ficha", on_click=lambda e: self.page.pop_dialog())]))
