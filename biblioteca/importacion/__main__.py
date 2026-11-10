"""Evaluar e integrar la muestra local, conservando fuente y datos operativos."""

import argparse
from contextlib import closing
import json
from itertools import chain
from pathlib import Path

from biblioteca.errores import ErrorBiblioteca, ErrorValidacion, PosibleDuplicado
from biblioteca.importacion.fuente_openlibrary import FuenteOpenLibrary
from biblioteca.importacion.modelos import EstadoImportacion
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.importacion_repository import ImportacionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.servicios.clasificacion_service import ClasificacionService
from biblioteca.servicios.importacion_service import ImportacionService


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fuente", type=Path, required=True, help="SQLite de preparación, sólo lectura")
    parser.add_argument("--detalles", type=Path, help="JSON originales de las ediciones")
    parser.add_argument("--destino", type=Path, required=True, help="SQLite operativa separada de la fuente")
    parser.add_argument("--limite", type=int, default=1000)
    parser.add_argument("--solo-evaluar", action="store_true")
    args = parser.parse_args()
    if args.limite < 1:
        parser.error("--limite debe ser positivo")
    destino = args.destino.resolve()
    if destino == args.fuente.resolve() or (args.detalles is not None and destino == args.detalles.resolve()):
        parser.error("El destino debe ser distinto de los archivos fuente")
    try:
        fuente = FuenteOpenLibrary(args.fuente, args.detalles)
        # Abrir/validar la fuente antes de crear el destino.
        candidatas = fuente.iterar(limite=args.limite)
        primera = next(candidatas, None)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with closing(conectar(destino)) as conexion:
            migrar(conexion)
            obras, ediciones, autores = ObraRepository(conexion), EdicionRepository(conexion), AutorRepository(conexion)
            clasificaciones = ClasificacionRepository(conexion)
            servicio = ImportacionService(ImportacionRepository(conexion), obras, ediciones, autores, clasificaciones)
            reglas = () if args.solo_evaluar else ClasificacionService(clasificaciones, obras).preparar_reglas_iniciales()
            conflictos = []
            for candidata in chain((primera,) if primera is not None else (), candidatas):
                registro = servicio.evaluar(candidata)
                if not args.solo_evaluar and registro.estado is EstadoImportacion.VALIDADA:
                    try:
                        servicio.integrar(registro.edicion_ol, reglas)
                    except (PosibleDuplicado, ErrorValidacion) as error:
                        conflictos.append({"edicion_ol": registro.edicion_ol, "motivo": str(error)})
            resultado = {**servicio.resumen(), "destino": str(destino), "conflictos_integracion": conflictos}
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
            return 2 if conflictos else 0
    except (ErrorBiblioteca, OSError) as error:
        parser.exit(2, f"No se pudo completar la importación: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
