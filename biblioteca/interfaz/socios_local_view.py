"""Socios reales: presentación y llamadas a los servicios de la red."""

from functools import partial

import flet as ft

from biblioteca.dominio.socio import EstadoSocio
from biblioteca.interfaz.administracion_view import AdministracionView
from biblioteca.interfaz.componentes import etiqueta, selector


class SociosLocalView(AdministracionView):
    def __init__(self, page, administracion, lector, escritor, al_guardar=None):
        super().__init__(page, administracion, lector, escritor, "socios", "Socios",
                         "Registros de toda la red · identificación mediante DNI", "Nuevo socio", al_guardar)
        self.busqueda.label = "Buscar nombre, DNI o contacto"
        self.estado = selector("Estado", ["Todos", "Habilitados", "Inhabilitados"], "Todos", self._filtrar)
        self.barra_filtros.controls.append(self.estado)

    def filtros(self):
        return {"texto": self.busqueda.value or None,
                "estado": {"Todos": None, "Habilitados": EstadoSocio.HABILITADO,
                           "Inhabilitados": EstadoSocio.INHABILITADO}[self.estado.value]}

    def tabla(self, registros):
        return self.construir_tabla(("SOCIO", "DNI", "CONTACTO", "ESTADO", "ACCIONES"), [[
            ft.Text(s.nombre_completo), ft.Text(s.documento), ft.Text(s.contacto),
            etiqueta("Habilitado" if s.esta_habilitado() else "Inhabilitado", disponible=s.esta_habilitado()),
            ft.Row([ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, tooltip=f"Editar socio {s.nombre_completo}",
                on_click=lambda e, s=s: self.abrir_formulario(s)),
                ft.TextButton("Inhabilitar" if s.esta_habilitado() else "Habilitar",
                    on_click=lambda e, s=s: self.confirmar(
                        "Cambiar habilitación", f"{s.nombre_completo} · DNI {s.documento}",
                        "inhabilitar" if s.esta_habilitado() else "habilitar", s.id))]),
        ] for s in registros])

    def abrir_formulario(self, socio=None):
        campos = {
            "nombre_completo": ft.TextField(label="Nombre y apellido", value=socio.nombre_completo if socio else "", autofocus=True),
            "documento": ft.TextField(label="DNI", value=socio.documento if socio else ""),
            "contacto": ft.TextField(label="Contacto", value=socio.contacto if socio else ""),
        }
        operacion = partial(self.administracion.ejecutar, "socios", "modificar", socio.id) if socio else partial(
            self.administracion.ejecutar, "socios", "registrar")
        self.mostrar_formulario("Editar socio" if socio else "Nuevo socio", campos, operacion)
