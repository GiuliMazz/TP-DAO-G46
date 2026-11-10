"""Altas explícitas de copias, condición física, baja y consulta por sede."""

from uuid import UUID

from biblioteca.dominio.ejemplar import (
    CondicionFisica, Ejemplar, SituacionOperativa, normalizar_codigo_inventario,
)
from biblioteca.dominio.validacion import validar_uuid
from biblioteca.errores import ErrorValidacion, RegistroDuplicado, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import transaccion
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.resultados_inventario import DisponibilidadSede


class InventarioService:
    def __init__(
        self, ejemplares: EjemplarRepository, ediciones: EdicionRepository,
        sedes: SedeRepository, obras: ObraRepository,
    ) -> None:
        if any(repo.conexion is not ejemplares.conexion for repo in (ediciones, sedes, obras)):
            raise ErrorValidacion("Los repositorios de inventario deben compartir la misma conexión.")
        self._ejemplares, self._ediciones = ejemplares, ediciones
        self._sedes, self._obras = sedes, obras
        self._conexion = ejemplares.conexion

    def registrar(
        self, codigo_inventario: str, edicion_id: UUID | str, sede_id: UUID | str, *,
        condicion_fisica: CondicionFisica = CondicionFisica.APTO,
    ) -> Ejemplar:
        id_edicion, id_sede = validar_uuid(edicion_id), validar_uuid(sede_id)
        ejemplar = Ejemplar(codigo_inventario, id_edicion, id_sede,
                            sede_actual_id=id_sede, condicion_fisica=condicion_fisica)
        with transaccion(self._conexion):
            sede = self._sedes.obtener(id_sede)
            if sede is None:
                raise RegistroNoEncontrado("La sede no existe.")
            if not sede.esta_activa():
                raise ErrorValidacion("No se puede registrar un ejemplar en una sede dada de baja.")
            edicion = self._ediciones.obtener(id_edicion)
            if edicion is None:
                raise RegistroNoEncontrado("La edición no existe.")
            obra = self._obras.obtener(edicion.obra_id)
            if obra is None or not obra.autor_ids:
                raise ErrorValidacion("El ejemplar requiere una edición y obra con autores identificados.")
            if self._ejemplares.buscar_por_codigo(ejemplar.codigo_inventario) is not None:
                raise RegistroDuplicado("El código de inventario ya está registrado, incluso si está de baja.")
            self._ejemplares.agregar(ejemplar)
        return ejemplar

    def obtener(self, id: UUID | str) -> Ejemplar:
        ejemplar = self._ejemplares.obtener(validar_uuid(id))
        if ejemplar is None:
            raise RegistroNoEncontrado("El ejemplar no existe.")
        return ejemplar

    def buscar_por_codigo(self, codigo: str) -> Ejemplar | None:
        return self._ejemplares.buscar_por_codigo(normalizar_codigo_inventario(codigo))

    def registrar_condicion(self, id: UUID | str, condicion: CondicionFisica) -> Ejemplar:
        with transaccion(self._conexion):
            ejemplar = self.obtener(id)
            ejemplar.registrar_condicion(condicion)
            self._ejemplares.actualizar(ejemplar)
        return ejemplar

    def dar_de_baja(self, id: UUID | str) -> Ejemplar:
        with transaccion(self._conexion):
            ejemplar = self.obtener(id)
            ejemplar.dar_de_baja()
            self._ejemplares.actualizar(ejemplar)
        return ejemplar

    def listar(
        self, *, obra_id: UUID | str | None = None, edicion_id: UUID | str | None = None,
        sede_actual_id: UUID | str | None = None, sede_propietaria_id: UUID | str | None = None,
        condicion_fisica: CondicionFisica | None = None,
        situacion_operativa: SituacionOperativa | None = None, solo_disponibles: bool = False,
        limite: int = 50, desplazamiento: int = 0,
    ) -> list[Ejemplar]:
        return self._ejemplares.listar(
            obra_id=obra_id, edicion_id=edicion_id, sede_actual_id=sede_actual_id,
            sede_propietaria_id=sede_propietaria_id, condicion_fisica=condicion_fisica,
            situacion_operativa=situacion_operativa, solo_disponibles=solo_disponibles,
            limite=limite, desplazamiento=desplazamiento,
        )

    def consultar_disponibilidad(
        self, obra_id: UUID | str, *, sede_id: UUID | str | None = None,
        limite: int = 50, desplazamiento: int = 0,
    ) -> list[DisponibilidadSede]:
        id_obra = validar_uuid(obra_id)
        id_sede = validar_uuid(sede_id) if sede_id is not None else None
        if self._obras.obtener(id_obra) is None:
            raise RegistroNoEncontrado("La obra no existe.")
        if id_sede is not None and self._sedes.obtener(id_sede) is None:
            raise RegistroNoEncontrado("La sede no existe.")
        return self._ejemplares.disponibilidad_por_sede(
            id_obra, sede_id=id_sede, limite=limite, desplazamiento=desplazamiento
        )
