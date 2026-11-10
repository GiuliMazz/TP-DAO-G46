# Plan de desarrollo incremental — Biblioteca, grupo 46

Fecha: 10 de noviembre de 2026. Estado: etapas 0, 1, 2 y 3 consolidadas. Interfaz Flet con catálogo, socios, sedes y alta física de ejemplares conectados; demo explícita de ocho socios. Suite total: **455 pruebas aprobadas**. Completado también el [mantenimiento de inventario 3C.1](./docs/ETAPA_3C_1_RESULTADOS.md). La etapa 4 queda en [diseño para revisión](./docs/ETAPA_4_DISENO.md), sin implementar. [Resultados de etapa 1](./docs/ETAPA_1_RESULTADOS.md), [consolidación 2E](./docs/ETAPA_2E_RESULTADOS.md), [3A](./docs/ETAPA_3A_RESULTADOS.md), [3B.4](./docs/ETAPA_3B_4_RESULTADOS.md) y [3C](./docs/ETAPA_3C_RESULTADOS.md).

Diseño de etapa 0: [análisis, reglas y verificaciones previstas](./docs/ETAPA_0_DISENO.md) y [UML inicial](./docs/UML_ETAPA_0.md). La propiedad estable con retorno está acordada; las políticas nuevas del diseño se identifican como propuestas.

Nombre acordado: **Red de Bibliotecas Horizonte**, con sedes ficticias Norte, Centro y Sur. Primer módulo: horarios informativos, DNI argentino único en la red y UUID estable. Los estados técnicos de importación se separan del comportamiento de Edicion al implementar catálogo, conservando el contrato compartido.

## Objetivo y fuentes

Desarrollar una aplicación de escritorio en Python, orientada a objetos, defendible académicamente y con persistencia local. Cumplir los ocho procesos obligatorios, las siete validaciones de negocio, al menos dos patrones de diseño y cuatro reportes no triviales de [tema1.pdf](./docs/referencias/tema1.pdf).

También se incluyen los compromisos de la [presentación original](./docs/referencias/Presentacion-Grupo_46.docx): integración Open Library, inventario con códigos, historial de lecturas, recomendaciones e incidencias logísticas. Las notificaciones y las multas no forman parte de la propuesta inicial: la consigna las menciona como opcional y reporte sugerido, respectivamente.

Referencias: [Semana 1](<./docs/referencias/Semana 1. 2026.pdf>), [diagramas existentes](./archivo/diagramas), [contrato bibliográfico](./herramientas/openlibrary/CONTRATO_PARA_UML.md) y [continuidad del catálogo](./archivo/documentos_iniciales/CONTINUAR_EN_CODEX_OPENLIBRARY.md). Se leyeron los archivos DOT para analizar clases y relaciones. El apunte de Semana 10 mencionado en la conversación no está disponible; no se atribuyen a ese archivo detalles no comprobados.

El catálogo inicial pasa a aproximadamente 100 obras reales con edición española, priorizando el préstamo interbibliotecario. La demo tendrá unos 150 ejemplares ficticios en Centro, Norte y Sur, en una base separada de la operativa. No se exigen metadatos opcionales ausentes ni se inventan datos para completarlos. Se mantiene la prueba de 100.000 obras sintéticas para comprobar escala mediante consultas acotadas, índices y paginación. [Decisión y pasos de reutilización](./docs/ETAPA_3B_DISENO.md).

## Tecnología y responsabilidades

| Componente        | Elección                           | Responsabilidad                                      |
| ----------------- | ----------------------------------- | ---------------------------------------------------- |
| Lenguaje          | Python                              | Entidades, comportamientos y casos de uso            |
| Interfaz          | Flet, inicialmente escritorio local | Mostrar datos, recoger acciones y presentar errores  |
| Persistencia      | SQLite con sqlite3                  | Integridad, consultas parametrizadas y transacciones |
| Pruebas           | pytest                              | Pruebas unitarias, de repositorios y de integración |
| PDF               | ReportLab                           | Exportar resultados ya calculados                    |
| Gráficos         | Matplotlib                          | Representar resultados de reportes                   |
| Catálogo externo | Open Library                        | Metadatos bibliográficos trazables                  |

Las versiones se fijarán al preparar el entorno, comprobando compatibilidad entre Python y las dependencias. Se incorporarán las bibliotecas en la etapa en que se necesiten.

- Dominio: controla invariantes y cambios propios. Por ejemplo, Socio controla su habilitación, Ejemplar su disponibilidad y Remito delega sus operaciones al estado actual.
- Servicios: coordinan entidades, repositorios y transacciones para realizar un caso de uso. Las reglas que requieren consultar varios registros se comprueban aquí y se respaldan con restricciones de base cuando corresponda.
- Repositorios: ejecutan SQL y reconstruyen entidades o resultados de consulta. No deciden políticas de préstamo.
- Interfaz: llama servicios; no ejecuta SQL ni calcula reglas de negocio. Los textos y habilitaciones de botones ayudan al usuario, pero el servicio siempre valida otra vez.
- Patrones: clases de State y Strategy relacionadas con el dominio; su ubicación física no debe crear dependencias circulares.
- Importación: infraestructura separada del inventario. Nunca crea ejemplares ni modifica operaciones de circulación.

Se conserva la estructura de carpetas propuesta por el usuario, añadiendo migraciones y un módulo de importación cuando se necesiten. No se crearán carpetas ni clases vacías por anticipado. Una transacción de un caso de uso debe compartir conexión entre repositorios; cada repositorio no confirmará cambios por separado.

## Decisiones de modelo a cerrar antes del módulo correspondiente

1. **Identidad bibliográfica — propuesta de etapa 0.** Conservar UUID local e ID OL opcional y único en la aplicación, permitiendo altas manuales. Mantener el contrato y las claves OL del importador intactos y resolver la correspondencia al integrar. Reimportar conserva identidad local y revisiones humanas. Ver [consecuencias y mapeo](./docs/ETAPA_0_DISENO.md). No inventar IDs OL para datos locales.
2. **Cardinalidades.** Obra tiene varias ediciones y una edición varios ejemplares. El borrador de una obra puede no tener ediciones; una obra publicada en el catálogo importado debe tener al menos una edición elegible. Una obra puede mostrarse sin ejemplares disponibles.
3. **Propiedad y ubicación — acordado.** El ejemplar conserva su sede propietaria durante el préstamo interbibliotecario. Antes de asignarlo al envío debe estar disponible y físicamente en esa sede de origen. Para entregarlo al socio debe haberse recibido conforme en la sede de retiro; no se exige que siga ubicado en la propietaria. La devolución del socio cierra su préstamo y el retorno a la propietaria se gestiona con otro remito. Un ejemplar pendiente de retorno no queda disponible para otro préstamo. No se incorpora transferencia permanente de propiedad en el alcance inicial.
4. **Solicitud y préstamo.** Aprobar o transportar una solicitud no inicia todavía el préstamo: este nace al entregar el ejemplar al socio; el vencimiento se calcula desde esa entrega. Una reserva tampoco equivale a un préstamo.
5. **Reglas aún propuestas.** Plazos de préstamo y retiro, prioridades de reservas, cancelaciones, sedes permitidas para devolución y tratamiento de operaciones existentes al dar de baja una sede. Se documentarán con ejemplos antes de implementarlas, sin presentarlas como exigencias textuales de la cátedra.
6. **Remitos e incidencias.** El esquema existente es Pendiente → Empaquetado → Despachado → En tránsito → Recibido, con cancelación antes del despacho y recepción con incidencias. Antes de implementarlo se precisará el tratamiento de recepciones parciales, extravíos y resolución de incidencias; daño, falta y destrucción son resultados por ejemplar y no simples cambios globales. No se convertirá un faltante en recepción física. Una devolución no libera un ejemplar dañado ni uno pendiente de retorno.
7. **Baja de sede.** Bloquea nuevas operaciones hacia o desde ella. La política para recibir o resolver operaciones previas debe preservar su trazabilidad; no se eliminará su historia.
8. **Clasificación.** Propuesta, aprobación y rechazo se conservan por asociación. Las recomendaciones usarán clasificaciones aprobadas; el catálogo informará el estado de los datos. Devolver un libro no demuestra que se haya leído.

Estas decisiones actualizarán el UML con responsabilidades, métodos y cardinalidades antes del código afectado. Los diagramas actuales son una referencia revisable.

### Ejemplo de la política acordada

Un ejemplar de Centro se solicita para retirar en Norte. Centro sigue siendo su propietaria en todo el recorrido:

| Paso | Ubicación o situación física | Comprobación |
|---|---|---|
| Asignación al envío | Centro | Disponible, propietaria igual al origen y sedes activas |
| Traslado de ida | En tránsito | Ejemplar bloqueado para otras asignaciones; historial de remito |
| Recepción conforme | Norte | Recepción del ejemplar registrada antes de habilitar la entrega |
| Entrega al socio | En poder del socio | Nace el préstamo y se calcula el vencimiento |
| Devolución en Norte | Norte | Se cierra el préstamo y se registra condición física; pendiente de retorno |
| Traslado de retorno | En tránsito hacia Centro | Otro remito, sin reabrir el préstamo del socio |
| Recepción en Centro | Centro | Se evalúa disponibilidad según condición física y reservas |

Este recorrido es una política de diseño acordada, no una exigencia textual de retorno en la consigna. Se comprobará también que una recepción con daño o faltante no habilite una entrega ni una disponibilidad indebida.

## Etapas y criterios de salida

### 0. Cerrar análisis y UML

Funcionalidad: definir casos de uso, glosario, estados, identidad y reglas de la primera etapa. Registrar la correspondencia entre requerimientos, casos de uso y verificaciones.

Clases: revisar Obra, Edicion, Autor, Genero, Etiqueta, Ejemplar, Sede, Socio, SolicitudPrestamo, Prestamo, Devolucion, Reserva, Remito, DetalleRemito, EventoRemito y RevisionRecepcion, sin implementarlas todas.

Verificación: recorrer en papel un préstamo local y uno interbibliotecario completo, con devolución y retorno, y ejemplos de socio inhabilitado, sede inactiva y ejemplar ocupado. Acordar el UML inicial y la política de identidad antes de persistir datos de la aplicación.

### 1. Primer caso completo: sedes y socios, sin interfaz

Funcionalidad: altas, consultas, modificación, habilitación de socios y baja lógica de sedes. Crear sólo el esquema y repositorios necesarios, con migraciones simples versionadas.

Clases: Sede, Socio, sus servicios y repositorios. Entidades validan sus datos y cambios de estado; servicios verifican duplicados y coordinan persistencia.

Pruebas pytest: campos obligatorios, documento duplicado según normalización acordada, cambios de habilitación y baja sin borrado de historia. Integración con SQLite temporal: guardar/recuperar, unicidad, migraciones y rollback. No usar la base real en pruebas.

Salida: casos de uso comprobables desde pruebas, persistentes después de reabrir la conexión.

Estado: backend de sedes/socios completado, con 81 casos pytest aprobados y demostración temporal ejecutada. Interfaz pendiente de etapa 3. Detalles y límites en el informe de resultados.

### 2. Catálogo e inventario

Diseño incremental: [responsabilidades, políticas y pruebas](./docs/ETAPA_2_DISENO.md) y [UML específico](./docs/UML_ETAPA_2.md). Incrementos 2A–2E completos a nivel de backend; suite actual: 347 casos aprobados. Las búsquedas incluyen título original, todas las ediciones españolas y filtros combinables por géneros, etiquetas y público aprobados. La ficha usa la edición preferida. El inventario separa propiedad, ubicación, condición y baja, sin crear copias desde los metadatos. La clasificación conserva fuentes, versiones de reglas y decisiones humanas. La integración offline evaluó 1.000 candidatas, incorporó cinco obras/ediciones y conservó dos para revisión y 993 pendientes; repetirla mantiene identidades, metadatos y auditoría.

Funcionalidad: estabilizar validaciones del importador, incorporar un subconjunto real auditado, consultar obras/ediciones con filtros y páginas, dar de alta ejemplares explícitamente y consultar disponibilidad por sede.

Clases: Obra, Edicion, Autor, Genero, Etiqueta, asociaciones de clasificación, Ejemplar; servicios de catálogo e inventario y repositorios correspondientes. Materias originales quedan en infraestructura si no requieren comportamiento de dominio.

Pruebas: ISBN válidos e inválidos; título usable; idioma y portada de edición; autor frente a colaborador; estados de validación; varios ejemplares por edición y varias ediciones por obra; códigos únicos; relaciones válidas; importación repetible que preserve revisiones humanas. Regresiones con evidencia para títulos y géneros problemáticos de la muestra.

Rendimiento: índices según filtros y relaciones, resultados acotados, orden estable y paginación. Medir consultas y planes SQL con un conjunto de hasta 100.000 obras sintéticas identificado como prueba de carga, sin publicarlo como catálogo real. Evaluar búsqueda de texto de SQLite sólo si las mediciones lo justifican; un índice común no garantiza acelerar búsquedas por fragmento.

Salida: catálogo consultable e inventario separado, sin duplicar obras por sus ediciones. El importador no reconstruye destructivamente una base operativa. Dumps masivos quedan fuera del camino crítico y se evalúan sólo si hacen falta más datos.

Estado: recorrido conjunto con reapertura/reimportación verificado; mediciones en 1.000/10.000/100.000 obras sintéticas documentadas. Se corrigieron consultas y se agregó un índice por evidencia de planes SQL. Medianas locales con 100.000 obras: títulos ~21 ms, autor ~30 ms, disponibilidad ~0,35 ms, página profunda de catálogo ~466 ms e inventario ~442 ms. No equivale a 100.000 obras reales ni garantiza otros equipos/concurrencia. [Resultados y límites de 2E](./docs/ETAPA_2E_RESULTADOS.md).

### 3. Primera interfaz Flet

División acordada en [diseño de etapa 3](./docs/ETAPA_3_DISENO.md): 3A prototipo, 3B catálogo conectado y medición integrada con datos sintéticos, 3C administración conectada. Las tres están completadas. El [complemento 3C.1](./docs/ETAPA_3C_1_RESULTADOS.md) incorpora condición física y baja de ejemplares usando los servicios actuales. La suite vigente suma 455 casos. No se ha implementado circulación.

Datos de 3B.2: paquete autocontenido de 100 obras reales/100 ediciones españolas, 87 identidades de autor y 86 portadas locales. OL-2-LOCAL admite ausencias de ISBN/portada sin omitir identidad/relación/idioma; OL-1 sigue disponible. El comando offline reproduce operativa y demo independientes, esta última con 150 ejemplares DEMO, 50 por sede. Se verificaron reapertura, identidad estable e integridad al repetir. [Fuentes y reproducción](./datos/catalogo_local/README.md).

Funcionalidad: navegación y pantallas de sedes, socios, catálogo y detalle con disponibilidad. Adoptar las referencias visuales como orientación: panel, catálogo, circulación y logística.

Clases: vistas y componentes mínimos que dependen de los servicios existentes. Sin SQL ni reglas de negocio en eventos de controles.

Pruebas: errores del servicio traducidos a mensajes, actualización tras guardar, filtros y páginas sin duplicados. Verificación manual documentada de navegación, formularios y redimensionamiento. Consultas/importación que demoren no deben bloquear la interfaz; se respetará la propiedad de conexiones SQLite entre tareas.

Salida: primer recorrido visible y persistente; la misma regla se cumple invocando el servicio fuera de Flet.

### 4. Solicitudes y préstamo local, con base de Strategy

Funcionalidad propuesta, aún sin implementar: solicitar una obra, asignar ejemplar, cancelar antes de entrega y efectuar la entrega. Evitar dos compromisos incompatibles y calcular vencimiento desde entrega efectiva. Agregar pantallas de circulación después de aprobar las reglas.

Diseño propuesto: SolicitudPrestamo, AsignacionEjemplar, Prestamo y ampliación de Ejemplar; servicios de solicitud/entrega y repositorios específicos. Ver [reglas, transacciones y decisiones pendientes](./docs/ETAPA_4_DISENO.md) y [UML](./docs/UML_ETAPA_4.md). A pedido del usuario, Strategy permanece previsto para etapa 5, cuando ambas variantes tengan comportamientos reales; no se crean clases vacías en etapa 4.

Pruebas: éxito, socio inhabilitado, ejemplar ocupado, sede inactiva, propietario distinto del origen, ubicación incorrecta, fechas inválidas y entrega repetida. Verificar rollback de préstamo/asignación/ejemplar y que dos intentos no obtengan el mismo ejemplar. Las fechas de prueba son explícitas para evitar depender del día de ejecución.

Salida: préstamo local consistente y vencimiento calculado desde entrega efectiva.

### 5. Préstamo interbibliotecario y logística con State

Funcionalidad: completar Strategy local/interbibliotecaria, preparar remitos con uno o varios ejemplares, empaquetar, despachar, seguir tránsito, recibir y registrar incidencias e historial. Integrar vista logística.

Clases: EstrategiaPrestamoLocal, EstrategiaPrestamoInterbibliotecario, Remito, EstadoRemito y estados concretos, DetalleRemito, EventoRemito, RevisionRecepcion; servicios y repositorios de logística. Remito delega transiciones a State; LogisticaService coordina su persistencia y los efectos sobre ejemplares y solicitudes.

Pruebas: todas las transiciones válidas y prohibidas; cancelación antes de despacho; ejemplar no incluido en dos envíos activos; origen/destino; rechazo de nuevas operaciones con sede inactiva; revisión por ítem y faltantes; historial ordenado; recepción repetida y rollback ante fallos. No entregar al socio antes de la recepción conforme. Guardar y reconstruir el estado conserva el comportamiento.

Salida: solicitud interbibliotecaria → traslado → recepción → entrega al socio, con trazabilidad completa y ambos patrones demostrables.

### 6. Devoluciones y retorno

Funcionalidad: registrar fecha y condición física, cerrar préstamo una sola vez, bloquear material dañado y gestionar traslado de retorno cuando corresponda.

Clases: Devolucion, Prestamo, Ejemplar, Remito y revisión; servicios de devolución y logística sobre repositorios existentes.

Pruebas: devolución normal/tardía/dañada, doble devolución, sede de recepción no permitida, retorno a propietaria y ausencia de disponibilidad indebida durante el retorno. El cierre del préstamo y el registro de devolución se confirman juntos.

Salida: ciclo completo local e interbibliotecario, incluida restitución física, sin confundir deuda del socio y transporte.

### 7. Reservas

Funcionalidad: reservar una obra en sede de retiro, ordenar la cola con criterio documentado, asignar ejemplar, establecer plazo, cancelar, vencer y convertir a solicitud sin duplicarla.

Clases: Reserva, Obra, Ejemplar, Socio y SolicitudPrestamo; ReservaService y repositorio. Reserva controla sus cambios propios; el servicio coordina la cola y la disponibilidad.

Pruebas: orden y desempate, reserva activa duplicada, socio inhabilitado/sede inactiva, cancelación y liberación, vencimiento, conversión única y competencia entre reserva y préstamo directo. No saltear la cola al devolver un ejemplar.

Salida: reservas integradas al flujo existente, sin dobles asignaciones.

### 8. Lecturas y recomendaciones

Funcionalidad: consultar historial de préstamos, marcar obras leídas explícitamente y recomendar por géneros/etiquetas aprobados, mostrando disponibilidad por sede.

Clases: RegistroLectura y servicios de historial y recomendaciones, repositorios de consulta existentes. No se agrega otro patrón obligatorio ni servicios externos.

Pruebas: no inferir lectura por devolución, no repetir registros incompatibles, excluir obra de referencia, puntuación y desempate reproducibles, ausencia de afinidades inventadas y disponibilidad correcta. Probar resultado vacío.

Salida: compromisos complementarios de la presentación cubiertos con reglas explicables.

### 9. Reportes, PDF y gráficos

Funcionalidad: implementar cuatro reportes con filtros por fecha/sede y resultados verificables:

1. Préstamos activos/vencidos por sede: cantidades, días de atraso y tasa de vencidos con denominador explícito.
2. Disponibilidad por sede y obra: totales por estado, disponibles y porcentaje utilizable, sin contar ejemplares de otra ubicación como presentes.
3. Demanda interbibliotecaria: obras más solicitadas, cantidad de solicitudes y destinos, sin contar líneas de remito como nuevas solicitudes.
4. Desempeño logístico: envíos por origen/destino, tiempo medio de tránsito de los finalizados, tasa de conformidad e incidencias por tipo. Separar envíos pendientes y cancelados del denominador según política documentada.

Clases: ReportesService y repositorio de consultas agregadas; exportadores PDF y generadores de gráficos como componentes de presentación. ReportLab y Matplotlib reciben resultados ya calculados, no acceden directamente a SQL.

Pruebas: base pequeña con resultados calculados a mano, límites de fechas, denominadores cero, duplicación por joins y coherencia entre tabla/gráfico/PDF. Verificar PDFs legibles, con título, filtros, fecha y páginas.

Salida: cuatro reportes no triviales accesibles desde la interfaz y exportables.

### 10. Integración, rendimiento y defensa

Funcionalidad: completar panel con indicadores ya disponibles, recorrido final y entrega reproducible. Datos reales bibliográficos y datos operativos de demostración se identifican por separado.

Pruebas: recorrido integral con varias sedes, socios y ejemplares; restricciones de todas las capas; recuperación tras fallos de transacción; migración sobre copia de base; carga del catálogo y revisión manual Flet/PDF. Acordar metas de tiempo en el equipo real antes de medir y no afirmar rendimiento sin evidencia.

Salida: código y dependencias fijadas, instrucciones, base de demostración y respaldo, UML actualizado, matriz de requisitos/pruebas, resultados de pytest y guion para defender State, Strategy y las decisiones de dominio.

## Forma de trabajo por incremento

Antes de cada módulo: explicar requerimientos, responsabilidades, relaciones, decisiones y criterio de aceptación. Implementar sólo ese alcance, agregar pruebas significativas y ejecutar las verificaciones antes de avanzar. Documentar cambios de diseño antes de aplicarlos. Una etapa termina con evidencia y una revisión de lo realizado.

Completado 3B.4: Flet consulta el catálogo local y la ficha, con cargas/errores, un trabajador, conexiones independientes, debounce y descarte de respuestas obsoletas. Se conservan las 100 obras reales, las bases separadas y 150 copias demo; no hay siembra al iniciar. Se prepararon [cobertura](./docs/auditoria_catalogo/COBERTURA.md), [muestra visual de 20 obras](./docs/auditoria_catalogo/auditoria_visual.html) y [medición del cliente con 100.000 obras sintéticas](./docs/ETAPA_3B_4_RESULTADOS.md), con límites explícitos. La medición justificó un ajuste de disponibilidad local sin nuevos índices ni esquema. Hay cubiertas ilustrativas identificadas para las imágenes ausentes. Completado [3C](./docs/ETAPA_3C_RESULTADOS.md): socios/sedes e inventario conectados mediante los servicios; ocho socios ficticios preparados explícitamente. Completado también [3C.1](./docs/ETAPA_3C_1_RESULTADOS.md), con condición y baja en la interfaz. Próximo: revisar [diseño y decisiones de etapa 4](./docs/ETAPA_4_DISENO.md) antes de implementar solicitudes y préstamo local. Préstamos interbibliotecarios, remitos y sus patrones siguen como prioridad de las etapas posteriores. No ampliar el catálogo ni agregar optimizaciones sin evidencia.
