"""Horizonte: catálogo local preparado. No genera datos al iniciar."""

import argparse
from pathlib import Path

import flet as ft

from biblioteca.interfaz.aplicacion import AplicacionHorizonte
from biblioteca.consultas_locales import BASE_DEMO, ConsultasCatalogoLocal, PORTADAS
from biblioteca.interfaz.datos_prototipo import DatosPrototipo


def crear_aplicacion(base=BASE_DEMO, *, prototipo=False):
    def main(page: ft.Page):
        AplicacionHorizonte(page, DatosPrototipo() if prototipo else None,
                            consultas=ConsultasCatalogoLocal(base)).montar()
    return main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE_DEMO, help="Base local previamente preparada (por defecto demo.db)")
    parser.add_argument("--prototipo", action="store_true", help="Abrir explícitamente la maqueta histórica 3A, sin persistencia")
    parser.add_argument("--web", action="store_true", help="Verificar en navegador local (requiere requirements-preview.txt)")
    parser.add_argument("--port", type=int, default=8550, help="Puerto de la vista web local")
    args = parser.parse_args()
    ft.run(crear_aplicacion(args.base, prototipo=args.prototipo), host="127.0.0.1", port=args.port if args.web else 0,
           assets_dir=str(PORTADAS),
           view=ft.AppView.WEB_BROWSER if args.web else ft.AppView.FLET_APP)
