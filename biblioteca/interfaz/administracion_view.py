"""Mecánica visual compartida: listado paginado y formulario con guardado único."""

import asyncio
import logging

import flet as ft

from biblioteca.errores import ErrorBiblioteca
from biblioteca.interfaz.componentes import PETROLEO, SECUNDARIO, panel, titulo_pantalla
from biblioteca.interfaz.lector_asincrono import ConsultaReemplazada

log = logging.getLogger(__name__)


def mensaje_error(error):
    if isinstance(error, ErrorBiblioteca):
        return str(error)
    log.error("Falló la administración", exc_info=(type(error), error, error.__traceback__))
    return "No se pudo completar la operación. Verificá la base e intentá nuevamente."


class FormularioAdministracion:
    def __init__(self, vista, titulo, campos, operacion, *, accion="Guardar"):
        self.vista, self.campos, self.operacion = vista, campos, operacion
        self.guardando, self.abierto = False, True
        self.error = ft.Text(color=ft.Colors.ERROR)
        self.guardar = ft.FilledButton(accion, on_click=self.enviar,
            style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=PETROLEO))
        self.cancelar = ft.TextButton("Cancelar", on_click=self.cerrar)
        self.dialogo = ft.AlertDialog(modal=True, title=ft.Text(titulo),
            content=ft.Container(ft.Column([*campos.values(), self.error], tight=True,
                spacing=16, scroll=ft.ScrollMode.AUTO), width=470,
                height=min(400, max(100, len(campos) * 76 + 60))),
            actions=[self.cancelar, self.guardar], on_dismiss=self._descartar)

    def _descartar(self, e=None):
        self.abierto = False

    def cerrar(self, e=None):
        if not self.guardando and self.abierto:
            self.abierto = False
            self.vista.page.pop_dialog()

    async def enviar(self, e=None):
        if self.guardando or not self.abierto or self.vista.cerrada:
            return
        self.guardando = True
        self.error.value = "Guardando…"
        self.guardar.disabled = self.cancelar.disabled = True
        for campo in self.campos.values():
            campo.disabled = True
        datos = {nombre: campo.value for nombre, campo in self.campos.items()}
        self.vista.page.update()
        try:
            await self.vista.escritor.ejecutar(self.operacion, **datos)
        except Exception as error:
            if self.abierto and not self.vista.cerrada:
                self.error.value = mensaje_error(error)
        else:
            if not self.vista.cerrada:
                if self.abierto:
                    self.abierto = False
                    self.vista.page.pop_dialog()
                # El commit ya terminó. Un error de refresco no vuelve a enviar el formulario.
                self.vista.aviso.value = "Cambios guardados."
                self.vista.page.update()
                await self.vista.refrescar_despues_de_guardar()
        finally:
            self.guardando = False
            if self.abierto and not self.vista.cerrada:
                self.guardar.disabled = self.cancelar.disabled = False
                for campo in self.campos.values():
                    campo.disabled = False
                self.vista.page.update()


class AdministracionView:
    TAMANO = 50

    def __init__(self, page, administracion, lector, escritor, entidad, titulo, descripcion,
                 nueva_etiqueta, al_guardar=None):
        self.page, self.administracion = page, administracion
        self.lector, self.escritor, self.entidad = lector, escritor, entidad
        self.al_guardar = al_guardar
        self.activa, self.cerrada = False, False
        self.revision, self.pagina, self.cargando = 0, 0, False
        self.registros = []
        self.formulario = None
        self.nuevo = ft.FilledButton(nueva_etiqueta, icon=ft.Icons.ADD,
            style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=PETROLEO),
            on_click=lambda e: self.abrir_formulario())
        self.busqueda = ft.TextField(label="Buscar por nombre", expand=True, on_change=self._buscar)
        # El TextField expandido necesita el ancho acotado de Row, no de Wrap.
        self.barra_filtros = ft.Row([self.busqueda])
        self.aviso = ft.Text(color=PETROLEO)
        self.resumen = ft.Text(color=SECUNDARIO, size=12)
        self.filas = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        self.anterior = ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Página anterior",
                                      disabled=True, on_click=lambda e: self._paginar(-1))
        self.siguiente = ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Página siguiente",
                                       disabled=True, on_click=lambda e: self._paginar(1))
        self.numero = ft.Text("1")
        self.control = ft.Column([
            titulo_pantalla(titulo, descripcion, self.nuevo), panel(self.barra_filtros), self.aviso,
            self.resumen, panel(self.filas, padding=8, expand=True),
            ft.Row([self.anterior, self.numero, self.siguiente], alignment=ft.MainAxisAlignment.END),
        ], expand=True, spacing=14)

    def activar(self, activa):
        self.activa = activa
        self.revision += 1
        if activa and not self.cerrada:
            self.page.run_task(self.cargar)

    def cerrar(self):
        self.cerrada = True
        self.activa = False
        self.revision += 1
        if self.formulario:
            self.formulario.abierto = False

    async def _buscar(self, e=None):
        await self.cargar(reiniciar=True, demora=0.3)

    async def _filtrar(self, e=None):
        await self.cargar(reiniciar=True)

    def _paginar(self, delta):
        if not self.cargando:
            self.pagina = max(0, self.pagina + delta)
            self.cargando = True
            self.page.run_task(self.cargar)

    def _vigente(self, revision):
        return self.activa and not self.cerrada and revision == self.revision

    def filtros(self):
        return {"nombre": self.busqueda.value or None}

    async def cargar(self, *, reiniciar=False, demora=0):
        self.revision += 1
        revision = self.revision
        if reiniciar:
            self.pagina = 0
        if not self._vigente(revision):
            return
        self.cargando = True
        self.anterior.disabled = self.siguiente.disabled = True
        self.resumen.value = "Cargando registros…"
        self.filas.controls = [ft.ProgressRing(width=26, height=26)]
        self.page.update()
        if demora:
            await asyncio.sleep(demora)
        if not self._vigente(revision):
            return
        try:
            # Una fila extra permite decidir Siguiente sin un COUNT adicional.
            registros = await self.lector.ejecutar(self.entidad, self.administracion.listar,
                self.entidad, **self.filtros(), limite=self.TAMANO + 1,
                desplazamiento=self.pagina * self.TAMANO)
        except ConsultaReemplazada:
            return
        except Exception as error:
            if self._vigente(revision):
                self.cargando = False
                self.resumen.value = "No se pudo leer el listado"
                self.filas.controls = [ft.Text(mensaje_error(error), color=ft.Colors.ERROR),
                    ft.TextButton("Reintentar lectura", on_click=lambda e: self.page.run_task(self.cargar))]
                self.page.update()
            return
        if not self._vigente(revision):
            return
        # Tras una modificación puede desaparecer la última fila de la página.
        if not registros and self.pagina:
            self.pagina -= 1
            await self.cargar()
            return
        self.cargando = False
        self.registros = registros[:self.TAMANO]
        self.anterior.disabled = self.pagina == 0
        self.siguiente.disabled = len(registros) <= self.TAMANO
        self.numero.value = str(self.pagina + 1)
        self.resumen.value = f"{len(self.registros)} registros en esta página · hasta {self.TAMANO} por página"
        self.filas.controls = [ft.Row([self.tabla(self.registros)], scroll=ft.ScrollMode.AUTO)] if self.registros else [
            ft.Container(ft.Text("No hay registros que coincidan con los filtros.", color=SECUNDARIO), padding=24)]
        self.page.update()

    async def refrescar_despues_de_guardar(self):
        if self.al_guardar:
            try:
                await self.al_guardar(self.entidad)
            except Exception as error:
                if not self.cerrada:
                    self.aviso.value = "Guardado confirmado; no se pudo actualizar la configuración: " + mensaje_error(error)
        await self.cargar()

    def mostrar_formulario(self, titulo, campos, operacion, **kwargs):
        if self.cerrada:
            return
        self.formulario = FormularioAdministracion(self, titulo, campos, operacion, **kwargs)
        self.page.show_dialog(self.formulario.dialogo)

    def confirmar(self, titulo, descripcion, accion, id):
        self.mostrar_formulario(titulo, {},
            lambda: self.administracion.ejecutar(self.entidad, accion, id))
        self.formulario.dialogo.content.content.controls.insert(0, ft.Text(descripcion))
        self.page.update()

    @staticmethod
    def construir_tabla(columnas, filas):
        return ft.DataTable(columns=[ft.DataColumn(ft.Text(t, size=11)) for t in columnas],
            rows=[ft.DataRow(cells=[ft.DataCell(c) for c in fila]) for fila in filas],
            column_spacing=22, heading_row_color=ft.Colors.SURFACE_CONTAINER_LOW,
            data_row_min_height=58, data_row_max_height=90)
