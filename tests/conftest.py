"""Cada prueba dispone de una base temporal independiente."""

import pytest
from pathlib import Path

from biblioteca.persistencia.base_datos import conectar, migrar
from biblioteca.repositorios.sede_repository import SedeRepository
from biblioteca.repositorios.socio_repository import SocioRepository
from biblioteca.servicios.sede_service import SedeService
from biblioteca.servicios.socio_service import SocioService
from biblioteca.repositorios.autor_repository import AutorRepository
from biblioteca.repositorios.edicion_repository import EdicionRepository
from biblioteca.repositorios.obra_repository import ObraRepository
from biblioteca.servicios.catalogo_service import CatalogoService
from biblioteca.repositorios.ejemplar_repository import EjemplarRepository
from biblioteca.servicios.inventario_service import InventarioService
from biblioteca.repositorios.clasificacion_repository import ClasificacionRepository
from biblioteca.servicios.clasificacion_service import ClasificacionService
from biblioteca.repositorios.importacion_repository import ImportacionRepository
from biblioteca.servicios.importacion_service import ImportacionService


@pytest.fixture(scope="session")
def base_prevalidacion(tmp_path_factory):
    """Reproducir la muestra histórica sin depender de una SQLite local versionada."""
    from herramientas.openlibrary.preparar_catalogo import generar
    from herramientas.openlibrary.enriquecer_con_muestra_30 import enriquecer

    raiz = Path(__file__).resolve().parents[1]
    salida = tmp_path_factory.mktemp("prevalidacion-offline")
    generar(raiz / "datos/openlibrary/catalogo_exploratorio.json", salida, 100)
    base = salida / "catalogo_prevalidacion.db"
    enriquecer(base, raiz / "datos/openlibrary/respuestas_originales.json")
    return base


@pytest.fixture
def ruta_db(tmp_path):
    return tmp_path / "biblioteca.db"


@pytest.fixture
def conexion(ruta_db):
    conexion = conectar(ruta_db)
    migrar(conexion)
    yield conexion
    conexion.close()


@pytest.fixture
def sede_repository(conexion):
    return SedeRepository(conexion)


@pytest.fixture
def socio_repository(conexion):
    return SocioRepository(conexion)


@pytest.fixture
def sedes(sede_repository):
    return SedeService(sede_repository)


@pytest.fixture
def socios(socio_repository):
    return SocioService(socio_repository)


@pytest.fixture
def autor_repository(conexion):
    return AutorRepository(conexion)


@pytest.fixture
def obra_repository(conexion):
    return ObraRepository(conexion)


@pytest.fixture
def edicion_repository(conexion):
    return EdicionRepository(conexion)


@pytest.fixture
def catalogo(obra_repository, edicion_repository, autor_repository):
    return CatalogoService(obra_repository, edicion_repository, autor_repository)


@pytest.fixture
def ejemplar_repository(conexion):
    return EjemplarRepository(conexion)


@pytest.fixture
def inventario(ejemplar_repository, edicion_repository, sede_repository, obra_repository):
    return InventarioService(ejemplar_repository, edicion_repository, sede_repository, obra_repository)


@pytest.fixture
def clasificacion_repository(conexion):
    return ClasificacionRepository(conexion)


@pytest.fixture
def clasificaciones(clasificacion_repository, obra_repository):
    return ClasificacionService(clasificacion_repository, obra_repository)


@pytest.fixture
def importacion_repository(conexion):
    return ImportacionRepository(conexion)


@pytest.fixture
def importacion(importacion_repository, obra_repository, edicion_repository, autor_repository, clasificacion_repository):
    return ImportacionService(importacion_repository, obra_repository, edicion_repository, autor_repository,
                              clasificacion_repository)


@pytest.fixture
def candidato_ol():
    from biblioteca.importacion.modelos import CandidatoOpenLibrary
    return CandidatoOpenLibrary.desde_datos({
        "obra": {"id_openlibrary": "OL100W", "titulo_original": "Original de prueba",
                 "anio_primera_publicacion": 1980, "portada_obra_id": 900},
        "edicion": {"id_openlibrary": "OL100M", "obra_id": "OL100W", "titulo": "Edición española de prueba",
                    "isbn_10": "0306406152", "isbn_13": "9780306406157", "portada_edicion_id": 501,
                    "estado_validacion": "ENRIQUECIDA", "idioma_verificado": 1},
        "autores": [{"id_openlibrary": "OL100A", "nombre": "Autora de prueba"}],
        "materias": ["Fantasy fiction", "Magic -- Fiction"],
        "detalle": {
            "obra": {"key": "/works/OL100W", "title": "Original de prueba",
                     "authors": [{"author": {"key": "/authors/OL100A"}}],
                     "subjects": ["Fantasy fiction", "Magic -- Fiction"]},
            "edicion": {"key": "/books/OL100M", "title": "Edición española de prueba",
                        "works": [{"key": "/works/OL100W"}], "languages": [{"key": "/languages/spa"}],
                        "isbn_10": ["0306406152"], "isbn_13": ["9780306406157"], "covers": [501],
                        "publishers": ["Editorial de prueba"], "publish_date": "2001", "number_of_pages": 200},
        }, "origen": {"base": "fuente sintética"},
    })
