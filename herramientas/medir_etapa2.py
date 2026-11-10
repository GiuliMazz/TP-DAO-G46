"""Medición reproducible de servicios sobre bases temporales, siempre sintéticas."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sqlite3
from statistics import median
import sys
from tempfile import TemporaryDirectory
from time import perf_counter, process_time
import tracemalloc

from biblioteca.persistencia.base_datos import VERSION_ESQUEMA, conectar
from biblioteca.errores import ErrorPersistencia
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.inventario_service import InventarioService
from herramientas.catalogo_sintetico import generar_catalogo, id_sintetico


def _medir(conexion, operacion, repeticiones, limite_segundos=2.0):
    # Capturar el SQL realmente emitido para EXPLAIN; sólo contiene datos sintéticos.
    sentencias = []
    def acotada():
        vence = perf_counter() + limite_segundos
        conexion.set_progress_handler(lambda: int(perf_counter() > vence), 1000)
        try:
            return operacion()
        finally:
            conexion.set_progress_handler(None, 0)
    tiempos, cpu = [], []
    fase = "calentamiento"
    try:
        conexion.set_trace_callback(sentencias.append)
        try:
            resultado = acotada()  # Calentamiento explícito, fuera de la medición.
        finally:
            conexion.set_trace_callback(None)
        for numero in range(repeticiones):
            fase = f"muestra {numero + 1}"
            inicio, inicio_cpu = perf_counter(), process_time()
            acotada()
            tiempos.append((perf_counter() - inicio) * 1000)
            cpu.append((process_time() - inicio_cpu) * 1000)
        fase = "memoria Python"
        tracemalloc.start()
        try:
            acotada()
            _, pico = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
    except ErrorPersistencia as error:
        if not isinstance(error.__cause__, sqlite3.Error) or error.__cause__.sqlite_errorcode != sqlite3.SQLITE_INTERRUPT:
            raise
        planes = [{"sql": sql, "plan": [dict(f) for f in conexion.execute("EXPLAIN QUERY PLAN " + sql)]}
                  for sql in list(sentencias) if sql.lstrip().upper().startswith(("SELECT", "WITH"))]
        return None, {"interrumpida": True, "fase": fase, "limite_segundos": limite_segundos,
                      "muestras_parciales_ms": tiempos, "muestras_parciales_cpu_ms": cpu, "planes": planes}
    finally:
        conexion.set_trace_callback(None)
    planes = []
    for sql in sentencias:
        if sql.lstrip().upper().startswith(("SELECT", "WITH")):
            planes.append({"sql": sql, "plan": [dict(fila) for fila in conexion.execute("EXPLAIN QUERY PLAN " + sql)]})
    return resultado, {"mediana_ms": median(tiempos), "maximo_ms": max(tiempos),
                       "mediana_cpu_ms": median(cpu), "muestras_cpu_ms": cpu,
                       "muestras_ms": tiempos, "pico_python_bytes": pico, "consultas_sql": len(planes), "planes": planes}


def medir_catalogo(ruta: Path, cantidad: int, repeticiones: int, *, limite_segundos: float = 2.0) -> dict:
    if type(repeticiones) is not int or repeticiones < 1:
        raise ValueError("Se requiere al menos una repetición.")
    with closing(conectar(ruta)) as c:
        obras, ediciones, autores = ObraRepository(c), EdicionRepository(c), AutorRepository(c)
        catalogo = CatalogoService(obras, ediciones, autores)
        inventario = InventarioService(EjemplarRepository(c), ediciones, SedeRepository(c), obras)
        punto = max(5, cantidad // 2 // 5 * 5)
        oid = id_sintetico("obra", punto)
        genero = id_sintetico("GENERO", 1)
        aptas_centro = cantidad - cantidad // 7 - cantidad // 13 + cantidad // 91
        escenarios = {
            "primera_pagina": lambda: catalogo.listar_obras(),
            "pagina_profunda": lambda: catalogo.listar_obras(desplazamiento=max(0, cantidad - 50)),
            "titulo_original": lambda: catalogo.listar_obras(titulo=f"Original sintético {punto:06}"),
            "titulo_alternativo": lambda: catalogo.listar_obras(titulo=f"alternativa sintética {punto:06}"),
            "autor": lambda: catalogo.listar_obras(autor="Autor sintético 0001"),
            "genero": lambda: catalogo.listar_obras(genero_id=genero),
            "etiqueta": lambda: catalogo.listar_obras(etiqueta_id=id_sintetico("ETIQUETA")),
            "publico": lambda: catalogo.listar_obras(publico_id=id_sintetico("PUBLICO")),
            "combinados": lambda: catalogo.listar_obras(titulo="sintético", genero_id=id_sintetico("GENERO", 2),
                                                        etiqueta_id=id_sintetico("ETIQUETA"), publico_id=id_sintetico("PUBLICO")),
            "sin_resultados": lambda: catalogo.listar_obras(titulo="fragmento_que_no_existe"),
            "detalle": lambda: catalogo.obtener_detalle(oid),
            "disponibilidad": lambda: inventario.consultar_disponibilidad(oid),
            "ejemplares_obra": lambda: inventario.listar(obra_id=oid, solo_disponibles=True),
            "ejemplares_sede": lambda: inventario.listar(sede_actual_id=id_sintetico("sede"), solo_disponibles=True),
            "ejemplares_sede_profunda": lambda: inventario.listar(sede_actual_id=id_sintetico("sede"), solo_disponibles=True,
                                                                  desplazamiento=max(0, aptas_centro - 50)),
        }
        mediciones = {}
        for nombre, operacion in escenarios.items():
            resultado, medida = _medir(c, operacion, repeticiones, limite_segundos)
            if medida.get("interrumpida"):
                mediciones[nombre] = medida
                print(f"{cantidad} obras: {nombre} interrumpida tras {medida['limite_segundos']} s", file=sys.stderr, flush=True)
                continue
            if isinstance(resultado, list):
                if len(resultado) > 50:
                    raise AssertionError(f"{nombre}: resultado no acotado")
                ids = [r.id for r in resultado if hasattr(r, "id")]
                if len(ids) != len(set(ids)):
                    raise AssertionError(f"{nombre}: identificadores repetidos")
                medida["filas_resultado"] = len(resultado)
            if nombre in ("titulo_original", "titulo_alternativo") and (len(resultado) != 1 or str(resultado[0].id) != oid):
                raise AssertionError("La búsqueda perdió una obra o la duplicó")
            if nombre == "sin_resultados" and resultado:
                raise AssertionError("Una búsqueda inexistente devolvió filas")
            if nombre in ("autor", "genero", "etiqueta", "publico", "combinados"):
                if not resultado:
                    raise AssertionError(f"{nombre}: el escenario debe tener coincidencias")
                for ficha in resultado:
                    n = int(ficha.titulo_original.rsplit(" ", 1)[1])
                    if nombre == "autor":
                        valido = n % min(2000, cantidad) == 1 or (n % 10 == 0 and (n + 1) % min(2000, cantidad) == 1)
                    else:
                        valido = n % 5 != 0 and n % 11 != 0
                        if nombre == "genero": valido &= n % 4 == 1
                        if nombre == "etiqueta": valido &= n % 2 == 0
                        if nombre == "publico": valido &= n % 3 == 0
                        if nombre == "combinados": valido &= n % 4 == 2 and n % 2 == 0 and n % 3 == 0
                    if not valido:
                        raise AssertionError(f"{nombre}: obra incompatible con los filtros")
            if nombre == "detalle":
                preferida = id_sintetico("alternativa" if punto % 7 == 0 else "edicion", punto)
                if resultado.cantidad_ediciones != 2 or str(resultado.edicion_preferida.id) != preferida:
                    raise AssertionError("El detalle no conserva edición preferida/cantidad")
            if nombre == "disponibilidad":
                apto = punto % 7 != 0 and punto % 13 != 0
                esperado = {"Centro": int(apto), "Norte": int(apto), "Sur": 0}
                if {r.nombre_sede: r.disponibles for r in resultado} != esperado:
                    raise AssertionError("La disponibilidad no coincide con la fixture")
            if nombre == "primera_pagina" and len(resultado) != min(50, cantidad):
                raise AssertionError("La página inicial no está completa")
            if nombre in ("ejemplares_sede", "ejemplares_sede_profunda"):
                numeros = [n for n in range(1, cantidad + 1) if n % 7 != 0 and n % 13 != 0]
                esperados = numeros[:50] if nombre == "ejemplares_sede" else numeros[max(0, len(numeros) - 50):]
                if [e.codigo_inventario for e in resultado] != [f"SINT-0-{n:06}" for n in esperados]:
                    raise AssertionError("La página de copias no respeta disponibilidad, orden u OFFSET")
            if nombre == "ejemplares_obra" and any(str(e.edicion_id) != id_sintetico("edicion", punto) for e in resultado):
                raise AssertionError("El listado mezcló ejemplares de otra obra")
            mediciones[nombre] = medida
            print(f"{cantidad} obras: {nombre} = {medida['mediana_ms']:.2f} ms", file=sys.stderr, flush=True)
        return {"escenarios": mediciones, "cache": "Una llamada de calentamiento por escenario; conexión reutilizada",
                "sqlite_cache_size": c.execute("PRAGMA cache_size").fetchone()[0]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tamanos", type=int, nargs="+", default=[1000, 10000, 100000])
    parser.add_argument("--repeticiones", type=int, default=5)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--limite-segundos", type=float, default=2.0)
    args = parser.parse_args()
    if args.repeticiones < 1 or any(n < 10 for n in args.tamanos) or args.limite_segundos <= 0:
        parser.error("Tamaños >= 10 y repeticiones >= 1")
    if args.salida.suffix.lower() != ".json":
        parser.error("La salida debe ser un informe .json")
    informe = {"fecha_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
               "sqlite": sqlite3.sqlite_version, "plataforma": platform.platform(), "procesador": platform.processor(),
               "version_esquema": VERSION_ESQUEMA, "repeticiones": args.repeticiones,
               "objetivo_local_mediana_ms": 500, "limite_segundos": args.limite_segundos, "cargas": []}
    with TemporaryDirectory(prefix="horizonte-solo-carga-") as carpeta:
        for numero, cantidad in enumerate(args.tamanos):
            ruta = Path(carpeta) / f"sintetica-{numero}.db"
            carga = generar_catalogo(ruta, cantidad)
            carga.update(medir_catalogo(ruta, cantidad, args.repeticiones, limite_segundos=args.limite_segundos))
            informe["cargas"].append(carga)
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        informe["maximo_rss_bytes"] = rss if sys.platform == "darwin" else rss * 1024
    except ImportError:
        informe["maximo_rss_bytes"] = None
    informe["memoria_alcance"] = "Pico Python por llamada excluye SQLite nativo; máximo RSS incluye generación y todas las consultas"
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Informe guardado en {args.salida}. Todas las bases sintéticas temporales se eliminaron.")


if __name__ == "__main__":
    main()
