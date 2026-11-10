"""Reglas de formato compartidas por las entidades del primer módulo."""

import re
from uuid import UUID

from biblioteca.errores import ErrorValidacion


def texto_obligatorio(valor: str, campo: str) -> str:
    if not isinstance(valor, str):
        raise ErrorValidacion(f"{campo} debe ser texto.")
    texto = " ".join(valor.split())
    if not texto:
        raise ErrorValidacion(f"{campo} es obligatorio.")
    return texto


def normalizar_dni(documento: str) -> str:
    texto = texto_obligatorio(documento, "DNI")
    if not re.fullmatch(r"[0-9](?:[0-9.\-\s]*[0-9])?", texto):
        raise ErrorValidacion("El DNI debe contener números y sólo separadores entre cifras.")
    return re.sub(r"[.\-\s]", "", texto)


def validar_uuid(valor: UUID | str) -> UUID:
    if isinstance(valor, UUID):
        return valor
    if isinstance(valor, str):
        try:
            return UUID(valor)
        except ValueError:
            pass
    raise ErrorValidacion("El identificador debe ser un UUID válido.")
