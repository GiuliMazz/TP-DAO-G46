# Handoff para Codex — Catálogo de Open Library (TP Integrador)

> **Propósito de este documento:** continuar el desarrollo del pipeline de extracción, validación, normalización e importación de un catálogo bibliográfico de Open Library. Está pensado para que Codex lo lea como contexto inicial dentro de un repositorio.
>
> **Alcance de esta rama:** exclusivamente datos bibliográficos y su proceso de importación. El sistema de préstamos interbibliotecarios y su diagrama de clases se desarrollan en otra rama/conversación. **No modificar el dominio de préstamos ni generar ejemplares físicos desde el importador.**

## 1. Contexto del proyecto

Proyecto universitario: **Sistema de Préstamos Interbibliotecarios**, implementado en Python, con base de datos SQLite. La aplicación administrará sedes, socios, catálogo bibliográfico, ejemplares físicos, reservas, préstamos locales/interbibliotecarios, remitos, devoluciones y reportes.

Para la interfaz del catálogo queremos disponer de **aproximadamente 100.000 obras diferentes**, con **al menos una edición en español** para cada obra. Open Library será la **fuente bibliográfica principal**. El inventario de ejemplares que realmente se pueden prestar será mucho menor y se gestionará de forma independiente desde la aplicación.

### Decisiones acordadas

- La clave de una **obra** es el identificador de Open Library (`OL…W`); la clave de una **edición** es otro identificador (`OL…M`). Varias ediciones pueden pertenecer a una obra.
- Una edición candidata debe estar identificada en español (`/languages/spa`); para el catálogo final hay que confirmarlo en los datos específicos de esa edición.
- **Requisitos deseados para seleccionar una edición final:** título usable en español, autor de la obra, ISBN-10 o ISBN-13 válido y portada **de la edición**. Editorial, año, páginas y sinopsis en español son preferibles; no necesariamente obligatorios.
- **No contar ediciones como obras distintas.** Evitar duplicados por ID y no usar coincidencias de texto para fusionar obras sin evidencia.
- Normalizar y traducir **géneros y etiquetas**, pero **conservar las materias originales** (`subjects`) para trazabilidad y reprocesamiento.
- Una obra puede tener varios géneros y etiquetas. **Público destinatario** (p. ej., infantil/juvenil) no equivale a género.
- Clasificaciones automáticas son **PROPUESTAS**, nunca hechos confirmados. La categoría usada para encontrar un libro en Search API no acredita su género.
- No traducir libremente sinopsis mediante reglas ingenuas ni inventar metadatos faltantes. Si la edición trae sinopsis en español, priorizarla sobre la descripción de la obra en otro idioma; si falta, conservar la descripción original identificada como tal.
- Los ISBN y los ID de portada se guardan como **referencias**; el campo `covers` de una obra no demuestra que esa imagen corresponda a la edición seleccionada.
- Procesar grandes volúmenes mediante los **dumps oficiales de Open Library**, no mediante decenas de miles de llamadas a su API pública.

## 2. Material existente que debe incorporarse al repositorio

La conversación anterior generó este paquete, que **hay que descomprimir o copiar al entorno local de Codex**. Codex no necesariamente tendrá acceso automático a los archivos que estaban adjuntos en ChatGPT.

**Paquete recomendado:** `kit_openlibrary_etapa1.zip`. Al descomprimirlo aparece la carpeta `ol_catalogo_etapa1/`:

```text
ol_catalogo_etapa1/
├── README.md
├── CONTRATO_PARA_UML.md
├── ejecutar_etapa1.py
├── preparar_catalogo.py
├── enriquecer_con_muestra_30.py
└── salida_v3/
    ├── catalogo_prevalidacion.db
    ├── catalogo_resumido.csv
    ├── auditoria_prioritaria.csv
    ├── informe_prevalidacion.md
    ├── metricas_prevalidacion.json
    └── errores_importacion.json
```

**Fuentes de entrada que hay que agregar aparte si se quiere reproducir el proceso desde cero:**

```text
catalogo_exploratorio.json   # muestra de 1.000 obras; aproximadamente 1,6 MB
respuestas_originales.json   # JSON detallados de la muestra anterior de 30; aproximadamente 203 KB
```

También existen archivos auxiliares: `catalogo_exploratorio.csv`, `catalogo_exploratorio.db`, `informe_exploratorio.json`, `informe_resumen.md`, `auditoria_40.csv`, `catalogo_muestra.json`, `biblioteca_muestra.db`.

### Ejecución actual (sin conexión)

Desde la carpeta que contenga los tres scripts y ambos JSON de entrada:

```bash
python3 ejecutar_etapa1.py \
  --catalogo catalogo_exploratorio.json \
  --detalles respuestas_originales.json \
  --salida resultado_etapa1
```

Usa sólo la biblioteca estándar de Python. El parámetro `--detalles` es opcional. **Leer el código antes de modificarlo**; no asumir que este pipeline ya procesa dumps masivos.

## 3. Estado verificado a noviembre de 2026

### Muestra exploratoria de 1.000 obras

- **1.000 obras únicas**, 1.000 ediciones candidatas identificadas en español en resultados de búsqueda.
- Procedencia: 10 categorías con cuota de 100 obras cada una (fantasía, ciencia ficción, misterio/policial, romance, terror, novela histórica, historia, ciencia, tecnología, biografías).
- 6.000 documentos de búsqueda examinados mediante 62 consultas API.
- 961 obras con portada **de obra**, no necesariamente de edición.
- 444 obras con alguna etiqueta propuesta inicialmente.
- Muestreo por relevancia: **no representativo** del catálogo total de Open Library.

### Etapa 1 de prevalidación (resultado de `salida_v3/`)

Se verificó la estructura SQLite y los archivos de métricas:

| Tabla | Filas |
|---|---:|
| `obra` | 1.000 |
| `edicion` | 1.000 |
| `autor` | 993 |
| `obra_autor` | 1.367 |
| `genero` | 10 |
| `obra_genero` | 1.467 |
| `etiqueta` | 19 |
| `obra_etiqueta` | 637 |
| `materia_original` | 10.987 |
| `obra_materia_original` | 24.817 |

- **7 ediciones `ENRIQUECIDA`**, gracias a que coincidían exactamente con JSON detallados de la muestra anterior: ISBN validado por dígito de control, portada de edición, editorial, idioma registrado.
- **993 ediciones `PENDIENTE`**; ninguna se declaró `VALIDADA` automáticamente.
- 214 obras con alguna **alerta heurística**, y 100 filas en la auditoría prioritaria. **Una alerta no equivale a un error confirmado.**
- La muestra inicial de 30 obras tuvo 30 aceptadas de 31 examinadas, pero era exclusivamente de fantasía, de modo que no debe extrapolarse su tasa de aceptación.
- El pipeline mejoró un título registrado como `Meow` gracias al `full_title` de la propia edición y recuperó una sinopsis de edición en español. Hay otros títulos y años dudosos que siguen sin corregir.

**Situación real:** todavía **NO** existe un catálogo final de 100.000 obras, ni se validaron los metadatos específicos de las 1.000 ediciones exploratorias.

## 4. Modelo de datos acordado con la rama UML

El contrato detallado está en `ol_catalogo_etapa1/CONTRATO_PARA_UML.md`. Mantenerlo como referencia; consultar antes de cambiar nombres o cardinalidades.

| Entidad | Datos y relaciones esenciales |
|---|---|
| `Obra` | ID OL, título original, descripción original opcional, año original opcional/provisorio; 1:N con `Edicion` |
| `Edicion` | ID OL, obra, título de edición, idioma, ISBN, editorial, año de edición, páginas, portada de edición, sinopsis en español, validación |
| `Autor` | ID OL, nombre; N:M con `Obra` |
| `Genero` | Catálogo controlado en español; N:M con `Obra` |
| `Etiqueta` | Etiqueta temática normalizada; N:M con `Obra` |
| `MateriaOriginal` | Texto `subjects` conservado; N:M con `Obra`; infraestructura de importación, no necesariamente clase de dominio |
| `Ejemplar` | **Fuera del importador**: copia física vinculada a una edición y una sede, gestionada por el sistema principal |

Las tablas reales de etapa 1 incluyen `obra`, `edicion`, `autor`, `obra_autor`, `genero`, `obra_genero`, `etiqueta`, `obra_etiqueta`, `materia_original` y `obra_materia_original`.

**Estados de edición:**

- `PENDIENTE`: candidata de la búsqueda; faltan detalles de edición.
- `ENRIQUECIDA`: datos de edición obtenidos y comprobaciones técnicas iniciales realizadas.
- `VALIDADA`: cumple la política de calidad final y la revisión correspondiente.
- `RECHAZADA`: se descartó con motivo registrado.

`obra_genero` y `obra_etiqueta` poseen su propio estado `PROPUESTO` / `APROBADO` / `RECHAZADO` y un campo de método/procedencia. No confundir el estado bibliográfico con la disponibilidad de un ejemplar.

## 5. Problemas observados y reglas a mejorar

1. **Clasificación sobredimensionada:** materias como `Science fiction, fantasy, horror` no justifican asignar automáticamente los tres géneros. Tampoco `History` dentro de una novela convierte la obra en un libro de historia. Evitar la confusión `No ficción` con `Ficción`.
2. **Ruido en materias:** `nyt:…`, premios, metadatos de ventas, `series:…`, idiomas, formatos y comentarios no deben tratarse como géneros. Algunas materias bibliográficas se aplican a estudios *sobre* la obra o a adaptaciones, no a la obra misma.
3. **Autores vs. colaboradores:** autores de `works` y `editions` no siempre coinciden; hay traductores, ilustradores y créditos de portada entremezclados. Identificar roles cuando exista evidencia; no sustituir autores originales por créditos de edición.
4. **Títulos:** preferir un campo verificado para la edición en español; revisar títulos en mayúsculas, bilingües, etiquetas `Spanish Edition` o títulos anómalos. No adivinar correcciones automáticas.
5. **Años:** `first_publish_year` puede ser inexacto; preservar su fuente, validar rangos y no interpretar año de obra como año de la edición.
6. **Etiquetas escasas:** sólo 19 etiquetas definidas inicialmente. Ampliar vocabulario controlado y equivalencias multilingües (p. ej., `Magic` / `Magia`, `Epic fantasy` / `Fantasía épica`), sin confundir materia con género.
7. **Sinopsis:** priorizar la descripción de la edición en español cuando exista; distinguir `descripcion_es` de `descripcion_original` y de una eventual traducción editorialmente aprobada.
8. **Calidad de ISBN y portada:** validar los dígitos de control ISBN-10/ISBN-13 y el `covers` de edición; identificar URL de portada sólo con ID específico. La existencia de ID no garantiza que la imagen remota esté accesible: eso se puede muestrear aparte.
9. **Trazabilidad:** preservar los JSON originales o referencias a ellos, fecha/versión de importación, reglas utilizadas, razones de rechazo y estadísticas por fase.

**Casos de prueba concretos** presentes en la auditoría: `Haunting Adeline` / título erróneo `Meow`; `Moby Dick` clasificado como demasiadas categorías; `La vuelta al mundo en 80 días` con excesivos géneros; `Drácula` con cantidad anómala de autores; mezcla de ciencia vs. ciencia ficción; `Los Miserables` como fantasía por materias ambiguas. Usar estos casos como tests de regresión, sin dar por cierto un dato que no se haya corroborado.

## 6. Próximo trabajo para Codex — Orden de implementación

### Fase A — Auditar y estabilizar lo existente

1. Examinar todos los scripts, el contrato UML, las tablas SQLite y las métricas. Ejecutar la etapa 1 para establecer una línea base reproducible.
2. Organizar el código en módulos (`fuentes`, `parseo`, `validacion`, `normalizacion`, `persistencia`, `informes`) **sin refactorizar innecesariamente**.
3. Agregar pruebas con `unittest` o `pytest` según el repositorio: validador ISBN; extracción de títulos, idiomas y descripciones; deduplicación; géneros; relaciones; estados; importación repetible.
4. Diseñar un pequeño diccionario explícito de equivalencias `subjects → genero/etiqueta`, con coincidencias robustas, prioridades y reglas de descarte. Conservar motivo y fuente de cada asociación. Priorizar precisión frente a cobertura.
5. Incorporar una auditoría fácil de editar para que una persona pueda **aprobar, rechazar o corregir** clasificaciones. Persistir esas decisiones y nunca sobrescribirlas accidentalmente en nuevas importaciones.

### Fase B — Importador de dumps en flujo

**No descargar todavía decenas de gigabytes ni iniciar la importación de 100.000 sin revisar primero opciones y recursos del equipo.** Implementar y probar con recortes locales pequeños de dumps reales.

1. Leer las líneas del dump de Open Library (TSV de 5 columnas, último campo JSON), con soporte de archivo comprimido `.gz`, **sin cargar el archivo completo en memoria**.
2. Primer paso sobre **ediciones**: filtrar `type=/type/edition`, `languages` que contenga `/languages/spa`, `works` válido, ISBN válido y portada de edición positiva. Guardar ediciones candidatas en **SQLite de staging** con índices por `obra_id` y `edicion_id`, evitando registros duplicados. Contar rechazados por motivo.
3. Priorizar varias ediciones candidatas por obra sólo si mejora la posibilidad de completar metadatos; seleccionar una **edición preferida** sin impedir múltiples ediciones en el modelo final. El criterio de preferencia debe ser explícito y reproducible.
4. Leer el dump de **obras** secuencialmente y enriquecer únicamente aquellas cuyo `OL…W` aparezca en la tabla de candidatos: autores, título original, descripción y materias originales. Registrar obras ausentes o sin autores.
5. Leer el dump de **autores** y resolver únicamente los identificadores utilizados, con tratamiento de nombres y roles si están disponibles.
6. Aplicar reglas de clasificación, control de calidad y estados; exportar una SQLite final compatible con el contrato bibliográfico, separada del staging.
7. Incorporar progreso, checkpoints recuperables, logging, manejo de errores de JSON/TSV, opción `--limite` para pruebas, modo `--dry-run`, y reportes de descartes y calidad.
8. Verificar política de uso y atribución de Open Library para los datos e imágenes cuando se integren a la aplicación.

### Fase C — Selección de 100.000 obras

1. Realizar una prueba con un subconjunto más amplio que incluya **ficción y no ficción**; medir precisión de géneros y disponibilidad real de ediciones completas.
2. Definir una política de variedad que **no se limite a los diez géneros exploratorios ni a las primeras páginas por relevancia**. La selección de 100.000 debe ser diversa y reproducible; documentar los sesgos.
3. Importar exactamente hasta 100.000 **obras distintas** que cumplan criterios y cuenten con al menos una edición válida en español. Si no se alcanza el número, informar cuántas y por qué, sin relajar requisitos a escondidas.
4. Producir estadísticas: examinadas, rechazadas por motivo, aprobadas, coberturas de ISBN/portada/sinopsis, distribución por géneros, auditorías y tamaño/rendimiento de la SQLite.
5. Mantener la salida lista para vincularse después a `Ejemplar`, sin crear existencias falsas.

## 7. Criterios de aceptación

- El pipeline es **reproducible e idempotente**: ejecutar dos veces sobre los mismos insumos no duplica obras, autores, ediciones ni vínculos.
- Las **claves foráneas** de SQLite se respetan (`PRAGMA foreign_keys=ON`; `PRAGMA foreign_key_check` sin errores).
- Cada obra exportada tiene ID de obra, título y autor válido, y al menos una edición `spa` que supere los controles finales acordados.
- El ISBN de la edición supera el algoritmo de suma de control; la portada proviene de la edición, no de la obra.
- La salida indica qué campos están ausentes y su procedencia; no presenta como verificados los que no lo están.
- Las clasificaciones conservan sus materias fuente y estado de aprobación; una regla ambigua no genera múltiples géneros injustificados.
- La operación por dumps usa memoria acotada, permite reanudar o repetir y produce informes de calidad.
- No se crean ni se alteran `Sede`, `Ejemplar`, `Prestamo`, `Reserva` o `Remito`.

## 8. Instrucción inicial para Codex

**Empezá por la Fase A.** Revisá los archivos existentes en el repositorio y el `CONTRATO_PARA_UML.md`, ejecutá el pipeline actual y entregá primero:

1. Un diagnóstico concreto de lo que hace hoy cada script y de sus puntos débiles.
2. Una propuesta de cambios mínimos y tests para garantizar que el esquema bibliográfico siga siendo compatible con la rama UML.
3. La implementación de las validaciones y pruebas más urgentes (en especial ISBN, títulos, estados y clasificación de géneros).
4. Un informe con comandos de ejecución, resultados de tests y **qué faltaría** para empezar el procesamiento de dumps.

**No saltes directamente a descargar los dumps ni a crear 100.000 registros de prueba.** No inventes datos ni tasas de aceptación. Si falta un archivo, señalá cuál y pedilo o usá fixtures mínimos claramente identificados como sintéticos. Antes de cambiar el contrato del modelo bibliográfico, exponé el motivo y los posibles efectos sobre el UML.

## 9. Documentación externa

- Dumps de Open Library: https://openlibrary.org/developers/dumps
- Información de API: https://openlibrary.org/developers/api
- Search API: https://openlibrary.org/dev/docs/api/search
- Portadas: https://openlibrary.org/dev/docs/api/covers

**Recordatorio de separación de responsabilidades:** *Open Library aporta metadatos de obras y ediciones; el TP administra qué ejemplares físicos existen, en qué sedes están y qué operaciones pueden realizarse sobre ellos.*
