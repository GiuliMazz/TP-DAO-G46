"""Recorrido de etapa 1 con datos ficticios en una base temporal."""

from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from biblioteca import NOMBRE_RED
from biblioteca.errores import RegistroDuplicado
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.sede_service import SedeService
from biblioteca.servicios.socio_service import SocioService


def main() -> None:
    print(f"{NOMBRE_RED} — demostración de etapa 1")
    print("Datos ficticios. La base es temporal y se elimina al terminar.\n")
    with TemporaryDirectory(prefix="horizonte_demo_") as carpeta:
        ruta = Path(carpeta) / "biblioteca.db"
        with closing(conectar(ruta)) as conexion:
            migrar(conexion)
            sedes = SedeService(SedeRepository(conexion))
            socios = SocioService(SocioRepository(conexion))
            for numero, nombre in enumerate(("Norte", "Centro", "Sur"), start=1):
                sedes.registrar(
                    nombre, f"Dirección ficticia {numero}",
                    f"{nombre.lower()}@horizonte.example", "Lunes a viernes de 9 a 18",
                )
            print("Sedes:", ", ".join(sede.nombre for sede in sedes.listar()))
            socio = socios.registrar("12.345.678", "Socio de demostración", "demo@example.test")
            socios.inhabilitar(socio.id)
            print("Estado después de inhabilitar:", socios.obtener(socio.id).estado.value)
            try:
                socios.registrar("12345678", "Otro registro", "demo@example.test")
            except RegistroDuplicado as error:
                print("Alta duplicada rechazada:", error)
            socios.habilitar(socio.id)
        with closing(conectar(ruta)) as conexion:
            recuperado = SocioService(SocioRepository(conexion)).obtener(socio.id)
            print("Estado al reabrir la base:", recuperado.estado.value)
            print("UUID conservado:", recuperado.id == socio.id)


if __name__ == "__main__":
    main()
