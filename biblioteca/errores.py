"""Errores que los casos de uso pueden comunicar a la interfaz."""


class ErrorBiblioteca(Exception):
    """Error esperado de la aplicación."""


class ErrorValidacion(ErrorBiblioteca, ValueError):
    """Un dato no satisface las reglas del módulo."""


class RegistroDuplicado(ErrorBiblioteca):
    """Una identidad o un dato único ya están registrados."""


class RegistroNoEncontrado(ErrorBiblioteca):
    """El registro solicitado no existe."""


class PosibleDuplicado(ErrorBiblioteca):
    """Coincidencia que exige revisión; no demuestra identidad bibliográfica."""


class ErrorPersistencia(ErrorBiblioteca):
    """No fue posible completar una operación de almacenamiento."""
