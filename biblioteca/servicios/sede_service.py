"""Administración de sedes sin dependencia de la interfaz gráfica."""

from uuid import UUID

from biblioteca.dominio.sede import Sede
from biblioteca.dominio.validacion import validar_uuid
from biblioteca.errores import RegistroDuplicado, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import transaccion
from biblioteca.repositorios.sede_repository import SedeRepository


class SedeService:
    def __init__(self, repositorio: SedeRepository) -> None:
        self._repositorio = repositorio

    def registrar(self, nombre: str, direccion: str, contacto: str, horarios: str) -> Sede:
        sede = Sede(nombre, direccion, contacto, horarios)
        with transaccion(self._repositorio.conexion):
            self._comprobar_nombre(sede)
            self._repositorio.agregar(sede)
        return sede

    def obtener(self, id: UUID | str) -> Sede:
        sede = self._repositorio.obtener(validar_uuid(id))
        if sede is None:
            raise RegistroNoEncontrado("La sede no existe.")
        return sede

    def modificar(
        self, id: UUID | str, nombre: str, direccion: str, contacto: str, horarios: str
    ) -> Sede:
        with transaccion(self._repositorio.conexion):
            sede = self.obtener(id)
            sede.actualizar_datos(nombre, direccion, contacto, horarios)
            self._comprobar_nombre(sede)
            self._repositorio.actualizar(sede)
        return sede

    def dar_de_baja(self, id: UUID | str) -> Sede:
        with transaccion(self._repositorio.conexion):
            sede = self.obtener(id)
            sede.dar_de_baja()
            self._repositorio.actualizar(sede)
        return sede

    def activar(self, id: UUID | str) -> Sede:
        with transaccion(self._repositorio.conexion):
            sede = self.obtener(id)
            sede.activar()
            self._repositorio.actualizar(sede)
        return sede

    def listar(
        self, *, activa: bool | None = None, nombre: str | None = None,
        limite: int = 50, desplazamiento: int = 0,
    ) -> list[Sede]:
        return self._repositorio.listar(
            activa=activa, nombre=nombre, limite=limite, desplazamiento=desplazamiento
        )

    def _comprobar_nombre(self, sede: Sede) -> None:
        existente = self._repositorio.buscar_por_nombre_normalizado(sede.nombre_normalizado)
        if existente is not None and existente.id != sede.id:
            raise RegistroDuplicado("Ya existe una sede con ese nombre, incluso si está de baja.")
