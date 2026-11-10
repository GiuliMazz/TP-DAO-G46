"""Recorrido 2A: títulos originales/españoles en una base temporal de demostración."""

from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from biblioteca import NOMBRE_RED
from biblioteca.dominio.edicion import Edicion
from biblioteca.dominio.obra import Obra
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.servicios.catalogo_service import CatalogoService


def main() -> None:
    print(f"{NOMBRE_RED} — demostración de catálogo 2A")
    print("Ediciones de ejemplo, sin afirmar metadatos de una edición real de Open Library.\n")
    with TemporaryDirectory(prefix="horizonte_catalogo_") as carpeta:
        ruta = Path(carpeta) / "biblioteca.db"
        with closing(conectar(ruta)) as conexion:
            migrar(conexion)
            catalogo = CatalogoService(ObraRepository(conexion), EdicionRepository(conexion),
                                       AutorRepository(conexion))
            autor = catalogo.registrar_autor("Ursula K. Le Guin")
            obra = Obra("A Wizard of Earthsea", [autor.id])
            catalogo.registrar_libro(obra, Edicion(obra.id, "Un mago de Terramar"))
            alternativa = catalogo.registrar_edicion(obra.id, "Terramar I: Un mago de Terramar")
            for titulo in ("Mago de Terramar", "Wizard", "Terramar I"):
                fichas = catalogo.listar_obras(titulo=titulo)
                print(f"Búsqueda {titulo!r}: {len(fichas)} obra, título: {fichas[0].titulo_mostrado}")
            catalogo.seleccionar_edicion_preferida(obra.id, alternativa.id)
        with closing(conectar(ruta)) as conexion:
            catalogo = CatalogoService(ObraRepository(conexion), EdicionRepository(conexion),
                                       AutorRepository(conexion))
            detalle = catalogo.obtener_detalle(obra.id)
            print("\nAl reabrir, título mostrado:", detalle.titulo_mostrado)
            print("Título original:", detalle.obra.titulo_original)
            print("Ediciones registradas:", detalle.cantidad_ediciones)
            print("La demostración no creó ejemplares físicos ni importó registros reales.")


if __name__ == "__main__":
    main()
