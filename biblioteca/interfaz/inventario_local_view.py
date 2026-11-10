"""Inventario de una obra: altas, condición física y baja mediante servicios."""

from functools import partial

import flet as ft

from biblioteca.dominio.ejemplar import CondicionFisica, SituacionOperativa
from biblioteca.interfaz.administracion_view import AdministracionView
from biblioteca.interfaz.componentes import SECUNDARIO, selector


class InventarioLocalView(AdministracionView):
    def __init__(self, page, administracion, lector, escritor, al_guardar=None):
        super().__init__(page, administracion, lector, escritor, "inventario", "Ejemplares",
                         "Propiedad estable · ubicación física independiente", "Registrar ejemplar", al_guardar)
        self.obra_id = None
        self.ediciones, self.sedes = (), ()
        self.busqueda.visible = False
        self.sede = selector("Ubicación actual", ["Todas"], "Todas", self._filtrar, width=210)
        self.barra_filtros.controls.append(self.sede)
        self.nuevo.disabled = True
        self.contexto = ft.Text(color=SECUNDARIO, selectable=True)
        self.control.controls.insert(1, self.contexto)

    def configurar(self, obra_id, titulo, ediciones, sedes):
        cambio_obra = self.obra_id != obra_id
        self.obra_id, self.ediciones, self.sedes = obra_id, tuple(ediciones), tuple(sedes)
        self.contexto.value = titulo
        self.nuevo.disabled = not self.ediciones or not any(s.activa for s in self.sedes)
        ids = {"Todas", *(str(s.id) for s in self.sedes)}
        self.sede.options = [ft.DropdownOption(key="Todas", text="Toda la red"), *[
            ft.DropdownOption(key=str(s.id), text=s.nombre + (" (inactiva)" if not s.activa else "")) for s in self.sedes]]
        if cambio_obra or self.sede.value not in ids:
            self.sede.value = "Todas"
            self.pagina = 0

    def filtros(self):
        return {"obra_id": self.obra_id,
                "sede_actual_id": self.sede.value if self.sede.value != "Todas" else None}

    def tabla(self, registros):
        sedes = {s.id: s.nombre for s in self.sedes}
        ediciones = {e.id: f"{e.titulo} · {e.id_openlibrary or 'Edición local'}" for e in self.ediciones}
        condicion = {"APTO": "Apto", "DANIADO": "Dañado", "DESTRUIDO": "Destruido"}
        return self.construir_tabla(("CÓDIGO", "EDICIÓN", "PROPIETARIA", "UBICACIÓN", "CONDICIÓN", "SITUACIÓN", "ACCIONES"), [[
            ft.Text(e.codigo_inventario), ft.Text(ediciones.get(e.edicion_id, str(e.edicion_id)), width=210, max_lines=3),
            ft.Text(sedes.get(e.sede_propietaria_id, str(e.sede_propietaria_id))),
            ft.Text(sedes.get(e.sede_actual_id, "Sin ubicación")),
            ft.Text(condicion[e.condicion_fisica.value]), ft.Text(e.situacion_operativa.value),
            ft.Row([
                ft.TextButton("Condición", tooltip=f"Cambiar condición de {e.codigo_inventario}",
                    on_click=lambda evento, ejemplar=e: self.abrir_condicion(ejemplar)),
                ft.TextButton("Dar de baja", tooltip=f"Dar de baja {e.codigo_inventario}",
                    disabled=e.situacion_operativa is SituacionOperativa.BAJA,
                    on_click=lambda evento, ejemplar=e: self.confirmar(
                        f"Dar de baja {ejemplar.codigo_inventario}",
                        "Se conserva el registro y su código. Dejará de estar disponible; cambiar su condición física no lo reactivará.",
                        "dar_de_baja", ejemplar.id)),
            ], spacing=0),
        ] for e in registros])

    def abrir_condicion(self, ejemplar):
        nombres = {CondicionFisica.APTO: "Apto", CondicionFisica.DANIADO: "Dañado",
                   CondicionFisica.DESTRUIDO: "Destruido"}
        campo = ft.Dropdown(label="Condición física", value=ejemplar.condicion_fisica.value,
            options=[ft.DropdownOption(key=c.value, text=nombres[c]) for c in CondicionFisica])

        def guardar(condicion):
            return self.administracion.ejecutar("inventario", "registrar_condicion",
                                               ejemplar.id, CondicionFisica(condicion))

        self.mostrar_formulario(f"Condición de {ejemplar.codigo_inventario}", {"condicion": campo}, guardar)
        self.formulario.dialogo.content.content.controls.insert(0, ft.Text(
            "Destruido es irreversible. Cambiar la condición no modifica la situación operativa, la propietaria ni la ubicación.",
            color=SECUNDARIO, size=12))
        self.formulario.dialogo.content.height = 220
        self.page.update()

    def abrir_formulario(self):
        if self.nuevo.disabled:
            return
        activas = [s for s in self.sedes if s.activa]
        edicion = ft.Dropdown(label="Edición española", value=str(self.ediciones[0].id),
            options=[ft.DropdownOption(key=str(e.id), text=f"{e.titulo} · {e.isbn_13 or e.isbn_10 or e.id_openlibrary or 'Sin ISBN'}")
                     for e in self.ediciones])
        sede = ft.Dropdown(label="Sede propietaria y ubicación inicial", value=str(activas[0].id),
            options=[ft.DropdownOption(key=str(s.id), text=s.nombre) for s in activas])
        campos = {"codigo_inventario": ft.TextField(label="Código de inventario", autofocus=True),
                  "edicion_id": edicion, "sede_id": sede}
        self.mostrar_formulario("Registrar ejemplar físico", campos,
            partial(self.administracion.ejecutar, "inventario", "registrar"))
