"""Prueba 3B.4: preparación explícita y servidor Flet instrumentado, sin red OL.

La instrumentación sólo existe en esta entrada. Los tiempos de page.update son
construcción/envío del parche, nunca tiempos de renderizado en el cliente.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sqlite3
import threading
from time import perf_counter_ns, sleep

from biblioteca.consultas_locales import ConsultasCatalogoLocal, PORTADAS
from biblioteca.errores import ErrorValidacion
from herramientas.catalogo_sintetico import generar_catalogo


def preparar(base: Path, cantidad: int = 100000):
    base = Path(base).resolve()
    marcador = base.with_suffix(base.suffix + ".tipo.json")
    if base.exists() or marcador.exists():
        raise ErrorValidacion("La prueba requiere un destino nuevo; no reemplaza bases existentes.")
    resultado = generar_catalogo(base, cantidad)
    marcador.write_text(json.dumps({"version": 1, "tipo": "RENDIMIENTO", "naturaleza": "SINTETICA",
        "cantidad_obras": cantidad}, indent=2) + "\n", encoding="utf-8")
    return resultado


def exigir_sintetica(base):
    try:
        marcador = json.loads(base.with_suffix(base.suffix + ".tipo.json").read_text(encoding="utf-8"))
        if marcador.get("tipo") != "RENDIMIENTO" or marcador.get("naturaleza") != "SINTETICA":
            raise ValueError("No es una fixture de rendimiento")
    except (OSError, ValueError, TypeError, AttributeError) as error:
        raise ErrorValidacion("Esta herramienta sólo sirve una base sintética identificada.") from error
    return marcador


class RegistroMedicion:
    def __init__(self, base, destino, demora_ms=0):
        self.base, self.destino, self.demora_ms = Path(base), Path(destino), demora_ms
        self.eventos = []
        self._candado = threading.Lock()

    def anotar(self, tipo, **datos):
        with self._candado:
            id = len(self.eventos) + 1
            self.eventos.append({"id": id, "tipo": tipo, "instante_ns": perf_counter_ns(), **datos})
            return id

    def guardar(self):
        with self._candado:
            eventos = list(self.eventos)
        informe = {"fecha_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version, "plataforma": platform.platform(), "base": str(self.base),
            "naturaleza": "SINTETICA", "demora_artificial_ms": self.demora_ms,
            "reloj": "perf_counter_ns; sólo comparar intervalos del mismo proceso",
            "eventos": eventos}
        self.destino.parent.mkdir(parents=True, exist_ok=True)
        self.destino.write_text(json.dumps(informe, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


class ConsultasMedidas(ConsultasCatalogoLocal):
    def __init__(self, base, registro):
        super().__init__(base)
        self.registro = registro

    def consultar_pagina(self, **filtros):
        id = self.registro.anotar("consulta_inicio", filtros=filtros)
        inicio = perf_counter_ns()
        if self.registro.demora_ms:
            sleep(self.registro.demora_ms / 1000)
        try:
            resultado = super().consultar_pagina(**filtros)
        except Exception as error:
            self.registro.anotar("consulta_error", consulta=id, error=type(error).__name__)
            raise
        self.registro.anotar("consulta_fin", consulta=id, duracion_ms=(perf_counter_ns() - inicio) / 1e6,
                            total=resultado.total, filas=len(resultado.obras))
        return resultado


def servir(base, destino, *, puerto=8552, demora_ms=0):
    import flet as ft
    from biblioteca.interfaz.aplicacion import AplicacionHorizonte

    exigir_sintetica(base)
    registro = RegistroMedicion(base, destino, demora_ms)

    class AplicacionMedida(AplicacionHorizonte):
        def montar(self):
            actualizar = self.page.update
            def actualizar_medido(*controles):
                inicio = perf_counter_ns()
                actualizar(*controles)
                registro.anotar("parche_enviado", duracion_ms=(perf_counter_ns() - inicio) / 1e6,
                    destino=self.destino, resumen=self.catalogo.resumen.value,
                    contador=self.catalogo.contador.value, tema=self.page.theme_mode.value)
            self.page.update = actualizar_medido
            super().montar()

        async def _desconectar(self, e=None):
            await super()._desconectar(e)
            await self.lector.esperar_cierre()
            registro.guardar()

    def main(page):
        AplicacionMedida(page, consultas=ConsultasMedidas(base, registro)).montar()

    try:
        ft.run(main, host="127.0.0.1", port=puerto, view=ft.AppView.WEB_BROWSER, assets_dir=str(PORTADAS))
    finally:
        registro.guardar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modos = parser.add_subparsers(dest="modo", required=True)
    generador = modos.add_parser("preparar", help="Generar una base nueva, sin tocar demo/operativa")
    generador.add_argument("--base", type=Path, required=True)
    generador.add_argument("--cantidad", type=int, default=100000)
    servidor = modos.add_parser("servir", help="Abrir una fixture ya preparada")
    servidor.add_argument("--base", type=Path, required=True)
    servidor.add_argument("--registro", type=Path, required=True)
    servidor.add_argument("--port", type=int, default=8552)
    servidor.add_argument("--demora-ms", type=int, default=0, help="Retardo de ensayo; no es rendimiento real")
    args = parser.parse_args()
    if args.modo == "preparar":
        print(json.dumps(preparar(args.base, args.cantidad), ensure_ascii=False, indent=2))
    else:
        if args.demora_ms < 0 or args.registro.resolve() in (args.base.resolve(), args.base.with_suffix(".db.tipo.json").resolve()):
            parser.error("Retardo inválido o registro incompatible con la base")
        servir(args.base.resolve(), args.registro, puerto=args.port, demora_ms=args.demora_ms)
