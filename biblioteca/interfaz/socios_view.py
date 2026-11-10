"""Administración de socios como prototipo de presentación, sin altas reales."""

import flet as ft

from biblioteca.interfaz.componentes import BORDE, PETROLEO, SECUNDARIO, TINTA, etiqueta, panel, selector, titulo_pantalla


class SociosView:
    def __init__(self, page, datos):
        self.page, self.datos = page, datos
        self.busqueda = ft.TextField(hint_text="Buscar nombre, DNI o contacto…", prefix_icon=ft.Icons.SEARCH,
                                     border_color=BORDE, border_radius=8, expand=True, text_size=14,
                                     on_change=lambda e: self._mostrar(actualizar=True))
        self.estado = selector("Estado", ["Todos", "Habilitados", "Inhabilitados"], "Todos",
                               lambda e: self._mostrar(actualizar=True), width=180)
        self.filas = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)
        self.resumen = ft.Text(size=12, color=SECUNDARIO)
        self.control = ft.Column([
            titulo_pantalla("Socios", "Registros de toda la red, identificados por DNI.",
                            ft.FilledButton("Nuevo socio", icon=ft.Icons.PERSON_ADD_ALT_1,
                                            on_click=lambda e: self.abrir_formulario())),
            panel(ft.Row([self.busqueda, self.estado], spacing=14)),
            self.resumen,
            panel(self.filas, padding=8, expand=True),
            ft.Text("Datos ficticios para revisar el diseño. El formulario todavía no registra cambios.", size=12, color=SECUNDARIO),
        ], expand=True, spacing=18)
        self._mostrar()

    def _mostrar(self, actualizar=False):
        socios = self.datos.buscar_socios(self.busqueda.value, self.estado.value)
        self.resumen.value = f"{len(socios)} {'socio' if len(socios) == 1 else 'socios'} · datos de demostración"
        tabla = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(t)) for t in ("SOCIO", "DNI", "CONTACTO", "ESTADO", "")],
            rows=[ft.DataRow(cells=[
                ft.DataCell(ft.Row([ft.CircleAvatar(content=ft.Text("".join(p[0] for p in s.nombre.split()[:2]), size=12),
                                                    radius=17, bgcolor=ft.Colors.PRIMARY_CONTAINER, color=PETROLEO),
                                    ft.Text(s.nombre, color=TINTA, size=13)], spacing=10)),
                ft.DataCell(ft.Text(s.dni, size=13)), ft.DataCell(ft.Text(s.contacto, size=12, color=SECUNDARIO)),
                ft.DataCell(etiqueta("Habilitado" if s.habilitado else "Inhabilitado", disponible=s.habilitado)),
                ft.DataCell(ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_size=19,
                                         tooltip=f"Ver formulario de {s.nombre}", on_click=lambda e, s=s: self.abrir_formulario(s))),
            ]) for s in socios], heading_row_color=ft.Colors.SURFACE_CONTAINER_LOW, column_spacing=26,
            heading_row_height=44, data_row_min_height=64, show_checkbox_column=False)
        self.filas.controls = [ft.Row([tabla], scroll=ft.ScrollMode.AUTO)] if socios else [
            ft.Container(ft.Text("No hay socios que coincidan con la búsqueda.", color=SECUNDARIO), padding=24)]
        if actualizar:
            self.page.update()

    def abrir_formulario(self, socio=None):
        campos = [ft.TextField(label="Nombre y apellido", value=socio.nombre if socio else "", autofocus=True),
                  ft.TextField(label="DNI", value=socio.dni if socio else "", keyboard_type=ft.KeyboardType.NUMBER),
                  ft.TextField(label="Contacto", value=socio.contacto if socio else "")]
        self.page.show_dialog(ft.AlertDialog(modal=True, title=ft.Text("Socio · formulario de muestra"),
            content=ft.Container(ft.Column([
                ft.Text("Revisá los campos y su disposición. Los cambios se descartan al cerrar.", size=13, color=SECUNDARIO),
                *campos,
                etiqueta("Sin guardado en este prototipo", disponible=False),
            ], spacing=20, tight=True, scroll=ft.ScrollMode.AUTO), width=440),
            actions=[ft.TextButton("Cerrar formulario", on_click=lambda e: self.page.pop_dialog())]))
