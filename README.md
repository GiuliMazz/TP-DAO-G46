# Red de Bibliotecas Horizonte

TP integrador de Desarrollo de Aplicaciones con Objetos, grupo 46. Aplicación incremental de gestión bibliotecaria en Python.

## Estado actual

Están implementadas y consolidadas las etapas 1 (sedes/socios), 2 (catálogo, inventario, clasificación e integración Open Library) y 3 (primera interfaz Flet conectada). Con modos claro/oscuro, permite consultar el catálogo, administrar socios y sedes y registrar ejemplares, modificar su condición física o darlos de baja desde la ficha de una obra. Incluye guardados sin bloquear la interfaz y formularios recuperables. Préstamos y traslados siguen pendientes. Suite completa: **455 pruebas aprobadas**. Ver [complemento de inventario 3C.1](./docs/ETAPA_3C_1_RESULTADOS.md), [resultados de 3C](./docs/ETAPA_3C_RESULTADOS.md) y [medición de 3B.4 con 100.000 obras sintéticas](./docs/ETAPA_3B_4_RESULTADOS.md).

El catálogo local de 3B.2 contiene **100 obras reales, 100 ediciones españolas y 87 identidades de autor**, con 86 portadas locales. La base demo tiene **150 ejemplares ficticios, 50 por sede, y ocho socios ficticios**, separada de la operativa sin datos operativos ficticios. Ocho ediciones carecen de ISBN y catorce de portada: se conservan las ausencias. Las 100.000 obras sintéticas se mantienen para medir escala. La muestra histórica 2D sigue con sus cinco obras en otro archivo, sin cambios. Ver [paquete y fuentes](./datos/catalogo_local/README.md) y [resultados de 3B.2](./docs/ETAPA_3B_2_RESULTADOS.md).

La interfaz usa Flet 1.0.5; dominio, servicios y persistencia siguen usando sólo la biblioteca estándar. pytest es la dependencia de pruebas. ReportLab y Matplotlib se incorporarán al implementar reportes.

## Incorporarse al equipo

Leer [AGENTS.md](./AGENTS.md) para continuidad de agentes y la [guía de colaboración](./docs/COLABORACION.md) para reproducir un clon y publicar en GitHub. La etapa 4 sigue en diseño pendiente de revisión; no está implementada.

## Preparar el entorno

La ejecución de 3C se verificó con Python 3.14.10. Usar un entorno virtual desde la raíz del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

En Windows la activación de PowerShell es `.venv\Scripts\Activate.ps1`. El proyecto aún no se ha verificado en Windows; los comandos de pruebas y demostración son los mismos después de activar el entorno.

## Abrir la aplicación de escritorio

Con el entorno activado:

```bash
python main.py
```

También está la tarea de VS Code **Horizonte: aplicación de escritorio**, definida en [tasks.json](./.vscode/tasks.json). La ventana recomendada es 1440 × 960, con mínimo de escritorio de 900 × 700. En ventanas pequeñas aparece desplazamiento; al reducir el ancho, el menú muestra iconos con ayuda contextual.

La entrada abre la base demo ya preparada, con 100 obras reales y 150 ejemplares ficticios identificados como demostración. **No crea bases ni datos al iniciar**, tampoco necesita internet. Catálogo, ficha, socios y sedes están conectados. Desde la ficha se consulta el inventario, se registran ejemplares, se cambia su condición física y se confirma su baja. Estas acciones actualizan la disponibilidad al regresar al catálogo. Préstamos, reservas y remitos permanecen pendientes. Las consultas se ejecutan en un trabajador con conexiones propias y el buscador tiene debounce de 300 ms y descarte de respuestas obsoletas. Los guardados usan otro trabajador con un solo comando en curso: bloquean dobles envíos y no se cancelan al desconectar. Las imágenes se sirven desde archivos locales; cuando faltan o fallan se muestra una cubierta tipográfica con título, autor y «PORTADA ILUSTRATIVA». Su diseño es estable y no modifica los metadatos bibliográficos.

Para elegir otra base preparada, usar `python main.py --base datos/generados/catalogo_local/operativa.db`. Debe conservar su identificador de tipo junto al archivo SQLite. La operativa no recibe ejemplares o socios ficticios. Para abrir únicamente la maqueta histórica 3A sin persistencia, usar `python main.py --prototipo`; sus datos ilustrativos nunca se incorporan a las bases.

El botón de luna/sol junto a la sede alterna modo claro y oscuro durante la sesión, sin perder filtros o sede. El selector superior de sede de trabajo es independiente del filtro «Disponibilidad en sede» del catálogo; elegir una sede en el filtro limita las cantidades, y «Disponibles» exige stock local. La ficha muestra propiedad, ubicación y disponibilidad de todas las sedes. Cerrar una ventana anterior y volver a ejecutar para cargar cambios de código.

Para verificar los mismos controles en navegador local, opcionalmente:

```bash
python -m pip install -r requirements-preview.txt
python main.py --web --port 8550
```

Este modo de revisión no cambia el destino de escritorio del TP. La primera preparación del cliente Flet puede demorar. Ver [diseño de etapa 3](./docs/ETAPA_3_DISENO.md) y [alcance/verificaciones de 3A](./docs/ETAPA_3A_RESULTADOS.md).

## Ejecutar las pruebas

```bash
python -m pytest -q
```

La configuración limita el descubrimiento a [tests/](./tests). Cada prueba usa entidades aisladas o bases temporales: no cambia muestras ni bases reales. Incluye integridad, migraciones repetidas, rollback de varias escrituras y dos intentos concurrentes con el mismo DNI.

## Preparar el catálogo local y la demo sin internet

```bash
python -m herramientas.preparar_catalogo_local
python -m herramientas.preparar_socios_demo
```

Verifica el manifiesto y sus fuentes, integra las 100 obras con OL-2-LOCAL y genera [operativa.db](./datos/generados/catalogo_local/operativa.db), [demo.db](./datos/generados/catalogo_local/demo.db) y [catálogo auditable CSV](./datos/generados/catalogo_local/catalogo_auditable.csv). Las portadas ya están guardadas en [datos/catalogo_local/](./datos/catalogo_local/). No descarga datos al reproducir las bases.

La operativa contiene bibliografía real y cero sedes/socios/ejemplares ficticios. La demo incorpora Centro, Norte y Sur y códigos DEMO-0001 a DEMO-0150 mediante los servicios existentes. Conservar los identificadores `.tipo.json` junto a cada SQLite: impiden invertir tipos o adoptar archivos ajenos. Repetir no duplica UUID ni reinicia condición/baja/ubicación de las copias, ni sobrescribe correcciones humanas. Las salidas generadas están ignoradas por Git.

La carga de socios es un segundo comando explícito, exclusivo de la demo. Crea ocho identidades ficticias y repetirlo conserva sus UUID y los cambios manuales. No se ejecuta al abrir Flet. Ver [reglas y límite de recuperación de la semilla](./docs/ETAPA_3C_RESULTADOS.md).

Los metadatos provienen de las capturas locales verificables; la selección no equivale a una auditoría humana exhaustiva. Las dudas detectadas están registradas y apartadas. El [informe de 3B.2](./docs/ETAPA_3B_2_RESULTADOS.md) explica la política, procedencia, verificaciones y límites. El preparador no rehace la etapa 2 ni modifica la base histórica de prevalidación.

## Revisar clasificación y bibliografía

```bash
python -m herramientas.auditar_catalogo_local
```

Genera el [informe de cobertura](./docs/auditoria_catalogo/COBERTURA.md) y la [auditoría visual de 20 obras](./docs/auditoria_catalogo/auditoria_visual.html), autónoma y sin red. La cobertura aprobada es 53 obras con género, 26 con etiquetas y 16 con público. Las materias ambiguas quedan propuestas; no se completan edades ni géneros por intuición. Ver [hallazgos y límites](./docs/auditoria_catalogo/HALLAZGOS.md).

## Probar el primer recorrido

```bash
python -m biblioteca.demo
```

La demostración crea Norte, Centro y Sur, registra un socio ficticio, cambia su habilitación, rechaza el alta duplicada y vuelve a abrir la base para comprobar la persistencia del estado y del UUID. Todos los datos son de demostración y la base temporal se elimina al terminar. No genera la base operativa definitiva.

Para el recorrido de catálogo:

```bash
python -m biblioteca.demo_catalogo
```

Busca una obra por título original y por títulos de dos ediciones españolas, devuelve una ficha por obra y conserva la edición seleccionada al reabrir la base. Los datos de edición son de ejemplo; no corresponden a una importación real.

Para registrar copias y consultar disponibilidad por sede:

```bash
python -m biblioteca.demo_inventario
```

La demostración crea copias ficticias aptas, dañadas y dadas de baja, rechaza un código duplicado y muestra cómo inactivar una sede deja de ofrecer sus copias sin borrarlas. Usa SQLite temporal.

Para clasificar y revisar una obra:

```bash
python -m biblioteca.demo_clasificacion
```

Usa materias sintéticas para aprobar Fantasía, Magia y Juvenil en sus respectivos vocabularios. Después rechaza el género manualmente y comprueba que reprocesar no lo aprueba otra vez. Muestra historial y no crea ejemplares. Usa SQLite temporal.

## Integrar la muestra real de Open Library

Este recorrido histórico es opcional. Primero reconstruir la prevalidación con el [comando de colaboración](./docs/COLABORACION.md#recuperar-el-recorrido-histórico-opcional-de-etapa-2); las bases generadas no se incluyen en Git.

Con el entorno activado y desde la raíz:

```bash
python -m biblioteca.importacion \
  --fuente datos/generados/prevalidacion/catalogo_prevalidacion.db \
  --detalles datos/openlibrary/respuestas_originales.json \
  --destino datos/generados/integracion_2d/biblioteca.db
```

Lee la preparación y los detalles originales sin modificarlos ni acceder a la red. Crea/migra la base de destino, conserva evaluaciones y decisiones, e integra sólo candidatas aceptadas. Repetir el comando conserva identidades y metadatos existentes; no sobrescribe correcciones humanas ni crea ejemplares. El destino puede ser una base operativa existente y debe ser distinto de los archivos fuente. Los conflictos de título/autor o ISBN se informan para revisión y dejan intacta la integración de ese registro.

Resultado verificado sobre la muestra disponible: **cinco obras y cinco ediciones integradas**, dos ediciones ENRIQUECIDA para revisión y 993 PENDIENTE de detalle. Las dos señaladas son Mort (título breve) y Haunting Adeline (title=Meow frente a otro full_title); no se corrigen ni aceptan silenciosamente. La base de referencia sigue con sus siete ENRIQUECIDA originales: los estados nuevos viven en el destino.

La base indicada ya se generó localmente con ese contenido y cero ejemplares. Está fuera del control de versiones y puede reproducirse con el comando. `--solo-evaluar` conserva auditoría sin incorporar libros ni preparar vocabularios; `--limite N` acota las candidatas procesadas (1.000 por defecto).

La revisión se ofrece mediante [ImportacionService](./biblioteca/servicios/importacion_service.py): consultar evidencia/evaluaciones, aprobar/rechazar con motivo y corregir títulos explícitamente antes de la primera integración. Aprobar requiere controles técnicos completos; las decisiones humanas quedan vinculadas a la instantánea revisada. Las correcciones del catálogo ya existente se realizan con CatalogoService, porque reimportar conserva sus metadatos.

## Comprobar la etapa 2 consolidada

```bash
python -m biblioteca.demo_etapa2
```

La [demostración integrada](./biblioteca/demo_etapa2.py) usa una candidata bibliográfica real y una base temporal nueva. Registra sedes/socio ficticios, importa, busca por título original y español, agrega una edición y copias de demostración, registra daño/baja, revisa clasificación e inactiva una sede. Reabre y repite la importación, comprobando UUID, correcciones, preferencia, socio, copias y revisión. No modifica las fuentes ni la base generada en 2D.

Para reproducir la medición de escala:

```bash
python -m herramientas.medir_etapa2 \
  --tamanos 1000 10000 100000 \
  --repeticiones 5 \
  --limite-segundos 5 \
  --salida datos/generados/etapa2e/mediciones_finales.json
```

La herramienta genera SQLite temporales **sintéticas**, mide 15 escenarios con los servicios reales y guarda tiempos, memoria y planes SQL en JSON. Verifica resultados y claves foráneas; las bases de volumen se eliminan. El límite por llamada evita esperas indefinidas y registra una interrupción si ocurre, sin confundirla con una consulta rápida. La carga SQL directa es una fixture de desarrollo, no una vía alternativa de altas ni un importador.

Última medición local con 100.000 obras, 120.000 ediciones y 140.000 copias sintéticas: título original/alternativo alrededor de 21 ms, autor 30 ms, disponibilidad 0,35 ms y páginas profundas de catálogo/inventario 466/442 ms de mediana. Todos los escenarios quedaron bajo la referencia local de 500 ms, con una llamada previa por escenario. No es un SLA ni una medición de interfaz, concurrencia o almacenamiento en frío. Ver [informe completo de 2E](./docs/ETAPA_2E_RESULTADOS.md).

Esto no amplía el catálogo real: siguen siendo cinco obras integradas, dos candidatas para revisión y 993 pendientes.

## Organización

| Ubicación | Responsabilidad |
|---|---|
| [biblioteca/](./biblioteca/) | Código vigente de la aplicación |
| [interfaz/](./biblioteca/interfaz/) | Presentación Flet conectada mediante servicios, sin SQL ni reglas de negocio |
| [docs/](./docs/) | Diseño, UML, resultados y [referencias de la materia](./docs/referencias/) |
| [herramientas/openlibrary/](./herramientas/openlibrary/) | Pipeline bibliográfico vigente y contrato del importador |
| [datos/openlibrary/](./datos/openlibrary/) | JSON fuente para reconstruir la prevalidación en temporales o datos/generados |
| [archivo/](./archivo/) | DOT, PNG de diagramas y documento histórico versionados; ZIP, cachés y muestras duplicadas permanecen sólo locales |
| [dominio/](./biblioteca/dominio) | Entidades bibliográficas/operativas, vocabularios y clasificación revisable |
| [servicios/](./biblioteca/servicios) | Casos de uso y límites de transacción |
| [repositorios/](./biblioteca/repositorios) | SQL parametrizado y reconstrucción de entidades |
| [persistencia/](./biblioteca/persistencia) | Conexión y migración versionada, sin borrar datos |
| [importacion/](./biblioteca/importacion) | Adaptador de fuente, instantáneas, controles técnicos y ejecución offline |
| [tests/](./tests) | Pruebas con pytest |

Los repositorios se construyen con una conexión creada por `conectar`; los servicios reciben su repositorio. Cada escritura del servicio delimita una transacción sobre esa misma conexión. No ejecutar un servicio de escritura dentro de otra transacción: un caso compuesto debe coordinar sus repositorios en un único servicio. Cada hilo usa una conexión propia y el propietario de la conexión la cierra explícitamente.

Los listados tienen filtros por nombre/estado y límites de 1 a 100 registros por página (50 por defecto), con orden por nombre normalizado e ID. No garantizan una instantánea entre páginas si otros procesos modifican los datos durante la consulta.

## Reglas del primer módulo

- Sede: UUID estable; nombre, dirección, contacto y horarios obligatorios; estado activo/baja. Horarios es información descriptiva, sin calendario automático.
- Nombre de sede único sin distinguir mayúsculas ni espacios redundantes. Las sedes de baja conservan su nombre y pueden reactivarse.
- Socio: UUID estable, DNI, nombre completo, contacto y estado de habilitación; su registro es de toda la red.
- DNI como texto, único incluso en socios inhabilitados. Admite puntos, espacios y guiones entre cifras como presentación, pero conserva ceros iniciales y rechaza signos, letras y dígitos no ASCII. No se verifica autenticidad ni se exige una longitud exacta.
- Dar de baja o inhabilitar no elimina el registro. Cambiar al estado que ya tiene es idempotente.
- Los cambios inválidos no dejan datos parcialmente modificados; SQLite respalda la unicidad aunque se omita la comprobación del servicio.

El esquema operativo se prepara con `migrar(conexion)` y se versiona con `PRAGMA user_version`. Repetirlo conserva los datos. Rechaza bases con tablas ajenas sin versión y versiones más nuevas de las soportadas; no usar las SQLite del importador como base operativa.

El esquema vigente es 6; las migraciones conservan los datos de versiones 1 a 5. La migración 006 agrega un índice de ejemplares por sede/estado/código y no cambia registros. El catálogo muestra el título de la edición española preferida y busca también por el original y las demás ediciones. Los ISBN/portadas son opcionales en altas manuales; los ISBN proporcionados se comprueban. Una posible coincidencia de título/autor o ISBN requiere revisión explícita antes de continuar como registro distinto; nunca se omite la unicidad del ID OL. Los metadatos no generan existencias físicas.

El inventario se registra explícitamente sobre una edición y sede activa. Propiedad y ubicación son distintas; no hay una operación libre para mover copias o transferir propiedad. La disponibilidad para nueva asignación exige copia libre, apta, ubicada en su propietaria, sede activa y relaciones bibliográficas utilizables. Los totales registrados conservan bajas por historial y las discriminan de disponibles. Entrega de una copia asignada y traslados se incorporarán con circulación.

La clasificación separa Genero, Etiqueta y PublicoDestinatario. Cada asociación controla su revisión y conserva decisiones y evidencia. Las reglas iniciales son explícitas y versionadas; normalizan espacios/mayúsculas para comparar, conservando el texto fuente. Un contexto de crítica/estudio impide aprobar automáticamente un género. No se asigna Adulto por falta de información. Los filtros combinan los tres tipos y sólo usan APROBADO; las decisiones humanas prevalecen sobre reglas nuevas. Una aprobación automática puede volver a PROPUESTO al reevaluar su regla con contexto dudoso. La migración no carga vocabularios ni clasifica obras: preparar las reglas y procesar materias son acciones explícitas.

## Diseño y continuidad

- [Plan por etapas](./PLAN_DESARROLLO.md).
- [Análisis de etapa 0](./docs/ETAPA_0_DISENO.md) y [UML](./docs/UML_ETAPA_0.md).
- [Informe de etapa 1](./docs/ETAPA_1_RESULTADOS.md).
- [Informe de incremento 2A](./docs/ETAPA_2A_RESULTADOS.md).
- [Informe de incremento 2B](./docs/ETAPA_2B_RESULTADOS.md).
- [Informe de incremento 2C](./docs/ETAPA_2C_RESULTADOS.md).
- [Diseño de incremento 2D](./docs/ETAPA_2D_DISENO.md) y [resultados](./docs/ETAPA_2D_RESULTADOS.md).
- [Diseño de consolidación 2E](./docs/ETAPA_2E_DISENO.md) y [resultados y mediciones](./docs/ETAPA_2E_RESULTADOS.md).
- [Diseño de etapa 2](./docs/ETAPA_2_DISENO.md) y [UML de catálogo/inventario](./docs/UML_ETAPA_2.md), con 2A–2E completos a nivel de backend.
- [Diseño de etapa 3](./docs/ETAPA_3_DISENO.md) y [prototipo 3A](./docs/ETAPA_3A_RESULTADOS.md).
- [Nuevo alcance y diseño de 3B](./docs/ETAPA_3B_DISENO.md), [consulta SQL 3B.1 y modo oscuro](./docs/ETAPA_3B_1_RESULTADOS.md).
- [Catálogo local y demo 3B.2](./docs/ETAPA_3B_2_RESULTADOS.md), [insumos reproducibles](./datos/catalogo_local/README.md).
- [Diseño de 3C](./docs/ETAPA_3C_DISENO.md) y [resultados de administración conectada](./docs/ETAPA_3C_RESULTADOS.md).
- [Mantenimiento de inventario 3C.1](./docs/ETAPA_3C_1_RESULTADOS.md).
- [Diseño de etapa 4 para revisión](./docs/ETAPA_4_DISENO.md) y [UML propuesto](./docs/UML_ETAPA_4.md), sin implementación.
- [Contrato del importador](./herramientas/openlibrary/CONTRATO_PARA_UML.md).

El [índice del archivo](./archivo/README.md) explica qué se conservó y dónde está la versión vigente de cada material. Los archivos históricos no son el punto de entrada para continuar el desarrollo; las pruebas se descubren sólo en [tests/](./tests/).

El pipeline histórico de prevalidación permanece separado de las bases nuevas. Para reproducirlo, seguir las [instrucciones del pipeline](./herramientas/openlibrary/README.md). Las etapas 3B y 3C están completas, conservando SQL y reglas fuera de las vistas. Sigue la etapa 4: solicitudes y préstamo local, como base del posterior flujo interbibliotecario.
