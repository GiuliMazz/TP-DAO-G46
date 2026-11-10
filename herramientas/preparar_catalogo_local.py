"""Reproducir dos bases locales desde evidencia guardada, sin acceso a internet."""

import argparse
from contextlib import closing
import csv
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from biblioteca.errores import ErrorBiblioteca, ErrorValidacion
from biblioteca.importacion.fuente_catalogo_local import FuenteCatalogoLocal
from biblioteca.importacion.modelos import EstadoImportacion
from biblioteca.importacion.validador_catalogo_local import ValidadorCatalogoLocal
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.importacion_repository import ImportacionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.servicios.clasificacion_service import ClasificacionService
from biblioteca.servicios.importacion_service import ImportacionService
from biblioteca.servicios.inventario_service import InventarioService
from biblioteca.servicios.sede_service import SedeService

RAIZ = Path(__file__).resolve().parents[1]
TOTAL_EJEMPLARES = 150
SEDES = ("Centro", "Norte", "Sur")


def _ruta_marcador(ruta):
    return ruta.with_suffix(ruta.suffix + ".tipo.json")


def _validar_destino(ruta, tipo, fuente):
    if ruta.suffix != ".db" or ruta.is_relative_to(fuente.raiz):
        raise ErrorValidacion("Las bases deben estar fuera de los insumos y terminar en .db.")
    marcador = _ruta_marcador(ruta)
    if marcador.exists():
        try:
            datos = json.loads(marcador.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ErrorValidacion("El identificador de tipo de base no se puede verificar.") from error
        if not isinstance(datos, dict) or not isinstance(datos.get("sedes"), dict):
            raise ErrorValidacion("El identificador de tipo de base no tiene el formato esperado.")
        if (datos.get("version"), datos.get("tipo"), datos.get("coleccion")) != (1, tipo, fuente.coleccion):
            raise ErrorValidacion("El destino pertenece a otro tipo de base o selección bibliográfica.")
        return datos
    if ruta.exists():
        raise ErrorValidacion("No se adopta ni reemplaza una base existente sin identificador de preparación.")
    return {"version": 1, "tipo": tipo, "coleccion": fuente.coleccion, "sedes": {}}


def _guardar_marcador(ruta, datos):
    destino = _ruta_marcador(ruta)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=ruta.parent,
                            prefix=".tipo-", suffix=".tmp", delete=False) as temporal:
        temporal.write(json.dumps(datos, ensure_ascii=False, indent=2) + "\n")
        nombre = Path(temporal.name)
    nombre.replace(destino)


def _sembrar_demo(conexion, ruta, marcador, ediciones):
    sedes = SedeService(SedeRepository(conexion))
    ids_sedes = []
    for nombre in SEDES:
        id = marcador["sedes"].get(nombre)
        if id is not None:
            sede = sedes.obtener(id)
        else:
            # Recuperar un alta ya confirmada si se interrumpió antes de guardar el marcador.
            sede = SedeRepository(conexion).buscar_por_nombre_normalizado(nombre.casefold())
            if sede is None:
                sede = sedes.registrar(nombre, f"Dirección ficticia de Sede {nombre}",
                    f"{nombre.lower()}@horizonte.example.test", "Lunes a viernes, 9 a 18 (demostración)")
            marcador["sedes"][nombre] = str(sede.id)
            _guardar_marcador(ruta, marcador)
        ids_sedes.append(sede.id)
    inventario = InventarioService(EjemplarRepository(conexion), EdicionRepository(conexion),
                                  SedeRepository(conexion), ObraRepository(conexion))
    plan = [(f"DEMO-{i + 1:04d}", ediciones[i % len(ediciones)].id, ids_sedes[i % len(SEDES)])
            for i in range(TOTAL_EJEMPLARES)]
    pendientes = []
    for codigo, edicion_id, sede_id in plan:
        existente = inventario.buscar_por_codigo(codigo)
        if existente is None:
            pendientes.append((codigo, edicion_id, sede_id))
        elif existente.edicion_id != edicion_id or existente.sede_propietaria_id != sede_id:
            raise ErrorValidacion(f"El código {codigo} ya representa otra edición o propietaria; no se sobrescribe.")
    for codigo, edicion_id, sede_id in pendientes:
        inventario.registrar(codigo, edicion_id, sede_id)
    # No restablecer condición, ubicación, situación ni habilitación al repetir.


def _resumen_verificado(conexion):
    # SQL de auditoría de la herramienta, no una vía alternativa de altas de dominio.
    if conexion.execute("PRAGMA foreign_key_check").fetchall():
        raise ErrorValidacion("La base contiene relaciones inválidas.")
    if conexion.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ErrorValidacion("La integridad SQLite no es correcta.")
    conteos = {tabla: conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
               for tabla in ("obra", "edicion", "autor", "sede", "socio", "ejemplar")}
    conteos["ejemplares_por_sede_propietaria"] = {fila[0]: fila[1] for fila in conexion.execute(
        "SELECT s.nombre, COUNT(e.id) FROM sede s LEFT JOIN ejemplar e ON e.sede_propietaria_id = s.id GROUP BY s.id")}
    return conteos


def preparar(manifiesto: str | Path, operativa: str | Path, demo: str | Path) -> dict:
    fuente = FuenteCatalogoLocal(manifiesto)
    validador = ValidadorCatalogoLocal()
    for candidato in fuente.iterar():
        evaluacion = validador.evaluar(candidato)
        if evaluacion.estado is not EstadoImportacion.VALIDADA:
            raise ErrorValidacion(f"La selección contiene una candidata sin aceptación automática: "
                                 f"{candidato.clave}: {evaluacion.alertas}")
    operativa, demo = Path(operativa).resolve(), Path(demo).resolve()
    if operativa == demo or (operativa.exists() and demo.exists() and operativa.samefile(demo)):
        raise ErrorValidacion("Las bases operativa y demo deben ser archivos independientes.")
    destinos = ((operativa, "OPERATIVA"), (demo, "DEMOSTRACION"))
    # Comprobar ambos destinos antes de escribir en cualquiera de ellos.
    marcadores = [_validar_destino(ruta, tipo, fuente) for ruta, tipo in destinos]
    resultado = {"politica": validador.VERSION, "seleccion": len(fuente.candidatos),
                 "portadas_locales": len(fuente.portadas), "bases": {}}
    for (ruta, tipo), marcador in zip(destinos, marcadores, strict=True):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        _guardar_marcador(ruta, marcador)
        with closing(conectar(ruta)) as conexion:
            migrar(conexion)
            obras, ediciones = ObraRepository(conexion), EdicionRepository(conexion)
            clasificaciones = ClasificacionRepository(conexion)
            servicio = ImportacionService(ImportacionRepository(conexion), obras, ediciones,
                AutorRepository(conexion), clasificaciones, validador=validador)
            clasificador = ClasificacionService(clasificaciones, obras)
            reglas = clasificador.preparar_reglas_catalogo_local()
            ediciones_demo, omitidas = [], []
            for candidato in fuente.iterar():
                registro = servicio.evaluar(candidato)
                if registro.estado is EstadoImportacion.VALIDADA:
                    edicion = servicio.integrar(registro.edicion_ol, reglas)
                else:
                    omitidas.append({"edicion": registro.edicion_ol, "estado": registro.estado.value,
                                      "motivo": registro.motivo})
                    edicion = ediciones.buscar_por_openlibrary(registro.edicion_ol)
                if edicion is not None:
                    ediciones_demo.append(edicion)
                    # Repetir también evalúa las materias ya preservadas de obras
                    # integradas. No reintegra ni sobreescribe metadatos o revisiones.
                    clasificador.procesar_materias(edicion.obra_id, (), reglas)
            if tipo == "DEMOSTRACION":
                if len(ediciones_demo) != len(fuente.candidatos):
                    raise ErrorValidacion("No se puede completar la demo: hay ediciones no incorporadas.")
                _sembrar_demo(conexion, ruta, marcador, sorted(ediciones_demo, key=lambda e: e.id_openlibrary))
            resultado["bases"][tipo] = {"ruta": str(ruta), **_resumen_verificado(conexion),
                                       "decisiones_manuales_conservadas_sin_integrar": omitidas}
    return resultado


def exportar_catalogo(fuente: FuenteCatalogoLocal, destino: Path):
    """Informe derivado para revisar bibliografía; nunca es la fuente de las altas."""
    campos = ("obra_ol", "edicion_ol", "titulo_obra", "titulo_es", "autores", "isbn_10", "isbn_13",
              "editorial", "portada_edicion_id", "portada_local", "url_obra", "url_edicion")
    with destino.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        for candidato in fuente.iterar():
            datos = ValidadorCatalogoLocal().evaluar(candidato).normalizados
            obra, edicion = datos["obra"], datos["edicion"]
            escritor.writerow(dict(zip(campos, (
                obra["id_openlibrary"], edicion["id_openlibrary"], obra["titulo_original"], edicion["titulo"],
                "; ".join(a["nombre"] + " (" + a["id_openlibrary"] + ")" for a in datos["autores"]),
                edicion["isbn_10"], edicion["isbn_13"], edicion["editorial"], edicion["portada_edicion_id"],
                str(fuente.portadas.get(edicion["portada_edicion_id"], "")),
                "https://openlibrary.org/works/" + obra["id_openlibrary"],
                "https://openlibrary.org/books/" + edicion["id_openlibrary"],
            ), strict=True)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifiesto", type=Path, default=RAIZ / "datos/catalogo_local/seleccion.json")
    parser.add_argument("--operativa", type=Path, default=RAIZ / "datos/generados/catalogo_local/operativa.db")
    parser.add_argument("--demo", type=Path, default=RAIZ / "datos/generados/catalogo_local/demo.db")
    args = parser.parse_args()
    try:
        resultado = preparar(args.manifiesto, args.operativa, args.demo)
        csv_destino = args.operativa.resolve().parent / "catalogo_auditable.csv"
        exportar_catalogo(FuenteCatalogoLocal(args.manifiesto), csv_destino)
        resultado["catalogo_csv"] = str(csv_destino)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    except (ErrorBiblioteca, OSError) as error:
        parser.exit(2, f"No se pudo preparar el catálogo local: {error}\n")


if __name__ == "__main__":
    main()
