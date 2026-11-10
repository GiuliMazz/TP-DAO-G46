"""Recorrido 2B con copias ficticias y SQLite temporal."""

from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from biblioteca import NOMBRE_RED
from biblioteca.dominio.ejemplar import CondicionFisica
from biblioteca.errores import RegistroDuplicado
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.inventario_service import InventarioService
from biblioteca.servicios.sede_service import SedeService


def main() -> None:
    print(f"{NOMBRE_RED} — demostración de inventario 2B")
    print("Datos y copias ficticios en una base temporal.\n")
    with TemporaryDirectory(prefix="horizonte_inventario_") as carpeta:
        ruta = Path(carpeta) / "biblioteca.db"
        with closing(conectar(ruta)) as conexion:
            migrar(conexion)
            sedes = SedeService(SedeRepository(conexion))
            centro = sedes.registrar("Centro", "Calle ficticia 1", "Contacto", "9 a 18")
            norte = sedes.registrar("Norte", "Calle ficticia 2", "Contacto", "9 a 18")
            sedes.registrar("Sur", "Calle ficticia 3", "Contacto", "9 a 18")
            catalogo = CatalogoService(ObraRepository(conexion), EdicionRepository(conexion),
                                       AutorRepository(conexion))
            autor = catalogo.registrar_autor("Autora de demostración")
            obra = catalogo.registrar_obra("Obra de demostración", [autor.id])
            edicion = catalogo.registrar_edicion(obra.id, "Edición española de demostración")
            inventario = InventarioService(EjemplarRepository(conexion), EdicionRepository(conexion),
                                           SedeRepository(conexion), ObraRepository(conexion))
            copia = inventario.registrar("HZ-0001", edicion.id, centro.id)
            inventario.registrar("HZ-0002", edicion.id, centro.id,
                                  condicion_fisica=CondicionFisica.DANIADO)
            inventario.registrar("HZ-0003", edicion.id, norte.id)
            baja = inventario.registrar("HZ-0004", edicion.id, norte.id)
            inventario.dar_de_baja(baja.id)
            for fila in inventario.consultar_disponibilidad(obra.id):
                print(f"{fila.nombre_sede}: propios={fila.total_propios}, "
                      f"ubicados={fila.total_ubicados}, bajas={fila.bajas_ubicadas}, "
                      f"disponibles={fila.disponibles}")
            try:
                inventario.registrar("hz-0001", edicion.id, norte.id)
            except RegistroDuplicado as error:
                print("\nCódigo duplicado rechazado:", error)
            sedes.dar_de_baja(centro.id)
            resumen = inventario.consultar_disponibilidad(obra.id, sede_id=centro.id)[0]
            print("Disponibles en Centro después de su baja:", resumen.disponibles)
        with closing(conectar(ruta)) as conexion:
            recuperada = EjemplarRepository(conexion).obtener(copia.id)
            print("UUID y propietaria conservados al reabrir:",
                  recuperada.id == copia.id and recuperada.sede_propietaria_id == centro.id)
            print("El registro del ejemplar dado de baja sigue existiendo:",
                  EjemplarRepository(conexion).obtener(baja.id) is not None)


if __name__ == "__main__":
    main()
