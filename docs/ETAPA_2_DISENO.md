# Etapa 2 — Catálogo e inventario: diseño incremental

Fecha: 3 de noviembre de 2026. Estado: 2A–2E implementados/verificados a nivel de backend. Ajustes A–D de búsqueda, automatización, clasificación y circulación incorporados al diseño. Ver [diseño de consolidación](./ETAPA_2E_DISENO.md) y [resultados y mediciones](./ETAPA_2E_RESULTADOS.md).

Se apoya en el [plan](../PLAN_DESARROLLO.md), el [análisis general](./ETAPA_0_DISENO.md), el [contrato bibliográfico](../herramientas/openlibrary/CONTRATO_PARA_UML.md), los [diagramas originales](../archivo/diagramas) y la implementación de [etapa 1](./ETAPA_1_RESULTADOS.md). No modifica el contrato ni incorpora un nuevo framework.

## 1. Resultado que buscamos

Administrar obras, ediciones, autores y copias físicas; buscar por título, autor y género con páginas acotadas; consultar disponibilidad por sede e integrar un subconjunto revisado de Open Library. Cubre RF03, RF06 y la parte bibliográfica/inventario de RN05. Las condiciones de una sede activa anticipan RN07; préstamos y remitos siguen en sus etapas.

El primer recorrido será: registrar autor → obra → edición → ejemplares en Centro y Norte → consultar una sola obra con sus ediciones y disponibilidad separada por sede. La carga de datos de ejemplo será explícita y separada de los datos reales.

El objetivo de datos sigue siendo aproximadamente 100.000 obras distintas, aunque no es una cantidad exigida por la consigna. Se llegará mediante procesamiento automatizado y auditoría selectiva, sin exigir revisión individual de cada obra ni relajar los criterios de calidad sin documentarlo. En 2A sólo se implementan altas y consultas: no se afirma haber alcanzado ese volumen ni su rendimiento.

### Evidencia de los datos disponibles

Se consultó la SQLite de prevalidación en modo sólo lectura:

| Dato | Resultado observado |
|---|---:|
| Obras / ediciones | 1.000 / 1.000 |
| Autores | 993 |
| Ediciones ENRIQUECIDA | 7 |
| Ediciones PENDIENTE | 993 |
| Ediciones VALIDADA | 0 |
| Asociaciones de género | 1.467, todas PROPUESTO |
| Asociaciones de etiqueta | 637 |
| Obras sin autor vinculado | 0 |
| Autores con identificador técnico LOCAL-… en esta base | 0 |

`PRAGMA foreign_key_check` no informó problemas. Esto acredita integridad referencial de la muestra, no corrección de los metadatos. Las siete ediciones enriquecidas tienen idioma verificado, ISBN y portada de edición registrados; aún requieren la revisión final acordada. No se transformarán automáticamente en VALIDADA.

## 2. Responsabilidades y campos

### Catálogo bibliográfico

| Clase | Datos esenciales | Comportamiento |
|---|---|---|
| Autor | UUID, nombre, ID OL opcional | Validar/corregir nombre conservando identidad. Dos autores pueden tener el mismo nombre. |
| Obra | UUID, título original, ID OL opcional, descripción original y año original estimado opcionales, edición preferida opcional | Corregir datos propios, vincular autores sin repetir relaciones y seleccionar una edición española de esa misma obra para mostrar. No representa una copia ni tiene un estado de préstamo. |
| Edicion | UUID, obra_id, título, idioma, ID OL opcional, ISBN-10/13, editorial, año, páginas, portada de edición y descripción española opcionales | Validar cambios completos; preservar identidad y relación con su obra. No modela el avance del pipeline. |
| Genero / Etiqueta / PublicoDestinatario | UUID, nombre normalizado único dentro de cada vocabulario | Validar denominación e impedir cambio de identidad/tipo. Un género no se crea por cada materia de Open Library. |
| ClasificacionObra / DecisionClasificacion | Obra y término, estado, método, motivo, fecha y regla/versionado cuando aplica | Aprobar/rechazar; proteger decisiones humanas y admitir reevaluación automática; conservar evidencia e historial mediante el repositorio |

Se mantiene la identidad local UUID y el ID externo único, según la propuesta de etapa 0. Varias ediciones de un mismo ID de obra OL resuelven a la misma obra local; repetir la integración conserva sus UUID.

Para no ampliar el modelo innecesariamente, inicialmente trabajaremos con libros, sin inventar subclases para revistas, audiovisuales u otros formatos. El `TipoMaterial` del diagrama original se pospone hasta tener un caso de uso distinto que lo necesite. El diseño conserva la posibilidad de ampliarlo después.

Una Obra puede existir administrativamente antes de registrar sus ediciones. El listado de catálogo utilizable requiere al menos una edición y autores identificados. No se agrega por eso otro ciclo de estados de publicación: el servicio consulta si existen las relaciones requeridas. Una obra con edición puede aparecer aunque no haya ejemplares físicos.

### Inventario físico

| Clase | Datos esenciales | Comportamiento |
|---|---|---|
| Ejemplar | UUID, código de inventario único, edición_id, sede_propietaria_id, sede_actual_id, condición física y situación operativa | Informar disponibilidad propia, registrar condición y dar de baja sin borrar; impedir cambios incompatibles |

**Alta inicial propuesta:** código informado explícitamente, no vacío, sin espacios internos y normalizado a mayúsculas (por ejemplo `HZ-000001`). No codifica obligatoriamente sede ni ISBN. El UUID y la etiqueta física son identidades diferentes. El código se mantiene estable; no se genera a partir de contar filas.

Cada alta agrega una copia concreta de una edición existente en una sede activa. Propietaria y ubicación inicial son esa sede. No hay alta automática de copias al importar metadatos, ni traslado arbitrario con una simple edición de atributos. Más adelante los casos de logística cambiarán ubicación respetando sus transiciones.

Se separan dos aspectos:

- **Condición física:** propuesta inicial APTO, DANIADO o DESTRUIDO. Un daño impide prestar; una destrucción impide volver a declarar el material apto mediante una corrección ordinaria.
- **Situación operativa:** en este incremento sólo LIBRE o BAJA. LIBRE expresa ausencia de asignación, no garantiza por sí solo que pueda prestarse. ASIGNADO, PRESTADO, EN_TRANSITO, PENDIENTE_RETORNO y NO_LOCALIZADO se incorporarán con los casos de circulación/logística correspondientes. No se implementan ahora sus operaciones.

Disponibilidad propia del ejemplar: LIBRE, condición APTO y ubicación en su propietaria. Disponibilidad ofrecida por el servicio: además, sede activa y edición/obra existentes y utilizables. Una recepción en otra sede quedará asignada a su solicitud, sin liberar el material a otra persona. La disponibilidad futura de la cola de reservas se resolverá en su etapa.

Esta disponibilidad responde a si puede asignarse a una **nueva** solicitud. Entregar un ejemplar previamente asignado usa otra comprobación: asignación a esa misma solicitud, socio habilitado, sede de retiro activa, presencia en ella y recepción conforme si hubo traslado. No se exigirá LIBRE ni ubicación en la propietaria para esa entrega. Así, recibir en Norte un ejemplar de Centro mantiene la propiedad y su asignación, y no permite prestarlo a otro socio. Se comprobará al implementar circulación; 2A no incluye ejemplares.

La baja lógica deja el ejemplar y sus relaciones disponibles para historial. No se confunde con dar de baja una sede, ni con perder o dañar un libro.

Aplicación en 2B: Ejemplar, InventarioService y EjemplarRepository implementan alta explícita, código estable, condición, baja y consulta paginada. El código se normaliza a mayúsculas y rechaza espacios internos/controles. El alta fija ubicación en la propietaria; no hay operación de movimiento ni reactivación de una copia dada de baja. La ubicación es opcional para reconstruir fielmente registros, pero no se inventa al leer un valor nulo. Los resúmenes incluyen bajas en los totales registrados y las discriminan por separado; disponibilidad sólo cuenta copias elegibles.

## 3. Datos manuales e importados

### Invariantes comunes

- Títulos y nombres obligatorios como texto no vacío, conservando contenido y acentos; mayúsculas, un título corto o idioma aparente generan revisión, no una corrección inventada.
- ISBN opcional en un alta manual, pero cualquier ISBN proporcionado debe tener formato y dígito de control válidos. No aceptar un valor eliminando letras arbitrarias hasta obtener números que pasen el cálculo.
- Páginas, años e IDs de portada, cuando existan como números, deben ser enteros positivos; un booleano no cuenta como número válido. Una fecha original o dudosa de la fuente se conserva en la evidencia, sin adivinar su año.
- El ID OL debe corresponder al tipo de entidad y no se inventa para los registros manuales. El ID de portada de obra no acredita una portada de edición.
- No validar automáticamente el idioma de un título o una sinopsis a partir de que el registro esté marcado `spa`. Tampoco traducir el contenido para completar un campo ausente.

### Propuesta de alcance para altas manuales

Registrar libros en español en esta versión, con título y autor identificados. ISBN, editorial, portada, páginas, año y sinopsis pueden faltar. La ausencia de una imagen o de ISBN no demuestra que una copia física local no exista o no pueda prestarse.

No crear autores ficticios para satisfacer una restricción. Si falta evidencia suficiente para un autor de un registro importado, queda en preparación para revisión. Las altas de obras sin autor identificado necesitarían una política explícita posterior; no se resuelven atribuyéndolas a una persona inventada.

Los títulos no son únicos y el ISBN no sustituye la identidad de la obra. Ante un ISBN o combinación título/autor coincidente, presentar un posible duplicado para revisión antes de crear una nueva alta manual; no fusionar obras por texto. El manejo de esa confirmación se definirá en el caso de uso de alta, sin introducir coincidencias aproximadas o servicios externos.

### Open Library: controles automatizados y revisión selectiva

El importador mantiene PENDIENTE, ENRIQUECIDA, VALIDADA y RECHAZADA, junto con idioma verificado, fuente y evidencia. **VALIDADA podrá resultar de una política automatizada documentada**, sin aprobación humana de cada registro. No significa que una persona haya certificado todos sus metadatos.

- **Controles técnicos automatizables:** identidades OL por tipo, vínculos edición/obra/autor coherentes y presentes, campos obligatorios, idioma español declarado en el detalle de edición, formato/control ISBN y portada positiva de esa misma edición. La existencia de ID no acredita accesibilidad remota ni corrección visual de la imagen.
- **Auditoría bibliográfica:** detectar títulos anómalos, créditos de colaboradores mezclados con autores, fuentes contradictorias, descripciones dudosas y otros riesgos. Los registros señalados quedan pendientes de revisión o rechazados con motivo. Una comprobación técnica por sí sola no demuestra que el título esté bien traducido ni que la autoría sea correcta.
- **Aceptación automática:** si supera controles técnicos y no tiene alertas bloqueantes según la versión de política, puede pasar a VALIDADA, registrando método AUTOMATICO, versión, fecha y comprobaciones. Una decisión humana anterior se conserva y no se revierte automáticamente.
- **Revisión humana selectiva:** resolver casos señalados y auditar muestras de los aceptados para medir problemas y ajustar reglas. No se inventan tasas de precisión ni se aplica una heurística de idioma como prueba concluyente.

No se incorporan esos estados como métodos de Edicion. No se exige a un registro manual fingir que pasó por Open Library. Las reglas propias de la edición se comparten donde corresponda; las comprobaciones de fuente pertenecen a importación.

En 2D se evaluaron las 1.000 candidatas usando JSON detallados y evidencias locales: cinco VALIDADA automáticamente e integradas, dos ENRIQUECIDA para revisión y 993 PENDIENTE. La base de referencia sigue con siete ENRIQUECIDA y 993 PENDIENTE; sus datos no se modificaron. Los nuevos estados, controles, decisiones e identidades locales se guardan en el destino operativo.

La política OL-1 exige detalle exacto, relaciones coherentes, autores de obra identificados, español declarado, ISBN válido y portada propia. No acredita accesibilidad/corrección visual de la imagen ni corrección bibliográfica universal. Los títulos breves, discrepancias de títulos, múltiples ISBN, edición multilingüe, rechazo en fuente o más de cinco autores requieren revisión cuando los controles están completos. Cambiar resultados de una política para la misma instantánea exige versionarla.

ImportacionService conserva evaluaciones, decisiones y correspondencia con la edición local. Una decisión humana conserva la instantánea que aprobó/rechazó; los cambios posteriores se registran aparte y pueden consultarse mediante evidencia/de_decision. La integración usa la evidencia de la decisión vigente. Resolver por ID OL no autoriza fusionar coincidencias de título/autor o ISBN: éstas requieren revisión explícita.

La reimportación conserva todos los metadatos y relaciones existentes, no sólo los campos supuestamente humanos; así protege correcciones sin añadir un sistema de propiedad por campo. Las nuevas versiones de fuente quedan auditadas, y completar/corregir datos existentes se hace explícitamente con los servicios del catálogo. La primera integración puede aplicar títulos corregidos en una aceptación manual. Rechazar posteriormente una fuente no borra catálogo ni inventario existentes.

ProcesadorMaterias comparte el procesamiento de 2C sin abrir transacción propia. Una integración confirma autor/obra/edición/preferencia inicial/materias/clasificaciones/correspondencia juntos, o revierte todo; la evaluación previa se conserva para auditar conflictos. Los estados técnicos no se incorporaron a Edicion ni se crean existencias.

### Clasificación automatizada trazable — incremento 2C

APROBADO no implicará necesariamente aprobación humana. Una regla explícita de alta confianza podrá aprobar una asociación, por ejemplo una coincidencia exacta de `Fantasy fiction` con Fantasía, siempre que pase los controles de contexto y no haya una decisión humana que lo impida. Se conservarán materia fuente, regla/versionado, método AUTOMATICO y justificación. La condición de alta confianza se contrastará con casos auditados; no es una garantía universal.

Materias compuestas como `Science fiction, fantasy, horror`, menciones incidentales, negaciones o materias sobre estudios/adaptaciones no se descomponen ciegamente en varios géneros. Las asociaciones dudosas siguen PROPUESTO; las decisiones humanas prevalecen al reimportar. Búsqueda y recomendaciones pueden usar APROBADO tanto manual como automático, mostrando su procedencia donde corresponda.

Se mantienen tres conceptos distintos: **género** (Fantasía), **etiqueta temática** (Magia) y **público destinatario** (Infantil/Juvenil). El público tiene asociaciones de su propio tipo en 2C; no se guarda como género ni se infiere Adulto por ausencia de información. La aceptación técnica de una edición no aprueba por sí sola todas las clasificaciones de su obra.

**Concreción en 2C:** las tres clases de vocabulario comparten una base inmutable y el mismo comportamiento de asociación mediante ClasificacionObra, evitando tres clases de relación idénticas. El tipo se respalda en SQLite mediante clave foránea compuesta. ClasificacionService coordina propuestas, revisiones y procesamiento de materias; ClasificacionRepository guarda términos, asociaciones, materias originales, reglas inmutables por versión, evaluaciones e historial. Esto ajusta los nombres de las asociaciones previstas, sin cambiar el contrato externo del importador.

Las reglas iniciales optativas son `Fantasy fiction` → género Fantasía, `Magic -- Fiction` → etiqueta Magia, `Children's fiction` → público Infantil y `Young adult fiction` → público Juvenil. La comparación es exacta tras normalizar mayúsculas y espacios; la evidencia retiene el texto original. Las materias sin correspondencia se guardan sin inventar clasificaciones. Reglas candidatas pueden declarar que requieren revisión. El contexto de crítica, estudio o adaptaciones bloquea la aprobación automática de géneros. Es un control conservador, no una demostración de precisión bibliográfica.

Al añadir materias se reevalúan las ya guardadas para esa obra con las reglas suministradas. Una aprobación automática puede volver a PROPUESTO si su misma regla encuentra contexto dudoso o cambia de versión; una regla candidata distinta no anula una aprobación. Las decisiones manuales de aprobación/rechazo siempre prevalecen. Cambiar la definición de una regla requiere otra versión; cambiar los controles de contexto exigirá versionar las reglas afectadas. No se infiere rechazo por falta de materias ni se retiran automáticamente fuentes ausentes de un lote posterior.

## 4. Casos de uso y componentes

| Caso | Dominio | Servicio y persistencia |
|---|---|---|
| Registrar/corregir autor, obra y edición | Autor, Obra, Edicion | CatalogoService coordina; repositorios de obra/edición/autor guardan y reconstruyen |
| Listar y obtener detalle de obra | Relaciones bibliográficas | CatalogoService y consultas acotadas del repositorio, evitando cargar el catálogo completo |
| Clasificar/revisar género, etiqueta o público | ClasificacionObra y decisiones con estado/evidencia | ClasificacionService y ClasificacionRepository; relación N:M con claves compuestas |
| Registrar ejemplar y darlo de baja | Ejemplar, Sede, Edicion | InventarioService valida sede/edición/código; EjemplarRepository guarda |
| Consultar disponibilidad por sede | Ejemplar y Sede | Consulta agregada con una fila por obra/sede; no confundir propietaria con ubicación |
| Integrar subconjunto validado | Entidades anteriores | Servicio de importación y registros técnicos; usa los repositorios sin crear ejemplares |

Se mantendrán los repositorios específicos y la conexión compartida de la etapa 1. El dominio no consulta SQLite; los servicios no contienen SQL. Los objetos de resultado para listados pueden resumir título, autores y cantidades sin cargar todos los ejemplares. No son otra jerarquía de entidades con reglas duplicadas.

El alta de una obra con sus relaciones y primera edición debe confirmarse de forma atómica cuando se ofrezca como un único caso de uso. Un fallo de edición no deja una obra visible a medio registrar. No se habilitan métodos genéricos de fusión o borrado en cascada sobre datos con inventario.

## 5. Persistencia, migraciones y consultas

El ejecutor ya aplica migraciones pendientes en orden, sobre bases vacías o existentes, manteniendo las transacciones y sin volver a ejecutar una versión aplicada. Esquemas: 1 sedes/socios, 2 núcleo bibliográfico, 3 inventario, 4 clasificación, 5 importación y 6 índice de consulta de ejemplares por sede/estado/código. El último cambio no modifica registros ni entidades.

La prueba importante será crear una base versión 1 con sedes/socios, actualizarla y comprobar que sus registros, UUID y estados siguen intactos. Las pruebas actuales que esperan versión 1 se ajustarán para distinguir la prueba histórica de la versión vigente; no se eliminarán las comprobaciones de integridad ni rollback.

Tablas previstas, creadas en el incremento que las use:

- `autor`, `obra`, `edicion`, `obra_autor`: UUID locales, referencias externas únicas opcionales y claves foráneas.
- `ejemplar`: edición, propietaria, ubicación, código único y condición/situación diferenciadas.
- `termino_clasificacion` y `clasificacion_obra`: vocabularios tipados y asociaciones revisables; sustituyen las tablas separadas previstas en el borrador. Unicidad por tipo/nombre y obra/término, con índices para filtros aprobados.
- `materia_original`, `regla_clasificacion`, `evidencia_clasificacion` y `decision_clasificacion`: fuente y texto literal, definición/versionado, evaluación con contexto e historial de decisiones. No replican todos los JSON en las entidades.
- `evaluacion_importacion`, `decision_importacion` y `seguimiento_importacion`: instantánea original y huella/política, controles, alertas, datos normalizados, decisiones con motivo/método/fecha/correcciones y relación con la edición local. Una clave compuesta impide aplicar la decisión de otra candidata.

No se harán borrados de sedes/socios para reconstruir el esquema. Cambiar la fuente no elimina el inventario ni reasigna un ejemplar a otra edición.

Consultas:

- Listado devuelve obras distintas, no una fila por edición, autor o copia. Filtros por género usan asociaciones aprobadas; propuestas quedan en auditoría.
- **Búsqueda y título mostrado:** buscar en el título original y en el título de cualquier edición `spa`, incluida una edición no preferida. Mostrar el título de la preferida española y conservar el original en la ficha/detalle. La primera edición registrada queda seleccionada; el servicio permite cambiarla por otra de la misma obra. La base respalda esa pertenencia con una clave foránea compuesta. Si no hay selección persistida pero sí ediciones, el respaldo reproducible es la edición española de menor UUID; si no existe edición, el detalle administrativo muestra el título original. El listado utilizable excluye obras sin edición o sin autor.
- Orden estable y límite máximo de 100, como en etapa 1. Preferir paginación por clave para navegación profunda si las mediciones lo justifican; no introducir dos mecanismos antes de medir.
- Índices sobre IDs externos, títulos normalizados para orden/prefijo, claves de relaciones y claves de ejemplares por edición/sede/estado, según consulta concreta.
- Una búsqueda literal de fragmento con `instr` o equivalente no se vuelve rápida automáticamente por agregar un índice convencional. Medir título, autor y género con hasta 100.000 obras sintéticas; evaluar FTS de SQLite sólo si hace falta, sin otro servidor.
- No contar dos veces ejemplares al unir autores y géneros: separar la agregación de inventario de las asociaciones N:M. Mostrar cero disponibles cuando no hay copias; no inventarlas para llenar el panel.

## 6. Incrementos y pruebas de aceptación previstas

Cada fila es un incremento independiente: explicar cambios, implementar sólo ese alcance, probar y mostrar resultados antes de seguir. Las comprobaciones de 2A–2E ya se ejecutaron y se detallan en sus informes.

| Incremento | Funcionalidad / clases | Comprobaciones |
|---|---|---|
| **2A — Núcleo bibliográfico** | Autor, Obra y Edicion; registros manuales y consulta; edición preferida; repositorios y migración desde sedes/socios | Dos ediciones de una obra; búsquedas por título original y español alternativo sin duplicar filas; preferencia; homónimos; ISBN; IDs OL; campos opcionales; rollback y migración desde versión 1 |
| **2B — Inventario** | Ejemplar, InventarioService y repositorio; alta, condición, baja y disponibilidad | Varias copias por edición; código duplicado; sede inexistente/inactiva; edición inexistente; ubicación/propiedad inicial; daño impide disponibilidad; baja preserva registro; conteos por sede |
| **2C — Géneros y etiquetas** | Vocabularios, público destinatario, asociaciones y aprobación manual/automática trazable | Reglas confiables aprobadas automáticamente; ambigüedades pendientes; decisiones humanas preservadas; género/etiqueta/público separados; resultados sin duplicados |
| **2D — Integración Open Library** | Validación técnica automática, auditoría selectiva, aceptación por política y decisiones persistentes | Aceptación automática y revisión de alertas diferenciadas; reimportación conserva UUID, vínculos y decisiones humanas; no crear ejemplares; fuentes preservadas y rechazos motivados |
| **2E — Integración y escala** | Recorrido completo de catálogo/inventario y consulta paginada con carga de prueba | Integridad referencial; datos de etapa 1 conservados; filtros combinados; conteos sin multiplicación por joins; mediciones de tiempo/memoria y planes SQL documentados |

Casos específicos a conservar como regresiones del importador: Haunting Adeline / Meow, materias ambiguas de Moby Dick y Los Miserables, exceso de autores en Drácula y ciencia frente a ciencia ficción. No se codifica un género correcto por intuición: cada expectativa requiere evidencia o se limita a que una materia ambigua no se apruebe automáticamente.

El pipeline actual ejecuta primero la preparación, que reconstruye su base de salida, y después el enriquecimiento; esa ejecución sólo seguirá usándose sobre una salida temporal. Las decisiones humanas deberán vivir en un registro durable que pueda reaplicarse, y la revisión bibliográfica y la de clasificaciones conservarán sus identidades separadas. Se definirá esto antes de editar una auditoría que luego pudiera sobrescribirse.

## 7. Decisiones aplicadas en 2A/2B

1. Mantener altas manuales con ISBN y portada opcionales, mientras la importación OL conserva su política más exigente. Español como alcance inicial; no agregar otros materiales ahora.
2. Código de inventario explícito y estable, normalizado a mayúsculas; no generar automáticamente una copia por libro importado.
3. Separar condición física y situación operativa; disponibilidad como comportamiento calculado y validado con la sede, sin forzar State fuera de los remitos.

Estas propuestas completan detalles del modelo inicial. No cambian las claves ni las cardinalidades del contrato compartido de Open Library.

## 8. Consolidación aplicada en 2E

El recorrido integrado combina fuente real y operaciones de demostración en una base temporal; verifica persistencia al reabrir, correcciones y decisiones humanas al reimportar, disponibilidad de varias ediciones, daño/baja y sede inactiva. Incluye preservación de socio inhabilitado y sedes de etapa 1.

La medición usa 1.000/10.000/100.000 obras sintéticas con varias ediciones/autores, vocabularios y estados, y copia física explícita de fixture. No es un importador ni una ampliación del catálogo real. Los 15 escenarios verifican resultados además de medir; capturan SQL y planes reales, memoria Python por llamada y RSS global. Las bases temporales se eliminan y el informe JSON conserva la evidencia.

Los planes y una regresión reproducible justificaron tres ajustes: página de obras antes de contar sus ediciones, sin filtros de texto vacíos; búsquedas de título por conjuntos para el caso independiente y evaluación sobre candidatas cuando hay otros filtros; comprobación de autoría por obra e índice de copias por sede/estado/código. La disponibilidad agrega primero sólo copias de la obra, sin recorrer el inventario entero de cada sede.

No cambió la semántica literal por fragmento, la edición preferida/respaldo, el orden estable, los límites ni la separación entre propiedad y ubicación. La suite incluye una regresión de coste en instrucciones SQLite, sin afirmar tiempos de CPU en pytest. La prueba previa que contaba SELECT incorpora WITH para seguir comprobando exactamente dos consultas por página, no una por obra.

En la última corrida todas las medianas locales con 100.000 obras quedaron bajo la referencia de 500 ms. Las páginas profundas ~442–466 ms siguen creciendo con OFFSET: no se consideran coste constante ni garantía para otra carga/equipo. No hizo falta incorporar FTS, otro servidor o paginación por clave en esta etapa. Ver método, valores y límites en el [informe 2E](./ETAPA_2E_RESULTADOS.md).
