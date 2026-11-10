"""Carga explícita y repetible de socios ficticios, exclusivamente en la demo."""

import argparse
from contextlib import closing
import json
from pathlib import Path
from uuid import UUID

from biblioteca.administracion_local import AdministracionLocal
from biblioteca.consultas_locales import BASE_DEMO
from biblioteca.errores import ErrorBiblioteca, ErrorValidacion
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.socio_service import SocioService
from herramientas.preparar_catalogo_local import _guardar_marcador


# Identidades de demostración, sin afirmar que estos números no existan realmente.
SOCIOS = (
    ("01", "90000001", "Demo · Ana Torres", "ana", True),
    ("02", "90000002", "Demo · Bruno Díaz", "bruno", True),
    ("03", "90000003", "Demo · Camila Ruiz", "camila", True),
    ("04", "90000004", "Demo · Diego López", "diego", True),
    ("05", "90000005", "Demo · Elena Suárez", "elena", False),
    ("06", "90000006", "Demo · Facundo Vera", "facundo", True),
    ("07", "90000007", "Demo · Gabriela Paz", "gabriela", False),
    ("08", "90000008", "Demo · Hugo Ríos", "hugo", True),
)


def preparar_socios(base=BASE_DEMO):
    a = AdministracionLocal(base)
    ruta_marca = a.base.with_suffix(a.base.suffix + ".tipo.json")
    try:
        marca = json.loads(ruta_marca.read_text(encoding="utf-8"))
        if marca.get("version") != 1 or marca.get("tipo") != "DEMOSTRACION":
            raise ValueError("No es una demo")
        semilla = marca.setdefault("socios_demo", {"version": 1, "registros": {}})
        ids = semilla["registros"]
        if semilla.get("version") != 1 or not isinstance(ids, dict) or set(ids) - {s[0] for s in SOCIOS}:
            raise ValueError("Marca de semilla incompatible")
        if len(set(ids.values())) != len(ids):
            raise ValueError("Identidades repetidas")
        for id in ids.values():
            UUID(id)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        raise ErrorValidacion("La carga de socios requiere una demo preparada y una marca válida.") from error

    creados = 0
    with closing(a._abrir_escritura()) as c:
        servicio = SocioService(SocioRepository(c))
        # Revisar todo antes de iniciar; no adoptar un DNI ajeno ni reemplazar datos.
        for clave, documento, *_ in SOCIOS:
            if clave in ids:
                servicio.obtener(ids[clave])
            elif servicio.buscar_por_documento(documento) is not None:
                raise ErrorValidacion(f"El DNI demo {documento} ya existe sin una marca de esta semilla. "
                                     "No se adopta ni sobrescribe; revisá el conflicto.")
        for clave, documento, nombre, contacto, habilitado in SOCIOS:
            if clave in ids:
                continue
            socio = servicio.registrar(documento, nombre, f"{contacto}@horizonte.example.test")
            if not habilitado:
                servicio.inhabilitar(socio.id)
            ids[clave] = str(socio.id)
            # Si falla el archivo tras un commit, repetir detecta el conflicto; no duplica.
            _guardar_marcador(a.base, marca)
            creados += 1
    return {"tipo": "DEMOSTRACION", "base": str(a.base), "creados": creados,
            "identidades_de_semilla": len(ids), "datos": "Socios ficticios; cambios manuales conservados"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE_DEMO)
    args = parser.parse_args()
    try:
        print(json.dumps(preparar_socios(args.base), ensure_ascii=False, indent=2))
    except (ErrorBiblioteca, OSError) as error:
        parser.exit(2, f"No se pudieron preparar los socios demo: {error}\n")


if __name__ == "__main__":
    main()
