"""Una sede de la red, con identidad estable y baja lógica."""

from uuid import UUID, uuid4

from biblioteca.dominio.validacion import texto_obligatorio, validar_uuid
from biblioteca.errores import ErrorValidacion


class Sede:
    def __init__(
        self,
        nombre: str,
        direccion: str,
        contacto: str,
        horarios: str,
        *,
        id: UUID | None = None,
        activa: bool = True,
    ) -> None:
        if not isinstance(activa, bool):
            raise ErrorValidacion("El estado activo de la sede debe ser booleano.")
        self._id = uuid4() if id is None else validar_uuid(id)
        self.actualizar_datos(nombre, direccion, contacto, horarios)
        self._activa = activa

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def nombre_normalizado(self) -> str:
        return self._nombre.casefold()

    @property
    def direccion(self) -> str:
        return self._direccion

    @property
    def contacto(self) -> str:
        return self._contacto

    @property
    def horarios(self) -> str:
        return self._horarios

    @property
    def activa(self) -> bool:
        return self._activa

    def actualizar_datos(
        self, nombre: str, direccion: str, contacto: str, horarios: str
    ) -> None:
        # Validar todo antes de modificar: un error no deja cambios parciales.
        datos = (
            texto_obligatorio(nombre, "Nombre"),
            texto_obligatorio(direccion, "Dirección"),
            texto_obligatorio(contacto, "Contacto"),
            texto_obligatorio(horarios, "Horarios"),
        )
        self._nombre, self._direccion, self._contacto, self._horarios = datos

    def activar(self) -> None:
        self._activa = True

    def dar_de_baja(self) -> None:
        self._activa = False

    def esta_activa(self) -> bool:
        return self._activa
