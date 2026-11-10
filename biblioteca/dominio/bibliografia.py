"""Validaciones bibliográficas compartidas, sin dependencias de fuentes externas."""

import re

from biblioteca.errores import ErrorValidacion


def texto_opcional(valor: str | None, campo: str) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ErrorValidacion(f"{campo} debe ser texto.")
    return valor.strip() or None


def entero_positivo_opcional(valor: int | None, campo: str) -> int | None:
    if valor is not None and (type(valor) is not int or valor <= 0):
        raise ErrorValidacion(f"{campo} debe ser un entero positivo.")
    return valor


def id_openlibrary(valor: str | None, sufijo: str) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str) or not re.fullmatch(r"OL[0-9]+" + sufijo, valor.strip()):
        raise ErrorValidacion(f"El ID de Open Library debe tener formato OL…{sufijo}.")
    return valor.strip()


def normalizar_isbn(valor: str | None, longitud: int) -> str | None:
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ErrorValidacion("El ISBN debe ingresarse como texto.")
    texto = valor.strip().upper()
    if not texto:
        return None
    if not re.fullmatch(r"[0-9](?:[0-9X\s-]*[0-9X])?", texto):
        raise ErrorValidacion("El ISBN contiene caracteres no permitidos.")
    isbn = re.sub(r"[\s-]", "", texto)
    if longitud == 10:
        if not re.fullmatch(r"[0-9]{9}[0-9X]", isbn):
            raise ErrorValidacion("El ISBN-10 debe contener nueve cifras y un dígito de control.")
        suma = sum((10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(isbn))
        divisor = 11
    elif longitud == 13:
        if not re.fullmatch(r"97[89][0-9]{10}", isbn):
            raise ErrorValidacion("El ISBN-13 debe tener trece cifras y prefijo 978 o 979.")
        suma = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(isbn))
        divisor = 10
    else:
        raise ErrorValidacion("Sólo se admiten ISBN de 10 o 13 cifras.")
    if suma % divisor:
        raise ErrorValidacion(f"El ISBN-{longitud} tiene un dígito de control incorrecto.")
    return isbn


def isbn13_desde_isbn10(isbn: str) -> str:
    """Equivalente para búsquedas; no modifica el ISBN-10 original guardado."""
    normalizado = normalizar_isbn(isbn, 10)
    if normalizado is None:
        raise ErrorValidacion("Se requiere un ISBN-10 para convertirlo.")
    base = "978" + normalizado[:9]
    suma = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(base))
    return base + str((-suma) % 10)
