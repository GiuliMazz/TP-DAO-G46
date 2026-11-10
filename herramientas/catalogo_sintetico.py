"""Fixture de volumen en SQLite temporal; no es un importador de producción."""

from pathlib import Path
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from biblioteca.errores import ErrorValidacion
from biblioteca.persistencia.base_datos import conectar, migrar, transaccion


def id_sintetico(tipo: str, numero: int = 0) -> str:
    return str(uuid5(NAMESPACE_URL, f"horizonte:solo-prueba-sintetica:{tipo}:{numero}"))


def generar_catalogo(ruta: Path, cantidad: int, *, lote: int = 1000) -> dict:
    """Cargar por lotes una base NUEVA, con claves foráneas y esquema reales.

    SQL directo exclusivo de fixture: omite la revisión humana y la API de altas
    para medir consultas, no la velocidad del importador ni reglas de escritura.
    """
    if type(cantidad) is not int or cantidad < 10 or type(lote) is not int or lote < 1:
        raise ErrorValidacion("La carga requiere al menos diez obras y un lote positivo.")
    ruta = Path(ruta)
    if ruta.exists():
        raise ErrorValidacion("La carga sintética requiere un destino nuevo.")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    inicio = perf_counter()
    c = conectar(ruta)
    try:
        migrar(c)
        autores = min(2000, cantidad)
        with transaccion(c):
            for n, nombre in enumerate(("Centro", "Norte", "Sur")):
                c.execute("INSERT INTO sede VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (id_sintetico("sede", n), nombre, nombre.casefold(), "Dirección sintética",
                           "prueba@example.test", "Horario sintético", int(n != 2)))
            c.executemany("INSERT INTO autor VALUES (?, NULL, ?, ?)",
                          ((id_sintetico("autor", n), f"Autor sintético {n:04}", f"autor sintético {n:04}")
                           for n in range(autores)))
            for tipo, nombres in (("GENERO", [f"Género sintético {n}" for n in range(4)]),
                                 ("ETIQUETA", ["Tema sintético"]), ("PUBLICO", ["Público sintético"])):
                for n, nombre in enumerate(nombres):
                    c.execute("INSERT INTO termino_clasificacion VALUES (?, ?, ?, ?)",
                              (id_sintetico(tipo, n), tipo, nombre, nombre.casefold()))
            for primero in range(1, cantidad + 1, lote):
                obras, ediciones, autoria, copias, asociaciones, decisiones = [], [], [], [], [], []
                for n in range(primero, min(primero + lote, cantidad + 1)):
                    oid = id_sintetico("obra", n)
                    eid = id_sintetico("edicion", n)
                    alternativa = id_sintetico("alternativa", n) if n % 5 == 0 else None
                    titulo = "Título compartido sintético" if n % 20 == 0 else f"Libro sintético {n:06}"
                    original = f"Original sintético {n:06}"
                    preferida = alternativa if alternativa is not None and n % 7 == 0 else eid
                    obras.append((oid, original, original.casefold(), preferida))
                    ediciones.append((eid, oid, titulo, titulo.casefold()))
                    if alternativa:
                        otro = f"Traducción alternativa sintética {n:06}"
                        ediciones.append((alternativa, oid, otro, otro.casefold()))
                    autoria.append((oid, id_sintetico("autor", n % autores), 0))
                    if n % 10 == 0:
                        autoria.append((oid, id_sintetico("autor", (n + 1) % autores), 1))
                    for tipo, numero in (("GENERO", n % 4), ("ETIQUETA", 0), ("PUBLICO", 0)):
                        if (tipo == "ETIQUETA" and n % 2) or (tipo == "PUBLICO" and n % 3):
                            continue
                        estado = "RECHAZADO" if n % 11 == 0 else "PROPUESTO" if n % 5 == 0 else "APROBADO"
                        tid = id_sintetico(tipo, numero)
                        decision = (estado, "MANUAL", "Decisión sintética para carga, no revisión real", "2026-11-03T12:00:00+00:00")
                        asociaciones.append((oid, tid, tipo, *decision))
                        decisiones.append((oid, tid, *decision))
                    # Copias explícitas de fixture, marcadas SINT; no vinculadas a OL.
                    for numero_sede in (0, 1, 2):
                        if numero_sede != 0 and n % 5:
                            continue
                        sid = id_sintetico("sede", numero_sede)
                        condicion = "DANIADO" if n % 7 == 0 else "APTO"
                        situacion = "BAJA" if n % 13 == 0 else "LIBRE"
                        copias.append((id_sintetico(f"copia-{numero_sede}", n), f"SINT-{numero_sede}-{n:06}",
                                       eid, sid, sid, condicion, situacion))
                c.executemany("INSERT INTO obra (id, titulo_original, titulo_normalizado, edicion_preferida_id) VALUES (?, ?, ?, ?)", obras)
                c.executemany("INSERT INTO edicion (id, obra_id, titulo, titulo_normalizado, idioma) VALUES (?, ?, ?, ?, 'spa')", ediciones)
                c.executemany("INSERT INTO obra_autor VALUES (?, ?, ?)", autoria)
                c.executemany("INSERT INTO ejemplar VALUES (?, ?, ?, ?, ?, ?, ?)", copias)
                c.executemany("""INSERT INTO clasificacion_obra (obra_id, termino_id, tipo, estado, metodo, motivo, fecha)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)""", asociaciones)
                c.executemany("""INSERT INTO decision_clasificacion (obra_id, termino_id, estado, metodo, motivo, fecha)
                                 VALUES (?, ?, ?, ?, ?, ?)""", decisiones)
        # La fixture no fuerza estadísticas ni cambia PRAGMA para mejorar resultados.
        conteos = {tabla: c.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
                   for tabla in ("obra", "edicion", "autor", "obra_autor", "ejemplar", "clasificacion_obra")}
        if c.execute("PRAGMA foreign_key_check").fetchall() or c.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise AssertionError("La fixture sintética no cumple integridad.")
        return {"naturaleza": "SINTETICA; no es un catálogo real de Open Library", "filas": conteos,
                "lote_obras": lote, "generacion_segundos": perf_counter() - inicio,
                "base_bytes": ruta.stat().st_size}
    finally:
        c.close()
