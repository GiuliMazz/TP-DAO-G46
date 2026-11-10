"""Límites y normalización de consultas paginadas del primer módulo."""

from biblioteca.errores import ErrorValidacion


def validar_paginacion(limite: int, desplazamiento: int) -> None:
    if type(limite) is not int or not 1 <= limite <= 100:
        raise ErrorValidacion("El tamaño de página debe ser un entero entre 1 y 100.")
    if type(desplazamiento) is not int or desplazamiento < 0:
        raise ErrorValidacion("El desplazamiento debe ser un entero mayor o igual a cero.")


def filtro_nombre(nombre: str | None) -> str:
    if nombre is None:
        return ""
    if not isinstance(nombre, str):
        raise ErrorValidacion("El filtro de nombre debe ser texto.")
    return " ".join(nombre.split()).casefold()
