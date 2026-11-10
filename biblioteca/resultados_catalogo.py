"""Resultados de consulta: no cargan todas las ediciones ni el inventario."""

from dataclasses import dataclass
from uuid import UUID

from biblioteca.dominio.autor import Autor
from biblioteca.dominio.edicion import Edicion
from biblioteca.dominio.obra import Obra


@dataclass(frozen=True)
class FichaObra:
    id: UUID
    titulo_mostrado: str
    titulo_original: str
    edicion_preferida_id: UUID | None
    autores: tuple[str, ...]
    cantidad_ediciones: int


@dataclass(frozen=True)
class EntradaCatalogo:
    """Proyección de una obra para una página, sin cargar todas sus copias."""

    ficha: FichaObra
    portada_edicion_id: int | None
    generos: tuple[str, ...]
    disponibles: int


@dataclass(frozen=True)
class PaginaCatalogo:
    obras: tuple[EntradaCatalogo, ...]
    total: int
    limite: int
    desplazamiento: int
    sede_id: UUID | None


@dataclass(frozen=True)
class DetalleObra:
    obra: Obra
    autores: tuple[Autor, ...]
    edicion_preferida: Edicion | None
    cantidad_ediciones: int

    @property
    def titulo_mostrado(self) -> str:
        return self.edicion_preferida.titulo if self.edicion_preferida else self.obra.titulo_original
