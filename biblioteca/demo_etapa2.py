"""Recorrido consolidado con bibliografía real y operaciones ficticias temporales."""

from contextlib import closing
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from biblioteca.dominio.clasificacion import EstadoClasificacion
from biblioteca.dominio.ejemplar import CondicionFisica
from biblioteca.importacion.fuente_openlibrary import FuenteOpenLibrary
from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.repositorios.importacion_repository import ImportacionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.servicios.clasificacion_service import ClasificacionService
from biblioteca.servicios.importacion_service import ImportacionService
from biblioteca.servicios.inventario_service import InventarioService
from biblioteca.servicios.sede_service import SedeService
from biblioteca.servicios.socio_service import SocioService


def _servicios(c):
    obras, ediciones, autores = ObraRepository(c), EdicionRepository(c), AutorRepository(c)
    clasificaciones = ClasificacionRepository(c)
    return (CatalogoService(obras, ediciones, autores),
            InventarioService(EjemplarRepository(c), ediciones, SedeRepository(c), obras),
            ClasificacionService(clasificaciones, obras),
            ImportacionService(ImportacionRepository(c), obras, ediciones, autores, clasificaciones),
            SedeService(SedeRepository(c)), SocioService(SocioRepository(c)))


def demostrar(ruta: Path, fuente: FuenteOpenLibrary) -> dict:
    """Trabajar exclusivamente sobre un destino nuevo; comprobar persistencia al reabrir."""
    if Path(ruta).exists():
        raise ValueError("La demostración requiere una base nueva.")
    with closing(fuente.iterar()) as candidatas:
        candidata = next(c for c in candidatas if c.clave == "OL25440625M")
    with closing(conectar(ruta)) as c:
        migrar(c)
        catalogo, inventario, clasificacion, importador, sedes, socios = _servicios(c)
        centro, norte, sur = [sedes.registrar(n, "Dirección de demostración", "demo@example.test", "9 a 18")
                              for n in ("Centro", "Norte", "Sur")]
        socio = socios.registrar("12.345.678", "Socio ficticio de demostración", "demo@example.test")
        socios.inhabilitar(socio.id)
        reglas = clasificacion.preparar_reglas_iniciales()
        importador.evaluar(candidata)
        primera = importador.integrar(candidata.clave, reglas)
        obra = catalogo.obtener_obra(primera.obra_id)
        originales = catalogo.listar_obras(titulo=obra.titulo_original)
        espanoles = catalogo.listar_obras(titulo=primera.titulo)
        if [f.id for f in originales] != [obra.id] or [f.id for f in espanoles] != [obra.id]:
            raise AssertionError("El catálogo no integra ambos títulos en una única obra")
        # Esta segunda edición y las copias son ficticias; no se presentan como OL.
        segunda = catalogo.registrar_edicion(obra.id, "Otra edición española (demostración)")
        catalogo.seleccionar_edicion_preferida(obra.id, segunda.id)
        apta = inventario.registrar("DEMO-CENTRO-1", primera.id, centro.id)
        daniada = inventario.registrar("DEMO-CENTRO-2", segunda.id, centro.id, condicion_fisica=CondicionFisica.DANIADO)
        norte_apta = inventario.registrar("DEMO-NORTE-1", segunda.id, norte.id)
        inicial = {f.nombre_sede: f.disponibles for f in inventario.consultar_disponibilidad(obra.id)}
        if inicial != {"Centro": 1, "Norte": 1, "Sur": 0}:
            raise AssertionError("Las ediciones/autores multiplicaron copias o alteraron disponibilidad")
        inventario.registrar_condicion(apta.id, CondicionFisica.DANIADO)
        inventario.dar_de_baja(daniada.id)
        sedes.dar_de_baja(norte.id)
        # Decisión humana SIMULADA de prueba, no certificación bibliográfica real.
        genero = reglas[0].termino_id
        clasificacion.proponer(obra.id, genero, "Propuesta simulada para comprobar revisión")
        clasificacion.revisar(obra.id, genero, EstadoClasificacion.RECHAZADO, "Revisión simulada en la demostración")
        titulo_corregido = "El ladrón del rayo (corrección de demostración)"
        catalogo.modificar_edicion(primera.id, titulo_corregido)
    with closing(conectar(ruta)) as c:
        catalogo, inventario, clasificacion, importador, sedes, socios = _servicios(c)
        importador.evaluar(candidata)
        recuperada = importador.integrar(candidata.clave, reglas)
        detalle = catalogo.obtener_detalle(obra.id)
        final = {f.nombre_sede: f.disponibles for f in inventario.consultar_disponibilidad(obra.id)}
        checks = (recuperada.id == primera.id, recuperada.obra_id == obra.id,
                  recuperada.titulo == titulo_corregido, detalle.cantidad_ediciones == 2,
                  detalle.obra.edicion_preferida_id == segunda.id,
                  not socios.obtener(socio.id).esta_habilitado(), not sedes.obtener(norte.id).esta_activa(),
                  sedes.obtener(sur.id).esta_activa(),
                  inventario.obtener(norte_apta.id).sede_propietaria_id == norte.id,
                  len(inventario.listar(obra_id=obra.id)) == 3,
                  clasificacion.obtener(obra.id, genero).decision.estado is EstadoClasificacion.RECHAZADO,
                  catalogo.listar_obras(genero_id=genero) == [], final == {"Centro": 0, "Norte": 0, "Sur": 0})
        if not all(checks):
            raise AssertionError("El recorrido no conservó identidades, decisiones o datos operativos")
        return {"bibliografia_real": primera.id_openlibrary, "operaciones": "DE DEMOSTRACIÓN, no movimientos reales",
                "disponibilidad_inicial": inicial, "disponibilidad_final": final,
                "ediciones": detalle.cantidad_ediciones, "ejemplares": 3,
                "reimportacion_conserva_datos": True, "persistencia_tras_reabrir": True,
                "socio": socios.obtener(socio.id).estado.value, "genero": "RECHAZADO (revisión simulada)"}


def main() -> None:
    raiz = Path(__file__).resolve().parents[1]
    fuente = FuenteOpenLibrary(raiz / "datos/generados/prevalidacion/catalogo_prevalidacion.db",
                               raiz / "datos/openlibrary/respuestas_originales.json")
    with TemporaryDirectory(prefix="horizonte-consolidacion-") as carpeta:
        resultado = demostrar(Path(carpeta) / "demo.db", fuente)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    print("La base temporal se eliminó. Las fuentes y la base de 2D no se modificaron.")


if __name__ == "__main__":
    main()
