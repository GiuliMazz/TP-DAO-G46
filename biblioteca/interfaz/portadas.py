"""Cubiertas tipográficas de presentación; nunca se guardan como bibliografía."""

from hashlib import sha256

import flet as ft

PALETAS = (
    ("#173F50", "#96D6DA"), ("#48334F", "#E4B9CF"),
    ("#29463D", "#B6D8BB"), ("#5A382D", "#E6C29B"),
    ("#303F63", "#B3C8ED"), ("#513E25", "#E2D2A4"),
)


def portada_ilustrativa(titulo: str, autor: str) -> ft.Container:
    """Diseño estable por título/autor, independiente del tema y sin red."""
    indice = sha256(f"{titulo}\0{autor}".encode("utf-8")).digest()[0] % len(PALETAS)
    fondo, acento = PALETAS[indice]
    return ft.Container(ft.Stack([
        ft.Container(width=180, height=180, right=-65, top=24, border_radius=90,
                     border=ft.Border.all(1, acento), opacity=0.4),
        ft.Container(width=130, height=130, right=-40, top=49, border_radius=65,
                     border=ft.Border.all(1, acento), opacity=0.3),
        ft.Container(ft.Column([
            ft.Text(autor.upper(), size=10, color=acento, max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS),
            ft.Container(expand=True),
            ft.Icon(ft.Icons.AUTO_STORIES_OUTLINED, size=28, color=acento),
            ft.Text(titulo, size=22, color="#FFFFFF", weight=ft.FontWeight.W_600,
                    max_lines=4, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Container(height=4),
            ft.Text("PORTADA ILUSTRATIVA", size=9, color=acento),
        ], spacing=9, expand=True), padding=18),
    ], expand=True), bgcolor=fondo, expand=True, clip_behavior=ft.ClipBehavior.HARD_EDGE,
        border_radius=8, tooltip="Portada ilustrativa · diseño local, no es la cubierta de la edición")
