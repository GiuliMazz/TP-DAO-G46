"""Administración de sedes mediante sus servicios, sin traslados de inventario."""

from functools import partial

import flet as ft

from biblioteca.interfaz.administracion_view import AdministracionView
from biblioteca.interfaz.componentes import etiqueta, selector


class SedesLocalView(AdministracionView):
    def __init__(self, page, administracion, lector, escritor, al_guardar=None):
        super().__init__(page, administracion, lector, escritor, "sedes", "Sedes",
                         "Red de Bibliotecas Horizonte · baja lógica, sin eliminar existencias", "Nueva sede", al_guardar)
        self.estado = selector("Estado", ["Todas", "Activas", "Inactivas"], "Todas", self._filtrar)
        self.barra_filtros.controls.append(self.estado)

    def filtros(self):
        return {"nombre": self.busqueda.value or None,
                "activa": {"Todas": None, "Activas": True, "Inactivas": False}[self.estado.value]}

    def tabla(self, registros):
        return self.construir_tabla(("SEDE", "DIRECCIÓN", "CONTACTO / HORARIOS", "ESTADO", "ACCIONES"), [[
            ft.Text(s.nombre), ft.Text(s.direccion, width=180, max_lines=3),
            ft.Column([ft.Text(s.contacto, size=12), ft.Text(s.horarios, size=12)], spacing=3, tight=True),
            etiqueta("Activa" if s.activa else "Inactiva", disponible=s.activa),
            ft.Row([ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, tooltip=f"Editar sede {s.nombre}",
                on_click=lambda e, s=s: self.abrir_formulario(s)),
                ft.TextButton("Dar de baja" if s.activa else "Reactivar",
                    on_click=lambda e, s=s: self.confirmar(
                        "Cambiar estado de sede", f"Sede {s.nombre}. Se conservan sus ejemplares e historial.",
                        "dar_de_baja" if s.activa else "activar", s.id))]),
        ] for s in registros])

    def abrir_formulario(self, sede=None):
        campos = {nombre: ft.TextField(label=etiqueta_campo, value=getattr(sede, nombre) if sede else "",
                   autofocus=nombre == "nombre") for nombre, etiqueta_campo in (
                       ("nombre", "Nombre de sede"), ("direccion", "Dirección"),
                       ("contacto", "Contacto"), ("horarios", "Horarios de atención"))}
        operacion = partial(self.administracion.ejecutar, "sedes", "modificar", sede.id) if sede else partial(
            self.administracion.ejecutar, "sedes", "registrar")
        self.mostrar_formulario("Editar sede" if sede else "Nueva sede", campos, operacion)
