"""Altas, consultas y habilitación de socios de toda la red."""

from uuid import UUID

from biblioteca.dominio.socio import EstadoSocio, Socio
from biblioteca.dominio.validacion import normalizar_dni, validar_uuid
from biblioteca.errores import RegistroDuplicado, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import transaccion
from biblioteca.repositorios.socio_repository import SocioRepository


class SocioService:
    def __init__(self, repositorio: SocioRepository) -> None:
        self._repositorio = repositorio

    def registrar(self, documento: str, nombre_completo: str, contacto: str) -> Socio:
        socio = Socio(documento, nombre_completo, contacto)
        with transaccion(self._repositorio.conexion):
            self._comprobar_documento(socio)
            self._repositorio.agregar(socio)
        return socio

    def obtener(self, id: UUID | str) -> Socio:
        socio = self._repositorio.obtener(validar_uuid(id))
        if socio is None:
            raise RegistroNoEncontrado("El socio no existe.")
        return socio

    def buscar_por_documento(self, documento: str) -> Socio | None:
        return self._repositorio.buscar_por_documento(normalizar_dni(documento))

    def modificar(
        self, id: UUID | str, documento: str, nombre_completo: str, contacto: str
    ) -> Socio:
        with transaccion(self._repositorio.conexion):
            socio = self.obtener(id)
            socio.actualizar_datos(documento, nombre_completo, contacto)
            self._comprobar_documento(socio)
            self._repositorio.actualizar(socio)
        return socio

    def inhabilitar(self, id: UUID | str) -> Socio:
        with transaccion(self._repositorio.conexion):
            socio = self.obtener(id)
            socio.inhabilitar()
            self._repositorio.actualizar(socio)
        return socio

    def habilitar(self, id: UUID | str) -> Socio:
        with transaccion(self._repositorio.conexion):
            socio = self.obtener(id)
            socio.habilitar()
            self._repositorio.actualizar(socio)
        return socio

    def listar(
        self, *, estado: EstadoSocio | None = None, nombre: str | None = None,
        texto: str | None = None, limite: int = 50, desplazamiento: int = 0,
    ) -> list[Socio]:
        return self._repositorio.listar(
            estado=estado, nombre=nombre, texto=texto, limite=limite, desplazamiento=desplazamiento
        )

    def _comprobar_documento(self, socio: Socio) -> None:
        existente = self._repositorio.buscar_por_documento(socio.documento)
        if existente is not None and existente.id != socio.id:
            raise RegistroDuplicado("Ya existe un socio con ese DNI, incluso si está inhabilitado.")
