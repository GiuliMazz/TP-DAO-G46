"""Estilos y componentes visuales compartidos por las tres vistas de muestra."""

import flet as ft

SEMILLA = "#176477"
PETROLEO = ft.Colors.PRIMARY
TINTA = ft.Colors.ON_SURFACE
SECUNDARIO = ft.Colors.ON_SURFACE_VARIANT
FONDO = ft.Colors.SURFACE_CONTAINER_LOW
SUPERFICIE = ft.Colors.SURFACE
BORDE = ft.Colors.OUTLINE_VARIANT
SUAVE = ft.Colors.PRIMARY_CONTAINER


def etiqueta(texto, *, disponible=True):
    return ft.Container(ft.Text(texto, size=12, color=ft.Colors.ON_TERTIARY_CONTAINER if disponible else SECUNDARIO,
                                 weight=ft.FontWeight.W_500),
                        bgcolor=ft.Colors.TERTIARY_CONTAINER if disponible else ft.Colors.SURFACE_CONTAINER_HIGHEST, border_radius=6,
                        padding=ft.Padding.symmetric(horizontal=9, vertical=5))


def titulo_pantalla(titulo, descripcion, accion=None):
    return ft.Row([ft.Column([ft.Text(titulo, size=27, weight=ft.FontWeight.W_600, color=TINTA),
                              ft.Text(descripcion, size=13, color=SECUNDARIO)], spacing=5, expand=True),
                   *([accion] if accion is not None else [])], vertical_alignment=ft.CrossAxisAlignment.CENTER)


def panel(contenido, *, padding=20, expand=None):
    return ft.Container(contenido, bgcolor=SUPERFICIE, border=ft.Border.all(1, BORDE),
                        border_radius=12, padding=padding, expand=expand)


def selector(etiqueta_campo, valores, valor, callback, *, width=170):
    return ft.Dropdown(label=etiqueta_campo, value=valor,
                       options=[ft.DropdownOption(key=v, text=v) for v in valores],
                       on_select=callback, width=width, text_size=13,
                       border_color=BORDE, border_radius=8, filled=True,
                       fill_color=SUPERFICIE, dense=True, color=TINTA)


def estado_vacio(titulo, descripcion):
    return ft.Container(ft.Column([ft.Icon(ft.Icons.SEARCH_OFF_ROUNDED, size=40, color=SECUNDARIO),
                                    ft.Text(titulo, size=18, color=TINTA, weight=ft.FontWeight.W_500),
                                    ft.Text(descripcion, color=SECUNDARIO, text_align=ft.TextAlign.CENTER)],
                                   alignment=ft.MainAxisAlignment.CENTER,
                                   horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
                        expand=True, alignment=ft.Alignment.CENTER, padding=24)
