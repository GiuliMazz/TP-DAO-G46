"""Captura acotada para el TP; la reproducción de bases no utiliza esta red."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from biblioteca.errores import ErrorBiblioteca
from biblioteca.importacion.fuente_catalogo_local import candidato_desde_respuestas
from biblioteca.importacion.modelos import EstadoImportacion
from biblioteca.importacion.validador_catalogo_local import ValidadorCatalogoLocal

RAIZ = Path(__file__).resolve().parents[2]


def guardar_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def descargar(url, archivo):
    if archivo.exists():
        return archivo.read_bytes()
    for intento in range(3):
        time.sleep(1.1 if intento == 0 else 2 ** intento)
        try:
            req = Request(url, headers={"User-Agent": "Horizonte-DAO-TP/1.0 (educational local catalog)"})
            with urlopen(req, timeout=40) as respuesta:
                contenido = respuesta.read()
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(contenido)
            return contenido
        except HTTPError as error:
            if error.code in (404, 410):
                raise
            if intento == 2:
                raise
        except (URLError, TimeoutError):
            if intento == 2:
                raise


def capturar(destino):
    if (destino / "seleccion.json").exists():
        raise ValueError("La selección ya existe; no se sobrescriben capturas revisadas")
    cache = RAIZ / "datos/generados/captura_local"
    revision_ruta = destino / "revision_seleccion.json"
    revisiones = json.loads(revision_ruta.read_text(encoding="utf-8"))["ediciones"] if revision_ruta.exists() else {}
    busquedas = {}
    for ruta in sorted((RAIZ / "archivo/openlibrary/muestra_1000/cache_busquedas").glob("*.json")):
        respuesta = json.loads(ruta.read_text())
        url = "https://openlibrary.org/search.json?" + urlencode({
            "q": respuesta["q"], "offset": respuesta["offset"], "limit": 100,
            "fields": "key,title,author_key,author_name,cover_i,first_publish_year,subject,editions"})
        for doc in respuesta["docs"]:
            if doc.get("key", "").startswith("/works/"):
                busquedas.setdefault(doc["key"].split("/")[-1], {
                    "datos": doc, "url": url, "captura_utc": None,
                    "origen_anterior": str(ruta.relative_to(RAIZ)),
                    "sha256_archivo_anterior": sha256(ruta.read_bytes()).hexdigest()})
    ediciones, obras = {}, {}
    anteriores = json.loads((RAIZ / "datos/openlibrary/respuestas_originales.json").read_text())
    for registro in anteriores:
        b, w, e = registro["busqueda"], registro["obra"], registro["edicion"]
        wid, eid = w["key"].split("/")[-1], e["key"].split("/")[-1]
        busquedas[wid] = {"datos": b, "url": "https://openlibrary.org/search.json?" + urlencode({"q": "key:" + w["key"]}),
                          "captura_utc": None, "origen_anterior": "datos/openlibrary/respuestas_originales.json"}
        ediciones[eid] = {"datos": e, "url": "https://openlibrary.org" + e["key"] + ".json", "captura_utc": None}
        obras[wid] = {"datos": w, "url": "https://openlibrary.org" + w["key"] + ".json", "captura_utc": None}
    # Selección intercalada de categorías; no se asigna un género por la búsqueda.
    grupos = defaultdict(list)
    for r in json.loads((RAIZ / "datos/openlibrary/catalogo_exploratorio.json").read_text()):
        grupos[r["categoria_busqueda"]].append(r)
    candidatas, vistos = [], set()
    for r in anteriores:
        wid, eid = r["obra"]["key"].split("/")[-1], r["edicion"]["key"].split("/")[-1]
        if wid not in vistos:
            candidatas.append((wid, eid)); vistos.add(wid)
    for i in range(20):
        for grupo in grupos.values():
            if i < len(grupo):
                r = grupo[i]
                if r["obra_id"] not in vistos:
                    candidatas.append((r["obra_id"], r["edicion_id"])); vistos.add(r["obra_id"])
    candidatas = candidatas[:180]
    faltantes = [eid for _, eid in candidatas if eid not in ediciones]
    for inicio in range(0, len(faltantes), 25):
        lote = faltantes[inicio:inicio + 25]
        url = "https://openlibrary.org/api/books?" + urlencode({
            "bibkeys": ",".join("OLID:" + eid for eid in lote), "jscmd": "details", "format": "json"})
        archivo = cache / (sha256(url.encode()).hexdigest() + ".json")
        contenido = descargar(url, archivo)
        for clave, valor in json.loads(contenido).items():
            if "details" in valor:
                ediciones[clave.removeprefix("OLID:")] = {
                    "datos": valor["details"], "url": url,
                    "captura_utc": datetime.fromtimestamp(archivo.stat().st_mtime, timezone.utc).isoformat(),
                    "sha256_respuesta_lote": sha256(contenido).hexdigest()}
        print(f"Ediciones capturadas: {len(ediciones)}", flush=True)
    seleccion, excluidas = [], []
    validador = ValidadorCatalogoLocal()
    for wid, eid in candidatas:
        if eid in revisiones:
            excluidas.append({"obra_id": wid, "edicion_id": eid, "estado": "REVISION_BIBLIOGRAFICA",
                              "motivo": revisiones[eid]})
            continue
        try:
            b, e, w = busquedas[wid], ediciones[eid], obras.get(wid)
            evaluacion = validador.evaluar(candidato_desde_respuestas(b["datos"], e["datos"], w["datos"] if w else None))
            if evaluacion.estado is EstadoImportacion.VALIDADA:
                seleccion.append({"obra_id": wid, "edicion_id": eid})
                if len(seleccion) == 100:
                    break
            else:
                excluidas.append({"obra_id": wid, "edicion_id": eid, "estado": evaluacion.estado.value,
                                  "alertas": evaluacion.alertas})
        except (KeyError, ErrorBiblioteca, TypeError, ValueError) as error:
            excluidas.append({"obra_id": wid, "edicion_id": eid, "error": str(error)})
    if len(seleccion) < 100:
        guardar_json(cache / "excluidas.json", excluidas)
        raise ValueError(f"Sólo {len(seleccion)} candidatas aceptables; revisar antes de publicar selección")
    fuentes = {
        "fuentes/busquedas.json": {r["obra_id"]: busquedas[r["obra_id"]] for r in seleccion},
        "fuentes/ediciones.json": {r["edicion_id"]: ediciones[r["edicion_id"]] for r in seleccion},
        "fuentes/obras.json": {r["obra_id"]: obras[r["obra_id"]] for r in seleccion if r["obra_id"] in obras},
    }
    huellas = {}
    for nombre, datos in fuentes.items():
        ruta = destino / nombre
        guardar_json(ruta, datos)
        huellas[nombre] = sha256(ruta.read_bytes()).hexdigest()
    portadas, fallidas = [], []
    # Sólo la portada elegida por el validador, no toda la galería de cada edición.
    ids_portada = sorted({validador.evaluar(candidato_desde_respuestas(
        busquedas[r["obra_id"]]["datos"], ediciones[r["edicion_id"]]["datos"],
        obras[r["obra_id"]]["datos"] if r["obra_id"] in obras else None)).normalizados["edicion"]["portada_edicion_id"]
        for r in seleccion} - {None})
    for i, id in enumerate(ids_portada):
        url = f"https://covers.openlibrary.org/b/id/{id}-M.jpg?default=false"
        ruta = destino / f"portadas/{id}.jpg"
        try:
            contenido = descargar(url, ruta)
            if not contenido.startswith(b"\xff\xd8"):
                raise ValueError("Respuesta de portada no es JPEG")
            portadas.append({"id": id, "archivo": f"portadas/{id}.jpg", "url": url,
                             "sha256": sha256(contenido).hexdigest()})
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            fallidas.append({"id": id, "url": url, "motivo": str(error)})
        if (i + 1) % 10 == 0:
            print(f"Portadas: {i + 1}/{len(ids_portada)}", flush=True)
    if revision_ruta.exists():
        huellas["revision_seleccion.json"] = sha256(revision_ruta.read_bytes()).hexdigest()
    guardar_json(destino / "seleccion.json", {"version": 1, "politica": validador.VERSION,
        "fecha_preparacion_utc": datetime.now(timezone.utc).isoformat(), "fuentes": huellas,
        "registros": seleccion, "portadas": portadas, "portadas_no_disponibles": fallidas,
        "excluidas_antes_de_completar": excluidas})
    print(f"Selección: {len(seleccion)} obras, {len(portadas)} portadas locales", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=RAIZ / "datos/catalogo_local")
    args = parser.parse_args()
    capturar(args.destino.resolve())
