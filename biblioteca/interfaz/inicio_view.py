"""Inicio del prototipo: cifras de muestra y accesos a recorridos disponibles."""

import flet as ft

from biblioteca.interfaz.componentes import PETROLEO, SECUNDARIO, SUAVE, TINTA, etiqueta, panel, titulo_pantalla


class InicioView:
    def __init__(self, datos, navegar, sede="Centro"):
        self.datos, self.navegar, self.sede = datos, navegar, sede
        self.control = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=24)
        self.actualizar(sede)

    def actualizar(self, sede):
        self.sede = sede
        cifras = [("Obras en catálogo", len(self.datos.obras), ft.Icons.AUTO_STORIES_OUTLINED, "Catálogo de toda la red", "Catálogo"),
                  ("Socios de la red", len(self.datos.socios), ft.Icons.PEOPLE_OUTLINE, "Administrar registros", "Socios"),
                  ("Copias disponibles", sum(o.cantidad_mostrada(sede) for o in self.datos.obras),
                   ft.Icons.INVENTORY_2_OUTLINED, f"Disponibilidad de muestra · {sede}", "Catálogo")]
        tarjetas = []
        for nombre, valor, icono, detalle, destino in cifras:
            tarjetas.append(ft.Container(panel(ft.Column([
                ft.Row([ft.Icon(icono, color=PETROLEO, size=23), ft.Container(expand=True),
                        ft.Icon(ft.Icons.NORTH_EAST, color=SECUNDARIO, size=17)]),
                ft.Text(str(valor), size=35, color=TINTA, weight=ft.FontWeight.W_600),
                ft.Text(nombre, color=TINTA, size=14, weight=ft.FontWeight.W_500),
                ft.Text(detalle, color=SECUNDARIO, size=12)], spacing=9)),
                col={"xs": 12, "md": 4}, on_click=lambda e, d=destino: self.navegar(d),
                tooltip=f"Abrir {destino}"))
        self.control.controls = [
            titulo_pantalla("Panel principal", "Información y accesos para el equipo de bibliotecas."),
            ft.Container(ft.Row([ft.Column([
                etiqueta("Red de Bibliotecas Horizonte"),
                ft.Text("Cada libro, en su lugar.", size=26, color=TINTA, weight=ft.FontWeight.W_600),
                ft.Text(f"Estás trabajando en Sede {sede}. El catálogo y los socios son de toda la red.",
                        size=13, color=SECUNDARIO)], spacing=12, expand=True),
                ft.FilledButton("Explorar catálogo", icon=ft.Icons.EAST,
                                on_click=lambda e: self.navegar("Catálogo"))], spacing=18),
                bgcolor=SUAVE, border_radius=12, padding=26),
            ft.ResponsiveRow(tarjetas, spacing=16, run_spacing=16),
            ft.Row([ft.Text("Accesos rápidos", size=18, color=TINTA, weight=ft.FontWeight.W_600),
                    ft.Container(expand=True), etiqueta("Datos de demostración", disponible=False)]),
            panel(ft.Column([
                ft.ListTile(leading=ft.Icon(ft.Icons.LIBRARY_BOOKS_OUTLINED, color=PETROLEO),
                            title=ft.Text("Explorar obras y disponibilidad", size=14),
                            subtitle=ft.Text("Buscar por título o autor y consultar una ficha.", size=12),
                            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT), on_click=lambda e: self.navegar("Catálogo")),
                ft.Divider(height=1),
                ft.ListTile(leading=ft.Icon(ft.Icons.PERSON_ADD_ALT_OUTLINED, color=PETROLEO),
                            title=ft.Text("Administrar socios", size=14),
                            subtitle=ft.Text("Revisar el listado y el formulario de registro.", size=12),
                            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT), on_click=lambda e: self.navegar("Socios"))], spacing=8), padding=8),
            panel(ft.Row([ft.Icon(ft.Icons.MOVING_OUTLINED, color=SECUNDARIO, size=28),
                          ft.Column([ft.Text("Circulación y logística", color=TINTA, weight=ft.FontWeight.W_500),
                                     ft.Text("Los indicadores de préstamos, reservas y remitos aparecerán al habilitar esos módulos.",
                                             color=SECUNDARIO, size=12)], expand=True, spacing=5),
                          etiqueta("Próximamente", disponible=False)], spacing=16)),
        ]
