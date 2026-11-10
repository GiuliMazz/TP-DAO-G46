"""Datos de presentación ficticios; no son entidades ni registros operativos."""

from dataclasses import dataclass

SEDES = ("Centro", "Norte", "Sur")


@dataclass(frozen=True)
class ObraMuestra:
    titulo: str
    original: str
    autor: str
    genero: str
    color: str
    acento: str
    disponibles: tuple[int, int, int]
    descripcion: str

    def cantidad_mostrada(self, sede: str) -> int:
        """Sólo leer cantidades estáticas de maqueta; no calcular disponibilidad real."""
        return sum(self.disponibles) if sede == "Todas" else self.disponibles[SEDES.index(sede)]


@dataclass(frozen=True)
class SocioMuestra:
    nombre: str
    dni: str
    contacto: str
    habilitado: bool


class DatosPrototipo:
    obras = (
        ObraMuestra("El ladrón del rayo", "The Lightning Thief", "Rick Riordan", "Fantasía", "#164C63", "#B5E2E4", (2, 1, 0),
                    "Una aventura de descubrimiento y mitología. Texto de muestra para revisar la ficha; no es una sinopsis importada."),
        ObraMuestra("Choque de reyes", "A Clash of Kings", "George R. R. Martin", "Fantasía épica", "#34453F", "#E1CB99", (1, 0, 1),
                    "Reinos, alianzas y personajes en conflicto. Descripción ilustrativa del prototipo."),
        ObraMuestra("La sangre de los elfos", "Krew elfów", "Andrzej Sapkowski", "Fantasía épica", "#6C443B", "#F1CFAB", (0, 1, 0),
                    "Un mundo de magia y decisiones difíciles. Descripción ilustrativa del prototipo."),
        ObraMuestra("La espada de la asesina", "The Assassin’s Blade", "Sarah J. Maas", "Fantasía", "#4F4664", "#DDCDE8", (1, 0, 0),
                    "Historias de una protagonista y sus primeros desafíos. Descripción ilustrativa del prototipo."),
        ObraMuestra("El ojo del mundo", "The Eye of the World", "Robert Jordan", "Fantasía épica", "#526460", "#E9D8B8", (1, 1, 0),
                    "El comienzo de un viaje en un universo fantástico. Descripción ilustrativa del prototipo."),
        ObraMuestra("Un mago de Terramar", "A Wizard of Earthsea", "Ursula K. Le Guin", "Fantasía", "#AA714C", "#FFE5B7", (0, 0, 0),
                    "Aprendizaje, nombres y magia entre islas. Descripción ilustrativa del prototipo."),
    )
    socios = (
        SocioMuestra("Ana Martínez", "12345678", "ana@example.test", True),
        SocioMuestra("Bruno Fernández", "23456789", "bruno@example.test", True),
        SocioMuestra("Camila López", "34567890", "camila@example.test", False),
        SocioMuestra("Diego Romero", "45678901", "diego@example.test", True),
    )

    def buscar_obras(self, texto="", genero="Todos", sede="Todas", disponibilidad="Todas"):
        texto = " ".join(texto.split()).casefold()
        return [o for o in self.obras
                if (not texto or any(texto in t.casefold() for t in (o.titulo, o.original, o.autor)))
                and (genero == "Todos" or o.genero == genero)
                and (disponibilidad == "Todas" or
                     (o.cantidad_mostrada(sede) > 0) == (disponibilidad == "Disponibles"))]

    def buscar_socios(self, texto="", estado="Todos"):
        texto = " ".join(texto.split()).casefold()
        return [s for s in self.socios if
                (not texto or any(texto in t.casefold() for t in (s.nombre, s.dni, s.contacto)))
                and (estado == "Todos" or s.habilitado == (estado == "Habilitados"))]
