"""Demostración sintética temporal: python -m biblioteca.demo_clasificacion."""

from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from biblioteca.dominio.clasificacion import EstadoClasificacion
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.clasificacion_service import ClasificacionService


def main() -> None:
    with TemporaryDirectory(prefix="horizonte-clasificacion-") as carpeta:
        with closing(conectar(Path(carpeta) / "demo.db")) as conexion:
            migrar(conexion)
            obras = ObraRepository(conexion)
            catalogo = CatalogoService(obras, EdicionRepository(conexion), AutorRepository(conexion))
            clasificacion = ClasificacionService(ClasificacionRepository(conexion), obras)
            reglas = clasificacion.preparar_reglas_iniciales()
            autor = catalogo.registrar_autor("Autora ficticia")
            obra = catalogo.registrar_obra("Historia de prueba", [autor.id])
            catalogo.registrar_edicion(obra.id, "Historia de prueba en español")
            materias = ["Fantasy fiction", "Magic -- Fiction", "Young adult fiction"]
            clasificacion.procesar_materias(obra.id, materias, reglas)
            print("Datos sintéticos; base temporal. Clasificaciones automáticas:")
            for c in clasificacion.listar(obra.id):
                print(f"  {c.termino.tipo.value}: {c.termino.nombre} ({c.decision.estado.value})")
            genero_id = reglas[0].termino_id
            print(f"Obras filtradas por Fantasía: {len(catalogo.listar_obras(genero_id=genero_id))}")
            clasificacion.revisar(obra.id, genero_id, EstadoClasificacion.RECHAZADO,
                                  "Ejemplo de corrección humana tras consultar la edición.")
            clasificacion.procesar_materias(obra.id, materias, reglas)
            print(f"Después de revisar y reprocesar: {clasificacion.obtener(obra.id, genero_id).decision.estado.value}")
            print(f"Decisiones conservadas: {len(clasificacion.historial(obra.id, genero_id))}")
            print(f"Ejemplares creados: {conexion.execute('SELECT COUNT(*) FROM ejemplar').fetchone()[0]}")


if __name__ == "__main__":
    main()
