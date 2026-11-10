# Contrato de datos bibliográficos — Rama Open Library / Rama UML

Versión inicial para discutir con el equipo. La estructura distingue **información bibliográfica** e **inventario físico**.

**Actualización de alcance (4/11/2026):** el catálogo inicial se acota a 100 obras reales con edición española; la prueba de 100.000 obras será sintética. OL-2-LOCAL, implementada en 3B.2, admite ISBN/portada/sinopsis ausentes, manteniendo controles de identidad, relación e idioma y rechazando contradicciones. OL-1 y el esquema de prevalidación original conservan sus exigencias históricas; sus registros no se modifican. El dominio operativo ya admitía esos campos opcionales y mantiene su esquema 6. La aceptación técnica es cumplimiento de la política indicada en la evaluación, no una afirmación de presencia de los campos opcionales. Ver [resultados de 3B.2](../../docs/ETAPA_3B_2_RESULTADOS.md) y [secuencia de 3B](../../docs/ETAPA_3B_DISENO.md). Las cardinalidades e identidades de este contrato no cambian.

## Relaciones

| Relación | Cardinalidad | Comentario |
|---|---|---|
| `Obra` — `Edicion` | 1:N | Cada edición apunta a una obra; una obra puede tener varias ediciones |
| `Obra` — `Autor` | N:M | Un autor puede escribir varias obras; una obra puede tener varios autores |
| `Obra` — `Genero` | N:M | Una obra puede pertenecer a varios géneros, con estado de clasificación |
| `Obra` — `Etiqueta` | N:M | Las etiquetas temáticas son independientes de los géneros |
| `Obra` — `MateriaOriginal` | N:M | Sólo para trazabilidad de importación y futuras reglas de normalización |
| `Edicion` — `Ejemplar` | 1:N | `Ejemplar` es una entidad **local** del TP; no viene de Open Library |
| `Ejemplar` — `Sede` | N:1 (sede propietaria) | Definir también ubicación actual en el modelo de préstamos/remitos |

## Campos propuestos

**Obra**
- `id_openlibrary` (PK, por ejemplo `OL27482W`).
- `titulo_original`.
- `descripcion_original` (opcional; puede venir en otro idioma).
- `anio_primera_publicacion` (opcional y **estimado** hasta verificación).
- `portada_obra_id` (referencia de obra, no de edición).

**Edicion**
- `id_openlibrary` (PK, por ejemplo `OL13268284M`).
- `obra_id` (FK).
- `titulo` (el título de la edición en español).
- `idioma` (`spa`).
- `isbn_13`, `isbn_10`, `editorial`, `anio_publicacion`, `numero_paginas` (pueden faltar inicialmente).
- `portada_edicion_id` y `descripcion_es` (pueden faltar inicialmente).
- `idioma_verificado` y `estado_validacion` (campos técnicos del proceso de importación).

**Autor**
- `id_openlibrary` y `nombre`. Mantener identidad por ID, no por comparación exacta de nombres.
- No importar automáticamente traductores/ilustradores de la edición como autores de la obra.

**Genero / Etiqueta**
- Identificador y nombre en español.
- Tablas intermedias `ObraGenero` y `ObraEtiqueta`, con estado `PROPUESTO`, `APROBADO` o `RECHAZADO`.
- Una categoría usada para buscar en Open Library **no es** automáticamente un género confirmado.

**MateriaOriginal**
- Conservar el texto original de Open Library en una relación N:M con `Obra`.
- Esta clase/tabla puede ser **infraestructura de importación** y no necesita formar parte del UML de dominio que presenta la cátedra.

**Ejemplar**
- No se crea en el importador. Lo administra la aplicación: código único, edición, sede propietaria, ubicación actual y estado físico/operativo.

## Estados internos de una edición durante el proceso de importación

- `PENDIENTE`: sólo tenemos una edición candidata de Search API; faltan datos específicos.
- `ENRIQUECIDA`: tenemos datos específicos de la edición, idioma confirmado en el JSON, ISBN con dígito de control válido y portada de edición (sin auditoría final).
- `VALIDADA`: superó la política de aceptación final vigente, que puede aplicar controles automatizados y revisión humana selectiva de casos señalados; el esquema exige ISBN, portada e idioma verificado. No significa revisión humana individual de todos los metadatos.
- `RECHAZADA`: descartada por controles de calidad.

Estos estados **no deben confundirse** con el estado de disponibilidad de un `Ejemplar` para préstamo.

### Aclaración de automatización acordada en etapa 2

La futura aceptación automática debe registrar método, versión de política, fecha y evidencia de controles. Los casos bibliográficamente dudosos se auditan; las decisiones humanas anteriores no se sobrescriben. Lo mismo aplica a las asociaciones de clasificación: una regla explícita y verificada puede producir APROBADO con procedencia automática, manteniendo ambiguas como PROPUESTO y distinguiendo género, etiqueta y público destinatario.

Esta aclaración cambia la exigencia de revisión individual, no los IDs, las cardinalidades ni los valores de estado existentes. Los campos técnicos se diseñarán en 2C/2D antes de implementarse. El pipeline actual todavía sólo enriquece y no aplica aceptación automática; sus resultados existentes no se promueven por esta aclaración. Los estados técnicos siguen fuera del comportamiento de Edicion del dominio operativo.

## Reglas de importación para las 100.000 obras

1. Una obra se identifica por su ID `OL...W`; evitar contar cada edición como una obra distinta.
2. Mantener al menos una edición auténticamente en español `OL...M` por obra.
3. Priorizar edición con ISBN válido y portada propia. Editorial, páginas y sinopsis son preferibles pero no obligatorias por defecto.
4. Mantener materias originales, reglas de mapeo y estado de aprobación separado del catálogo comercial/de navegación.
5. Rechazar duplicados y registrar procedencia. Las portadas de obra no validan una portada de la edición española.
6. No generar automáticamente ejemplares físicos: los préstamos/reservas sólo se habilitan si la red de bibliotecas administra ejemplares reales o de demostración.

## Nota para el UML

El diseño de dominio (`Obra`, `Edicion`, `Ejemplar`, `Sede`, etc.) no tiene por qué reproducir literalmente todas las tablas internas de la importación. Importación/normalización es una capa técnica separada de la lógica de préstamos.
