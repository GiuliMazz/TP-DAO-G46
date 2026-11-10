"""Catálogo conectado: presentación asíncrona, sin SQL ni reglas de circulación."""

import asyncio
from dataclasses import dataclass
import logging

import flet as ft

from biblioteca.consultas_locales import ConsultasCatalogoLocal
from biblioteca.errores import ErrorBiblioteca
from biblioteca.interfaz.catalogo_view import CatalogoView
from biblioteca.interfaz.componentes import SECUNDARIO, TINTA, etiqueta, panel
from biblioteca.interfaz.lector_asincrono import ConsultaReemplazada
from biblioteca.interfaz.portadas import portada_ilustrativa
from biblioteca.resultados_catalogo import EntradaCatalogo

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LibroPagina:
    entrada: EntradaCatalogo

    @property
    def titulo(self):
        return self.entrada.ficha.titulo_mostrado

    @property
    def autor(self):
        return "; ".join(self.entrada.ficha.autores)

    @property
    def genero(self):
        return ", ".join(self.entrada.generos) or "Sin género aprobado"

    def cantidad_mostrada(self, sede):
        # La consulta ya aplicó el alcance elegido, antes de paginar.
        return self.entrada.disponibles


class CatalogoLocalView(CatalogoView):
    def __init__(self, page, consultas, lector):
        self.consultas, self.lector = consultas, lector
        self._pagina_resultado = None
        self._configurada = False
        self._cerrada = False
        self._cargando = False
        self._revision_ficha = 0
        self._tipo = ""
        self.al_inventario = None
        self._generos, self._sedes = {}, {}
        super().__init__(page, None)
        self.sede.label = "Disponibilidad en sede"
        self.sede.width = 205
        self.genero.options = [ft.DropdownOption(key="Todos", text="Todos")]
        self.sede.options = [ft.DropdownOption(key="Todas", text="Toda la red")]
        self.control.controls.insert(2, ft.Text(
            "La sede limita las cantidades; elegí Disponibles para exigir stock local. La ficha muestra toda la red.",
            size=12, color=SECUNDARIO))

    def configurar(self, configuracion):
        self._tipo = configuracion.tipo
        self._generos = {str(g.id): g.nombre for g in configuracion.generos}
        self._sedes = {str(s.id): s.nombre for s in configuracion.sedes}
        self.genero.options = [ft.DropdownOption(key="Todos", text="Todos"), *[
            ft.DropdownOption(key=id, text=nombre) for id, nombre in self._generos.items()]]
        self.sede.options = [ft.DropdownOption(key="Todas", text="Toda la red"), *[
            ft.DropdownOption(key=id, text=nombre) for id, nombre in self._sedes.items()]]
        self._configurada = True

    def activar(self, activa):
        self._activa = activa
        self._revision += 1
        self._revision_ficha += 1
        if activa and self._configurada and not self._cerrada:
            self.page.run_task(self.cargar)

    def cerrar(self):
        self._cerrada = True
        self._activa = False
        self._revision += 1
        self._revision_ficha += 1

    async def _buscar(self, e=None):
        await self.cargar(reiniciar=True, demora=0.3)

    async def _filtrar(self, e=None):
        await self.cargar(reiniciar=True)

    async def _limpiar(self, e=None):
        self.busqueda.value = ""
        self.genero.value, self.sede.value, self.disponibilidad.value = "Todos", "Todas", "Todas"
        await self._filtrar()

    def _paginar(self, delta):
        if not self._cargando:
            self.pagina = max(0, self.pagina + delta)
            self._cargando = True
            self.page.run_task(self.cargar)

    def _cambiar_vista(self, tabla):
        self.tabla = tabla
        if not self._cargando:
            self._mostrar()
        self.page.update()

    def _vigente(self, revision):
        return not self._cerrada and self._activa and revision == self._revision

    async def cargar(self, *, reiniciar=False, demora=0):
        self._revision += 1
        revision = self._revision
        if reiniciar:
            self.pagina = 0
        if not self._activa or self._cerrada or not self._configurada:
            return
        self._cargando = True
        self.anterior.disabled = self.siguiente.disabled = True
        self.contador.value = ""
        self.resumen.value = "Buscando…" if demora else "Cargando catálogo…"
        self.resultados.content = ft.Container(ft.Column([ft.ProgressRing(width=28, height=28),
            ft.Text(self.resumen.value, color=SECUNDARIO)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
            expand=True, alignment=ft.Alignment.CENTER)
        self.page.update()
        if demora:
            await asyncio.sleep(demora)
        if not self._vigente(revision):
            return
        filtros = dict(texto=self.busqueda.value or None,
            genero_id=self.genero.value if self.genero.value != "Todos" else None,
            sede_id=self.sede.value if self.sede.value != "Todas" else None,
            disponibles={"Todas": None, "Disponibles": True, "Sin disponibles": False}[self.disponibilidad.value],
            limite=self.TAMANO_PAGINA, desplazamiento=self.pagina * self.TAMANO_PAGINA)
        try:
            resultado = await self.lector.ejecutar("catalogo", self.consultas.consultar_pagina, **filtros)
        except ConsultaReemplazada:
            return
        except Exception as error:
            if self._vigente(revision):
                self._cargando = False
                self._pagina_resultado = None
                self.resumen.value = "No se pudo cargar el catálogo"
                self.contador.value = ""
                self.resultados.content = self._error(error, lambda e: self.page.run_task(self.cargar))
                self.page.update()
            return
        if self._vigente(revision):
            self._pagina_resultado = resultado
            self._cargando = False
            self._mostrar()
            self.page.update()

    def _mostrar(self):
        resultado = self._pagina_resultado
        if resultado is None:
            self.anterior.disabled = self.siguiente.disabled = True
            return
        inicio, cantidad = resultado.desplazamiento, len(resultado.obras)
        naturaleza = "datos sintéticos" if self._tipo == "RENDIMIENTO" else "bibliografía real"
        self.resumen.value = f"{resultado.total} {'obra' if resultado.total == 1 else 'obras'} · {naturaleza}"
        self.contador.value = (f"{inicio + 1}–{inicio + cantidad} de {resultado.total} · 24 por página"
                               if cantidad else "Sin resultados")
        self.numero.value = str(self.pagina + 1)
        self.anterior.disabled = inicio == 0
        self.siguiente.disabled = inicio + cantidad >= resultado.total
        self.boton_cuadricula.bgcolor = None if self.tabla else ft.Colors.PRIMARY_CONTAINER
        self.boton_tabla.bgcolor = ft.Colors.PRIMARY_CONTAINER if self.tabla else None
        self._dibujar_resultados([LibroPagina(entrada) for entrada in resultado.obras])

    @staticmethod
    def portada(obra):
        src = ConsultasCatalogoLocal.portada_local(obra.entrada.portada_edicion_id)
        ausente = portada_ilustrativa(obra.titulo, obra.autor)
        contenido = ft.Image(src=src, fit=ft.BoxFit.CONTAIN, expand=True,
                            error_content=ausente, semantics_label=f"Portada de {obra.titulo}") if src else ausente
        return ft.Container(contenido, expand=True, alignment=ft.Alignment.CENTER,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, padding=8)

    def abrir_ficha(self, obra):
        self.page.run_task(self._abrir_ficha, obra)

    async def _abrir_ficha(self, obra):
        self._revision_ficha += 1
        revision = self._revision_ficha
        contenedor = ft.Container(ft.Row([ft.ProgressRing(width=24, height=24), ft.Text("Cargando ficha…")]), width=680)
        def cerrar(e=None):
            self._revision_ficha += 1
            self.page.pop_dialog()
        dialogo = ft.AlertDialog(title=ft.Text("Ficha de obra"), modal=True, content=contenedor,
            on_dismiss=lambda e: self._invalidar_ficha(),
            actions=[ft.TextButton("Cerrar ficha", on_click=cerrar)])
        self.page.show_dialog(dialogo)

        async def completar():
            try:
                ficha = await self.lector.ejecutar("ficha", self.consultas.ficha, obra.entrada.ficha.id)
            except ConsultaReemplazada:
                return
            except Exception as error:
                if self._ficha_vigente(revision):
                    contenedor.content = self._error(error, lambda e: self.page.run_task(completar))
                    self.page.update()
                return
            if self._ficha_vigente(revision):
                contenedor.content = self._contenido_ficha(obra, ficha)
                self.page.update()
        await completar()

    def _invalidar_ficha(self):
        self._revision_ficha += 1

    def _ficha_vigente(self, revision):
        return not self._cerrada and self._activa and self._revision_ficha == revision

    def _contenido_ficha(self, obra, ficha):
        detalle = ficha.detalle
        cubierta = self.portada(obra)
        cubierta.expand = None
        cubierta.width, cubierta.height = 160, 230
        descripcion = ((detalle.edicion_preferida.descripcion_es if detalle.edicion_preferida else None)
                       or detalle.obra.descripcion_original)
        textos = [ft.Text(detalle.titulo_mostrado, size=22, color=TINTA, weight=ft.FontWeight.W_600),
                  ft.Text("; ".join(a.nombre for a in detalle.autores), size=14, color=SECUNDARIO),
                  ft.Text(f"Título de obra: {detalle.obra.titulo_original}", size=12, color=SECUNDARIO),
                  ft.Text("Español · edición seleccionada", size=12, color=SECUNDARIO),
                  ft.Text("Sinopsis de la edición" if detalle.edicion_preferida and detalle.edicion_preferida.descripcion_es
                          else "Descripción de la fuente (puede estar en otro idioma)", size=12, color=SECUNDARIO),
                  ft.Text(descripcion or "Sin sinopsis disponible.", size=13, color=SECUNDARIO)]
        nombres = {"GENERO": "Género", "ETIQUETA": "Tema", "PUBLICO": "Público"}
        clases = [etiqueta(f"{nombres[c.termino.tipo.value]}: {c.termino.nombre}") for c in ficha.clasificaciones]
        ediciones = [ft.Text(f"{e.titulo} · {e.editorial or 'Editorial no informada'} · "
                            f"{e.anio_publicacion or 'Año no informado'}\n"
                            f"ISBN: {e.isbn_13 or e.isbn_10 or 'No informado'} · {e.id_openlibrary or 'Alta local'}",
                            size=12, color=SECUNDARIO) for e in ficha.ediciones]
        tabla = ft.DataTable(columns=[ft.DataColumn(ft.Text(t, size=11)) for t in
                ("SEDE", "PROPIOS", "UBICADOS", "DISPONIBLES")],
            rows=[ft.DataRow(cells=[ft.DataCell(ft.Text(f.nombre_sede + (" (inactiva)" if not f.sede_activa else ""))),
                  *[ft.DataCell(ft.Text(str(n))) for n in (f.total_propios, f.total_ubicados, f.disponibles)]])
                  for f in ficha.existencias], column_spacing=20)
        return ft.Column([
            ft.Row([cubierta, ft.Column(textos, expand=True, spacing=10)], spacing=20,
                   vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row(clases, wrap=True) if clases else ft.Text("Sin clasificaciones aprobadas.", color=SECUNDARIO),
            ft.Divider(), ft.Text("Ediciones españolas", weight=ft.FontWeight.W_600), *ediciones,
            ft.Divider(), ft.Text("Existencias por sede", weight=ft.FontWeight.W_600),
            ft.Row([tabla], scroll=ft.ScrollMode.AUTO),
            *([ft.FilledButton("Administrar ejemplares", icon=ft.Icons.INVENTORY_2_OUTLINED,
                on_click=lambda e: self.al_inventario(obra, ficha))] if self.al_inventario else []),
            ft.Text("Propiedad, ubicación física y disponibilidad son datos distintos. "
                    + ("Las existencias de esta base son ficticias para demostración." if self._tipo == "DEMOSTRACION" else
                       "Bibliografía y existencias sintéticas para medir rendimiento." if self._tipo == "RENDIMIENTO" else
                       "Datos de la base operativa seleccionada."), size=12, color=SECUNDARIO),
        ], scroll=ft.ScrollMode.AUTO, spacing=14, tight=True)

    @staticmethod
    def _error(error, reintentar):
        if not isinstance(error, ErrorBiblioteca):
            log.error("Falló una lectura del catálogo", exc_info=(type(error), error, error.__traceback__))
        mensaje = str(error) if isinstance(error, ErrorBiblioteca) else "La consulta no pudo completarse. Intentá nuevamente."
        return panel(ft.Column([ft.Text(mensaje, color=TINTA), ft.TextButton("Reintentar", on_click=reintentar)]))
