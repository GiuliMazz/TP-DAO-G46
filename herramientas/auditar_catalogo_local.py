"""Informes reproducibles de cobertura y muestra visual; sólo lectura, sin red."""

import argparse
import base64
from contextlib import closing
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import sqlite3

from biblioteca.importacion.fuente_catalogo_local import FuenteCatalogoLocal

RAIZ = Path(__file__).resolve().parents[1]
# Muestra intencional: ficción/no ficción, coautoría, Search/Works y ausencias.
MUESTRA = (
    "OL7924103W", "OL27482W", "OL453936W", "OL46241W", "OL17077942W",
    "OL471891W", "OL1914079W", "OL19977306W", "OL492658W", "OL69612W",
    "OL503666W", "OL17610507W", "OL149155W", "OL1835957W", "OL16814568W",
    "OL2950913W", "OL1717271W", "OL8453734W", "OL63215W", "OL39560W",
)


def cobertura(conexion):
    total = conexion.execute("SELECT COUNT(*) FROM obra").fetchone()[0]
    resultado = {"obras": total, "tipos": {}, "terminos": []}
    for tipo in ("GENERO", "ETIQUETA", "PUBLICO"):
        conteos = {estado: conexion.execute(
            "SELECT COUNT(DISTINCT obra_id) FROM clasificacion_obra WHERE tipo=? AND estado=?",
            (tipo, estado)).fetchone()[0] for estado in ("APROBADO", "PROPUESTO", "RECHAZADO")}
        conteos["sin_aprobadas"] = total - conteos["APROBADO"]
        resultado["tipos"][tipo] = conteos
    resultado["terminos"] = [dict(r) for r in conexion.execute(
        """SELECT t.tipo,t.nombre,c.estado,COUNT(*) obras FROM clasificacion_obra c
           JOIN termino_clasificacion t ON t.id=c.termino_id
           GROUP BY t.id,c.estado ORDER BY t.tipo,t.nombre,c.estado""")]
    return resultado


def generar(base, manifiesto, destino):
    fuente = FuenteCatalogoLocal(manifiesto)
    destino.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(Path(base).resolve().as_uri() + "?mode=ro", uri=True)) as c:
        c.row_factory = sqlite3.Row
        informe = cobertura(c)
        tarjetas, registros = [], []
        for numero, wid in enumerate(MUESTRA, 1):
            r = dict(c.execute("""SELECT o.id,o.id_openlibrary obra_ol,o.titulo_original,e.titulo,
                e.id_openlibrary edicion_ol,e.isbn_10,e.isbn_13,e.editorial,e.anio_publicacion,
                e.portada_edicion_id FROM obra o JOIN edicion e ON e.id=o.edicion_preferida_id
                WHERE o.id_openlibrary=?""", (wid,)).fetchone())
            autores = "; ".join(f[0] for f in c.execute("""SELECT a.nombre FROM obra_autor oa
                JOIN autor a ON a.id=oa.autor_id WHERE oa.obra_id=? ORDER BY oa.orden""", (r["id"],)))
            clases = [dict(f) for f in c.execute("""SELECT t.tipo,t.nombre,c.estado FROM clasificacion_obra c
                JOIN termino_clasificacion t ON t.id=c.termino_id WHERE c.obra_id=?
                ORDER BY t.tipo,t.nombre""", (r["id"],))]
            detalle_obra = wid in fuente.fuentes["fuentes/obras.json"]
            evidencia = "Search + edición + Works" if detalle_obra else "Search + edición; sin detalle Works"
            portada = fuente.portadas.get(r["portada_edicion_id"])
            imagen = (f'<img alt="Portada de la edición seleccionada" src="data:image/jpeg;base64,'
                      + base64.b64encode(portada.read_bytes()).decode() + '">' if portada else
                      '<div class="ausente">Sin portada disponible</div>')
            datos = [("Autores", autores), ("Título de obra", r["titulo_original"]),
                     ("Edición", r["edicion_ol"]), ("Editorial", r["editorial"]),
                     ("Año", r["anio_publicacion"]), ("ISBN", r["isbn_13"] or r["isbn_10"]),
                     ("Evidencia", evidencia)]
            texto = "".join(f"<dt>{k}</dt><dd>{escape(str(v)) if v else 'No informado'}</dd>" for k, v in datos)
            clasificacion = " · ".join(f'{x["tipo"]}: {x["nombre"]} ({x["estado"]})' for x in clases)
            tarjetas.append(f'<article id="obra-{numero}"><div>{imagen}</div><section><small>{numero:02d} / 20 · {wid}</small>'
                            f'<h2>{escape(r["titulo"])}</h2><dl>{texto}</dl><p>{escape(clasificacion or "Sin clasificación")}</p>'
                            f'<a href="https://openlibrary.org/works/{wid}">Obra</a> · '
                            f'<a href="https://openlibrary.org/books/{r["edicion_ol"]}">Edición</a>'
                            '<p class="revision">Revisar: título y autor de cubierta, edición/ISBN, idioma y ausencias. '
                            'Search es evidencia parcial; no equivale a revisión bibliográfica definitiva.</p></section></article>')
            registros.append({**r, "autores": autores, "evidencia": evidencia,
                              "portada_local": portada is not None, "clasificaciones": clases})
    informe["muestra"] = registros
    informe["generado_utc"] = datetime.now(timezone.utc).isoformat()
    (destino / "cobertura.json").write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n")
    filas = ["# Cobertura de clasificación de las 100 obras", "", "Sólo asociaciones APROBADO alimentan los filtros. "
             "Las cantidades de los estados pueden superponerse en una obra. No se infiere público adulto por ausencia.", "",
             "| Tipo | Con aprobadas | Con propuestas | Sin aprobadas |", "|---|---:|---:|---:|"]
    for tipo, n in informe["tipos"].items():
        filas.append(f'| {tipo} | {n["APROBADO"]}/{informe["obras"]} | {n["PROPUESTO"]} | {n["sin_aprobadas"]} |')
    filas += ["", "## Distribución", "", "| Tipo | Término | Estado | Obras |", "|---|---|---|---:|"]
    filas += [f'| {r["tipo"]} | {r["nombre"]} | {r["estado"]} | {r["obras"]} |' for r in informe["terminos"]]
    filas += ["", "La muestra intencional de 20 obras está en [auditoria_visual.html](./auditoria_visual.html). "
              "Incluye ausencias de portada/ISBN y evidencia parcial de Search. No es una muestra estadística.", ""]
    (destino / "COBERTURA.md").write_text("\n".join(filas), encoding="utf-8")
    html = '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Horizonte · Auditoría bibliográfica · 20 obras</title><style>
body{font:16px system-ui;background:#edf3f5;color:#17333d;margin:32px auto;max-width:1100px;padding:0 24px}
header{margin-bottom:30px}h1{font-size:28px}article{background:white;border:1px solid #c8d8df;border-radius:12px;
padding:24px;margin-bottom:24px;display:grid;grid-template-columns:230px 1fr;gap:28px;break-inside:avoid}
img{max-width:230px;width:100%;max-height:350px;object-fit:contain;object-position:top}.ausente{height:280px;
display:grid;place-items:center;background:#eef2f4;color:#536a73;border-radius:8px}h2{margin:8px 0 14px}
dl{display:grid;grid-template-columns:130px 1fr;gap:7px;font-size:14px}dt{font-weight:600}dd{margin:0;overflow-wrap:anywhere}
small,.revision{color:#536a73}.revision{font-size:13px}a{color:#176477}
@media(max-width:650px){article{grid-template-columns:1fr}img{max-height:240px}dl{grid-template-columns:100px 1fr}}
</style><header><h1>Horizonte · Auditoría bibliográfica</h1><p>20 obras reales de las 100 seleccionadas. Portadas locales,
sin acceso a internet para visualizar. Datos ausentes identificados; enlaces externos sólo para contrastar fuentes.</p>
<p>Esta ficha reúne evidencia para la revisión. Los hallazgos del recorrido visual se documentan por separado.</p></header>'''
    (destino / "auditoria_visual.html").write_text(html + "".join(tarjetas) + "</html>", encoding="utf-8")
    return informe


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=RAIZ / "datos/generados/catalogo_local/demo.db")
    parser.add_argument("--manifiesto", type=Path, default=RAIZ / "datos/catalogo_local/seleccion.json")
    parser.add_argument("--destino", type=Path, default=RAIZ / "docs/auditoria_catalogo")
    args = parser.parse_args()
    informe = generar(args.base, args.manifiesto, args.destino)
    print(json.dumps({"obras": informe["obras"], "tipos": informe["tipos"], "muestra": len(informe["muestra"])}, indent=2))
