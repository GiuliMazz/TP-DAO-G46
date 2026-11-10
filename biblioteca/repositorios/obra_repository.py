"""Obras y búsqueda por títulos originales o de cualquier edición española."""

import sqlite3
from uuid import UUID

from biblioteca.dominio.obra import Obra
from biblioteca.dominio.validacion import validar_uuid
from biblioteca.errores import ErrorValidacion, RegistroNoEncontrado
from biblioteca.persistencia.base_datos import ejecutar
from biblioteca.repositorios.consultas import filtro_nombre, validar_paginacion
from biblioteca.resultados_catalogo import EntradaCatalogo, FichaObra, PaginaCatalogo


class ObraRepository:
    def __init__(self, conexion: sqlite3.Connection) -> None:
        self.conexion = conexion

    def agregar(self, obra: Obra) -> None:
        ejecutar(self.conexion,
                 """INSERT INTO obra (id, id_openlibrary, titulo_original, titulo_normalizado,
                    descripcion_original, anio_primera_publicacion, portada_obra_id, edicion_preferida_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (str(obra.id), obra.id_openlibrary, *self._datos(obra)))
        self._guardar_autores(obra)

    def actualizar(self, obra: Obra) -> None:
        cursor = ejecutar(self.conexion,
                          """UPDATE obra SET titulo_original = ?, titulo_normalizado = ?,
                             descripcion_original = ?, anio_primera_publicacion = ?,
                             portada_obra_id = ?, edicion_preferida_id = ? WHERE id = ?""",
                          (*self._datos(obra), str(obra.id)))
        if cursor.rowcount != 1:
            raise RegistroNoEncontrado("La obra no existe.")
        ejecutar(self.conexion, "DELETE FROM obra_autor WHERE obra_id = ?", (str(obra.id),))
        self._guardar_autores(obra)

    def obtener(self, id: UUID) -> Obra | None:
        fila = ejecutar(self.conexion, "SELECT * FROM obra WHERE id = ?", (str(id),)).fetchone()
        return self._reconstruir(fila) if fila else None

    def buscar_por_openlibrary(self, id_ol: str) -> Obra | None:
        fila = ejecutar(self.conexion, "SELECT * FROM obra WHERE id_openlibrary = ?", (id_ol,)).fetchone()
        return self._reconstruir(fila) if fila else None

    def coincidencias(self, obra: Obra) -> tuple[UUID, ...]:
        if not obra.autor_ids:
            return ()
        marcas = ",".join("?" for _ in obra.autor_ids)
        filas = ejecutar(self.conexion,
                         """SELECT o.id FROM obra o WHERE titulo_normalizado = ? AND o.id != ?
                            AND (SELECT COUNT(*) FROM obra_autor oa WHERE oa.obra_id = o.id) = ?
                            AND NOT EXISTS (SELECT 1 FROM obra_autor oa WHERE oa.obra_id = o.id
                            AND oa.autor_id NOT IN (""" + marcas + ")) ORDER BY o.id",
                         (obra.titulo_original.casefold(), str(obra.id), len(obra.autor_ids),
                          *(str(id) for id in obra.autor_ids))).fetchall()
        return tuple(UUID(fila["id"]) for fila in filas)

    def listar(self, *, titulo: str | None = None, autor: str | None = None,
               genero_id: UUID | str | None = None, etiqueta_id: UUID | str | None = None,
               publico_id: UUID | str | None = None,
               limite: int = 50, desplazamiento: int = 0) -> list[FichaObra]:
        validar_paginacion(limite, desplazamiento)
        titulo_busqueda, autor_busqueda = filtro_nombre(titulo), filtro_nombre(autor)
        filtros = ""
        parametros: list[object] = []
        if titulo_busqueda:
            if autor_busqueda or any(id is not None for id in (genero_id, etiqueta_id, publico_id)):
                # Otros filtros pueden acotar las obras; evitar construir un conjunto
                # global de títulos cuando el fragmento es amplio (p. ej. "novela").
                filtros += """ AND (instr(o.titulo_normalizado, ?) > 0 OR EXISTS (
                                SELECT 1 FROM edicion e WHERE e.obra_id = o.id AND e.idioma = 'spa'
                                    AND instr(e.titulo_normalizado, ?) > 0))"""
            else:
                filtros += """ AND o.id IN (
                                SELECT id FROM obra WHERE instr(titulo_normalizado, ?) > 0
                                UNION SELECT obra_id FROM edicion WHERE idioma = 'spa'
                                    AND instr(titulo_normalizado, ?) > 0)"""
            parametros.extend((titulo_busqueda, titulo_busqueda))
        if autor_busqueda:
            filtros += """ AND o.id IN (SELECT oa.obra_id FROM autor a
                            JOIN obra_autor oa ON oa.autor_id = a.id
                            WHERE instr(a.nombre_normalizado, ?) > 0)"""
            parametros.append(autor_busqueda)
        for tipo, id in (("GENERO", genero_id), ("ETIQUETA", etiqueta_id), ("PUBLICO", publico_id)):
            if id is not None:
                filtros += """ AND o.id IN (SELECT obra_id FROM clasificacion_obra
                              WHERE tipo = ? AND termino_id = ? AND estado = 'APROBADO')"""
                parametros.extend((tipo, str(validar_uuid(id))))
        filas = ejecutar(self.conexion,
                         """WITH pagina AS (
                            SELECT o.id, o.titulo_original, ep.titulo AS titulo_mostrado,
                                ep.titulo_normalizado AS orden_titulo, ep.id AS preferida_id
                            FROM obra o JOIN edicion ep ON ep.id = COALESCE(
                                o.edicion_preferida_id,
                                (SELECT e.id FROM edicion e WHERE e.obra_id = o.id AND e.idioma = 'spa'
                                 ORDER BY e.id LIMIT 1))
                            WHERE (SELECT COUNT(*) FROM obra_autor oa WHERE oa.obra_id = o.id) > 0
                            """ + filtros + """ ORDER BY orden_titulo, o.id LIMIT ? OFFSET ?)
                            SELECT p.*, (SELECT COUNT(*) FROM edicion e WHERE e.obra_id = p.id) AS cantidad
                            FROM pagina p ORDER BY p.orden_titulo, p.id""",
                         (*parametros, limite, desplazamiento)).fetchall()
        if not filas:
            return []
        # Una consulta adicional para los autores de toda la página; no una por ficha.
        marcas = ",".join("?" for _ in filas)
        nombres: dict[str, list[str]] = {fila["id"]: [] for fila in filas}
        autores = ejecutar(self.conexion,
                           "SELECT oa.obra_id, a.nombre FROM obra_autor oa JOIN autor a ON a.id = oa.autor_id "
                           "WHERE oa.obra_id IN (" + marcas + ") ORDER BY oa.obra_id, oa.orden",
                           tuple(fila["id"] for fila in filas)).fetchall()
        for fila in autores:
            nombres[fila["obra_id"]].append(fila["nombre"])
        return [FichaObra(UUID(fila["id"]), fila["titulo_mostrado"], fila["titulo_original"],
                          UUID(fila["preferida_id"]) if fila["preferida_id"] else None,
                          tuple(nombres[fila["id"]]), fila["cantidad"]) for fila in filas]

    def _guardar_autores(self, obra: Obra) -> None:
        for orden, autor_id in enumerate(obra.autor_ids):
            ejecutar(self.conexion,
                     "INSERT INTO obra_autor (obra_id, autor_id, orden) VALUES (?, ?, ?)",
                     (str(obra.id), str(autor_id), orden))

    def consultar_pagina(
        self, *, texto: str | None = None, genero_id: UUID | str | None = None,
        sede_id: UUID | str | None = None, disponibles: bool | None = None,
        limite: int = 24, desplazamiento: int = 0,
    ) -> PaginaCatalogo:
        """Búsqueda OR en SQL y disponibilidad local antes de paginar.

        Dos lecturas de cabecera y tres de la página (no por tarjeta). El servicio
        mantiene una instantánea de lectura durante toda esta operación.
        """
        validar_paginacion(limite, desplazamiento)
        texto = filtro_nombre(texto)
        if disponibles is not None and type(disponibles) is not bool:
            raise ErrorValidacion("La disponibilidad debe ser True, False o None.")
        sede = validar_uuid(sede_id) if sede_id is not None else None
        genero = validar_uuid(genero_id) if genero_id is not None else None
        if sede is not None and ejecutar(self.conexion, "SELECT 1 FROM sede WHERE id = ?", (str(sede),)).fetchone() is None:
            raise RegistroNoEncontrado("La sede del filtro no existe.")
        condiciones = ["EXISTS (SELECT 1 FROM obra_autor oa WHERE oa.obra_id = o.id)"]
        parametros: list[object] = []
        if texto:
            # UNION opera sobre identidades antes de LIMIT, nunca une páginas.
            condiciones.append("""o.id IN (
                SELECT id FROM obra WHERE instr(titulo_normalizado, ?) > 0
                UNION SELECT obra_id FROM edicion WHERE idioma = 'spa' AND instr(titulo_normalizado, ?) > 0
                UNION SELECT oa.obra_id FROM autor a JOIN obra_autor oa ON oa.autor_id = a.id
                    WHERE instr(a.nombre_normalizado, ?) > 0)""")
            parametros.extend((texto, texto, texto))
        if genero is not None:
            condiciones.append("""EXISTS (SELECT 1 FROM clasificacion_obra c WHERE c.obra_id = o.id
                AND c.tipo = 'GENERO' AND c.termino_id = ? AND c.estado = 'APROBADO')""")
            parametros.append(str(genero))
        disponibilidad_sede = " AND e.sede_actual_id = ?" if sede is not None else ""
        # Con una sede, SQLite elegía explorar todas sus copias aptas por cada
        # obra en un EXISTS correlacionado. Obtener las identidades una vez
        # evita ese producto; obra_id es NOT NULL, también para NOT IN.
        disponibles_sql = """SELECT d.obra_id FROM edicion d JOIN ejemplar e ON e.edicion_id = d.id
            JOIN sede s ON s.id = e.sede_actual_id
            WHERE e.situacion_operativa = 'LIBRE'
                AND e.condicion_fisica = 'APTO' AND e.sede_actual_id = e.sede_propietaria_id
                AND s.activa = 1""" + disponibilidad_sede
        if disponibles is not None:
            condiciones.append(("o.id IN (" if disponibles else "o.id NOT IN (") + disponibles_sql + ")")
            if sede is not None:
                parametros.append(str(sede))
        desde = """FROM obra o JOIN edicion ep ON ep.id = COALESCE(o.edicion_preferida_id,
            (SELECT id FROM edicion WHERE obra_id = o.id AND idioma = 'spa' ORDER BY id LIMIT 1))
            AND ep.obra_id = o.id AND ep.idioma = 'spa' WHERE """ + " AND ".join(condiciones)
        total = ejecutar(self.conexion, "SELECT COUNT(*) " + desde, tuple(parametros)).fetchone()[0]
        filas = ejecutar(self.conexion, """SELECT o.id, o.titulo_original, ep.titulo AS titulo_mostrado,
            ep.id AS preferida_id, ep.portada_edicion_id,
            (SELECT COUNT(*) FROM edicion WHERE obra_id = o.id) AS cantidad """ + desde
            + " ORDER BY ep.titulo_normalizado, o.id LIMIT ? OFFSET ?",
            (*parametros, limite, desplazamiento)).fetchall()
        if not filas:
            return PaginaCatalogo((), total, limite, desplazamiento, sede)
        ids = tuple(f["id"] for f in filas)
        marcas = ",".join("?" for _ in ids)
        autores = {id: [] for id in ids}
        for fila in ejecutar(self.conexion,
                "SELECT oa.obra_id, a.nombre FROM obra_autor oa JOIN autor a ON a.id = oa.autor_id "
                "WHERE oa.obra_id IN (" + marcas + ") ORDER BY oa.obra_id, oa.orden", ids).fetchall():
            autores[fila["obra_id"]].append(fila["nombre"])
        generos = {id: [] for id in ids}
        for fila in ejecutar(self.conexion,
                """SELECT c.obra_id, t.nombre FROM clasificacion_obra c
                    JOIN termino_clasificacion t ON t.id = c.termino_id
                    WHERE c.estado = 'APROBADO' AND c.tipo = 'GENERO' AND c.obra_id IN (""" + marcas
                + ") ORDER BY t.nombre_normalizado, t.id", ids).fetchall():
            generos[fila["obra_id"]].append(fila["nombre"])
        cantidades = {fila["obra_id"]: fila["cantidad"] for fila in ejecutar(self.conexion,
                """SELECT d.obra_id, COUNT(*) AS cantidad FROM edicion d
                    JOIN ejemplar e ON e.edicion_id = d.id JOIN sede s ON s.id = e.sede_actual_id
                    WHERE d.obra_id IN (""" + marcas + """) AND e.situacion_operativa = 'LIBRE'
                    AND e.condicion_fisica = 'APTO' AND e.sede_actual_id = e.sede_propietaria_id
                    AND s.activa = 1""" + disponibilidad_sede + " GROUP BY d.obra_id",
                (*ids, *((str(sede),) if sede is not None else ()))).fetchall()}
        entradas = tuple(EntradaCatalogo(
            FichaObra(UUID(f["id"]), f["titulo_mostrado"], f["titulo_original"], UUID(f["preferida_id"]),
                      tuple(autores[f["id"]]), f["cantidad"]),
            f["portada_edicion_id"], tuple(generos[f["id"]]), cantidades.get(f["id"], 0),
        ) for f in filas)
        return PaginaCatalogo(entradas, total, limite, desplazamiento, sede)

    def _reconstruir(self, fila: sqlite3.Row) -> Obra:
        autores = ejecutar(self.conexion,
                           "SELECT autor_id FROM obra_autor WHERE obra_id = ? ORDER BY orden",
                           (fila["id"],)).fetchall()
        return Obra(
            fila["titulo_original"], [UUID(a["autor_id"]) for a in autores],
            id=UUID(fila["id"]), id_openlibrary=fila["id_openlibrary"],
            descripcion_original=fila["descripcion_original"],
            anio_primera_publicacion=fila["anio_primera_publicacion"],
            portada_obra_id=fila["portada_obra_id"],
            edicion_preferida_id=UUID(fila["edicion_preferida_id"]) if fila["edicion_preferida_id"] else None,
        )

    @staticmethod
    def _datos(obra: Obra) -> tuple[object, ...]:
        return (obra.titulo_original, obra.titulo_original.casefold(), obra.descripcion_original,
                obra.anio_primera_publicacion, obra.portada_obra_id,
                str(obra.edicion_preferida_id) if obra.edicion_preferida_id else None)
