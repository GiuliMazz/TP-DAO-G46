# Etapa 0 — Análisis y diseño inicial

Fecha: 3 de noviembre de 2026. Estado: alcance de sedes y socios acordado e implementado. Ver [resultados de etapa 1](./ETAPA_1_RESULTADOS.md).

## 1. Alcance y decisiones

Este documento precisa el [plan de desarrollo](../PLAN_DESARROLLO.md) a partir de la [consigna](./referencias/tema1.pdf), la [presentación original del grupo](./referencias/Presentacion-Grupo_46.docx), los [diagramas de referencia](../archivo/diagramas) y el [contrato del importador](../herramientas/openlibrary/CONTRATO_PARA_UML.md).

Se distinguen tres orígenes de las reglas:

- **Consigna:** requisito obligatorio, identificado como RF o RN en las tablas siguientes.
- **Acuerdo:** decisión aceptada en la conversación: stack, capas, State/Strategy y propiedad estable con retorno.
- **Propuesta:** detalle que el equipo debe revisar antes de implementar el módulo afectado. No se atribuye a la cátedra.

Este documento registra el análisis previo a la implementación. Los escenarios enumerados sirven como criterios de aceptación; los resultados ejecutados de cada incremento se registran por separado.

El software inicial será de escritorio, operado por personal de la biblioteca. El socio es el titular de las operaciones; no hace falta agregar autenticación, roles o un portal independiente para cubrir la consigna. Los gráficos de referencia orientan la interfaz futura, sin fijar su implementación.

**Nombre acordado:** Red de Bibliotecas Horizonte. El nombre de la red pertenece a la configuración/presentación general de la aplicación, no a cada registro Sede. Las sedes ficticias de demostración serán Norte, Centro y Sur; cada una almacena únicamente su nombre particular. No hace falta crear una entidad Red ni soporte para múltiples redes.

## 2. Glosario y responsabilidades del dominio

| Concepto / clase | Responsabilidad y comportamiento |
|---|---|
| Obra | Identidad intelectual y datos comunes. Administrar asociaciones con autores y clasificaciones; no contiene disponibilidad física propia. |
| Edicion | Publicación concreta de una obra. Preservar datos bibliográficos coherentes y su relación con la obra. Propuesta revisada: candidatura, enriquecimiento y aprobación de la importación pertenecen a infraestructura, no a su comportamiento de dominio. |
| Autor | Identidad y nombre del autor; los colaboradores de edición no reemplazan a los autores de obra. |
| Genero / Etiqueta | Vocabulario controlado; sus asociaciones con una obra pueden aprobarse o rechazarse conservando procedencia. |
| Ejemplar | Copia física con código único, propietaria, ubicación y condición física. Controlar asignación y cambios operativos; no quedar disponible en tránsito o en préstamo. |
| Sede | Biblioteca integrante de la red; validar sus datos y controlar activación/baja lógica. |
| Socio | Persona registrada en la red; validar sus datos y controlar habilitación. No requiere pertenecer a una única sede. |
| SolicitudPrestamo | Pedido de una obra para un socio, con origen y retiro. Controlar asignación y avance hasta entrega/cancelación. |
| Prestamo | Entrega efectiva de un ejemplar a un socio. Controlar vencimiento y cierre único por devolución. |
| Devolucion | Registro de recepción del ejemplar desde el socio, fecha, sede y condición física observada. |
| Reserva | Espera por una obra en sede de retiro. Controlar asignación, cancelación, vencimiento y conversión única a solicitud. |
| Remito | Documento de traslado entre sedes. Controlar contenido y delegar transiciones a State. |
| DetalleRemito | Ejemplar incluido y vínculo a la solicitud de ida o al préstamo del retorno. Registrar su resultado individual. |
| EventoRemito | Hecho histórico: instante, transición y observación. No sustituye el estado actual ni se sobrescribe para cambiarlo. |
| RevisionRecepcion | Evaluación física de un ítem de remito: conforme, daño, extravío/faltante o destrucción, según política del módulo. |
| RegistroLectura | Declaración explícita de lectura por el socio; un préstamo devuelto no implica lectura completada. |

**Origen del préstamo:** sede propietaria que aporta el ejemplar. **Sede de retiro:** donde se entrega al socio; coincide con el origen para un préstamo local. **Ubicación:** sede donde está físicamente, o ausencia de sede física cuando está en tránsito, con el socio o no localizado; la situación se explica por su estado y operación asociada.

Las entidades trabajan sobre datos y relaciones necesarios para la operación. No se cargará toda la colección de una sede o todas las ediciones/ejemplares para construir un objeto: las consultas grandes se resolverán con repositorios y paginación.

## 3. Trazabilidad de los procesos obligatorios

Los números RF01–RF08 siguen el orden de la consigna. Los nombres de casos de uso son del proyecto.

| ID | Caso de uso / resultado | Clases principales | Etapa | Verificación prevista |
|---|---|---|---|---|
| RF01 | CU01: administrar sedes, consultar y dar de baja sin borrar | Sede, SedeService, SedeRepository | 1 y 3 | D01–D04; datos, unicidad y relectura desde SQLite |
| RF02 | CU02: administrar socios y su habilitación | Socio, SocioService, SocioRepository | 1 y 3 | D05–D09; datos, documento y estado |
| RF03 | CU03: administrar obras, ediciones y ejemplares propios de una sede | Obra, Edicion, Ejemplar, servicios y repositorios de catálogo/inventario | 2 y 3 | Varias ediciones/copias, código único, importación repetible |
| RF04 | CU04: solicitar, asignar y entregar préstamo local/interbibliotecario | SolicitudPrestamo, Prestamo, estrategias, PrestamoService | 4 y 5 | Recorridos L e I y rechazos N1–N5 |
| RF05 | CU05: empaquetar, despachar, seguir y recibir con remito | Remito, estados, DetalleRemito, EventoRemito, LogisticaService | 5 y 6 | Transiciones permitidas/prohibidas, ida y retorno, historial persistido |
| RF06 | CU06: consultar disponibilidad de ejemplares por sede | Ejemplar, Sede, CatalogoService y repositorios | 2 y 3 | Excluir ocupados/en tránsito; distinguir propietaria de ubicación |
| RF07 | CU07: reservar, asignar, cancelar y atender espera | Reserva, ReservaService, SolicitudPrestamo | 7 | Orden de cola, vencimiento y ausencia de doble asignación |
| RF08 | CU08: registrar devolución y condición física | Prestamo, Devolucion, Ejemplar, servicio de devoluciones | 6 | Devolución única, daño y retorno sin reabrir préstamo |

### Validaciones obligatorias

| ID | Regla de la consigna | Dónde se garantiza | Comprobación prevista |
|---|---|---|---|
| RN01 | No prestar ejemplares no disponibles | Ejemplar controla cambios; servicio consulta conflictos; transacción/restricciones impiden doble ocupación | N2; dos intentos no consiguen el mismo ejemplar |
| RN02 | No prestar a socios inhabilitados | Socio informa habilitación; servicio la comprueba al entregar, aunque la solicitud fuese previa | N1; inhabilitar entre solicitud y entrega |
| RN03 | Controlar vencimientos | Prestamo compara vencimiento con fecha de consulta; estrategia recibe política de plazo | Día de vencimiento, día posterior y préstamo ya devuelto |
| RN04 | Mantener trazabilidad del remito en todo el trayecto | Remito/State y EventoRemito, guardados juntos | Cada transición deja un evento, incluso cancelación; reconstrucción desde SQLite |
| RN05 | Evitar duplicados de socios, catálogo y ejemplares | Servicios y restricciones UNIQUE; importación por identidad de fuente | Documento/código/ID OL repetidos; reimportar no duplica ni pierde revisiones |
| RN06 | El ejemplar pertenece a la sede de origen del préstamo | Relación Ejemplar–Sede propietaria y validación del servicio | N3; origen es propietario aunque la entrega ocurra en retiro |
| RN07 | No iniciar préstamos, reservas ni envíos con sede de baja, hacia o desde ella | Servicios consultan las sedes involucradas dentro del caso de uso | N4; comprobar tanto origen como destino, y revalidar antes de entrega/despacho |

### Patrones, reportes y compromisos

| Compromiso | Diseño y evidencia prevista |
|---|---|
| Dos patrones obligatorios | State en Remito y Strategy en procesamiento local/interbibliotecario. Probar sustitución de estrategias y comportamiento de estados reconstruidos; un enum o dos ramas if por sí solos no demuestran estos patrones. |
| Al menos cuatro reportes no triviales | Activos/vencidos; disponibilidad; demanda interbibliotecaria; desempeño logístico. Agregaciones, filtros y denominadores explícitos según el plan. Verificar con una base pequeña calculada a mano. |
| Open Library | Importación/validación/normalización con procedencia, español confirmado en edición y clasificación revisable. Separada de ejemplares físicos. |
| Códigos de inventario | Únicos en toda la red y consultables; no exigen lector físico de códigos. |
| Historial y recomendaciones | Préstamos consultables, lecturas explícitas y afinidad por géneros/etiquetas aprobados, con disponibilidad por sede. |
| Incidencias | Resultado individual de recepción e historial; un faltante no se marca como físicamente recibido. |
| Capacidad del catálogo | Paginación, consultas acotadas, índices medidos; prueba de carga identificada como sintética. No exige importar 100.000 obras reales para terminar el TP. |

Notificaciones, multas, transferencia permanente de propiedad y nuevos servicios externos quedan fuera de la primera versión. No se elimina ningún compromiso de la presentación por ser opcional en la consigna.

## 4. Identidad bibliográfica: propuesta de integración

**Problema:** el UML existente propone UUID local e ID OL; el contrato de intercambio identifica obra/edición directamente por OL. Usar sólo OL impediría registrar materiales locales sin inventar un identificador externo. Usar título o ISBN como identidad de obra mezclaría publicaciones distintas.

**Propuesta:** conservar los UUID locales del UML como identidad estable de las entidades de aplicación y guardar `id_openlibrary` opcional y único en Obra, Edicion y Autor. Los IDs locales se generan una sola vez, no en cada importación. SQLite los almacena como texto. Géneros y etiquetas de fuentes distintas se mapean al vocabulario local, sin copiar ciegamente IDs numéricos.

El contrato y la base de prevalidación del importador permanecen iguales. En la etapa 2 se implementará la integración explícita:

1. Buscar cada obra por su ID OL. Crear identidad local sólo si no existe; si existe, conservarla y actualizar sólo campos que la política de importación permita.
2. Resolver cada edición por su propio ID OL y mapear su `obra_id` externo a la obra local. Varias ediciones del mismo work no crean nuevas obras.
3. Resolver autores por ID OL comprobado y asociaciones por sus claves estables. Los identificadores técnicos `LOCAL-…` del pipeline no son IDs OL válidos: conservar su procedencia y tratarlos aparte antes de integrar; no presentarlos como identidad externa verificada.
4. Mantener materias originales, procedencia y estados de revisión; no sobrescribir correcciones humanas con valores de la fuente.
5. Mantener separadas la SQLite de preparación y la operativa. La operación de importar no elimina la base de la aplicación ni genera ejemplares.

Consecuencias: hay un mapeo entre dos esquemas, pero no se cambia el contrato compartido y las altas manuales siguen siendo posibles. Una coincidencia textual con un registro manual se audita; no se fusiona automáticamente. El ISBN no es único global de la tabla como sustituto del ID OL. Los detalles SQL se diseñarán en etapa 2; nada de esto se implementa en etapa 0.

### Frontera de la validación de ediciones — propuesta revisada

`PENDIENTE`, `ENRIQUECIDA`, `VALIDADA`, `RECHAZADA`, `idioma_verificado`, las evidencias de fuente y los motivos de descarte describen el procesamiento de una fuente. Se conservan en los registros técnicos del importador con su significado actual; no se eliminan del contrato ni se convierten en disponibilidad de un libro.

La entidad Edicion de la aplicación no necesita métodos para pasar de candidata a enriquecida. Sí debe proteger invariantes propias: título no vacío, pertenencia a una obra, datos coherentes e ISBN válido cuando se proporciona. La política de calidad de Open Library comprueba además idioma español en la fuente, portada de edición y los requisitos de exportación acordados. La aceptación podrá ser automática bajo una política trazable, con revisión humana de casos señalados y muestras; no requiere revisar individualmente todas las obras. El servicio sólo integra registros aceptados; este acuerdo no promueve automáticamente las 993 ediciones pendientes de la muestra.

La interfaz técnica de auditoría podrá consultar estados de importación sin agregarlos a las pantallas de circulación ni a cada entidad Edicion. Una edición cargada manualmente no debe fingir que fue validada por Open Library. La ubicación exacta de la información técnica al integrar se diseñará en etapa 2; no se introduce ahora otra jerarquía de clases.

## 5. Primer módulo: sedes y socios

### Modelo propuesto

| Clase | Datos mínimos | Comportamiento propio |
|---|---|---|
| Sede | id UUID estable, nombre, dirección, contacto, horarios, activa | Crear/modificar datos válidos; activar; dar de baja; informar si está activa |
| Socio | id UUID estable, documento normalizado, nombre completo, contacto, estado | Crear/modificar datos válidos; habilitar; inhabilitar; informar si está habilitado |

Una Sede no es dueña de los socios: pertenecen a la red. No hay asociación obligatoria Socio–Sede. No se agrega una clase Persona, una jerarquía de socios ni State para dos indicadores simples. La identidad no cambia al editar nombre o documento.

### Políticas del primer módulo

- Sede: nombre, dirección, contacto y horarios como texto obligatorio no vacío tras compactar espacios. Se conservan horarios para cubrir el proceso obligatorio 1: son un dato informativo, sin calendario automático ni restricciones de préstamo por apertura.
- Nombre de sede único dentro de esta red después de compactar espacios y comparar sin distinguir mayúsculas. `Centro` y ` centro ` coinciden; no se eliminan acentos ni se hace coincidencia aproximada. Mantener unicidad incluso si está de baja y ofrecer reactivación en vez de duplicarla.
- Socio: nombre completo, documento y contacto obligatorios. No partir el nombre forzosamente ni exigir correo electrónico si se cuenta con otro contacto.
- **Documento acordado:** la Red de Bibliotecas Horizonte registra socios mediante DNI argentino, único en toda la red. Es una política de inscripción de esta versión, no una regla sobre nacionalidad. No se incorporan tipo de documento, país emisor ni otros documentos.
- El DNI se almacena como texto: quitar puntos, guiones y espacios de presentación entre cifras; exigir dígitos ASCII, sin convertir a entero ni eliminar ceros iniciales. Rechazar letras, signos en los extremos, otros símbolos y resultado vacío. No se impone una longitud exacta ni se afirma autenticidad a partir del formato.
- La unicidad incluye socios inhabilitados; al editar se excluye al propio registro. No se fusionan personas por nombre. El UUID estable identifica al socio y no cambia al corregir el DNI.
- Contacto es texto libre no vacío; no se implementan validadores exhaustivos de correo/teléfono ni servicios de verificación.
- Alta de sede activa y alta de socio habilitado. Cambiar al estado actual es idempotente: no duplica datos ni genera un error innecesario.
- Baja de sede e inhabilitación de socio conservan el registro y sus vínculos. No hay eliminación física en los casos de uso. Se permite consultar y corregir sus datos aunque estén inactivos.
- Un préstamo vencido se detecta, pero no inhabilita automáticamente ni produce multas. La inhabilitación es explícita hasta que se acuerde otra política.
- Datos inválidos no dejan una entidad parcialmente modificada. Si falla unicidad o persistencia no queda una actualización parcial en SQLite.

### Distribución de trabajo

| Componente | Responsabilidad concreta |
|---|---|
| Sede / Socio | Normalización y validación de sus datos, protección de identidad y cambios propios |
| SedeService / SocioService | Registrar, obtener, modificar, listar con límite y cambiar estado. Consultar unicidad, convertir conflictos a errores comprensibles y coordinar transacción |
| SedeRepository / SocioRepository | SQL parametrizado; guardar/recuperar, buscar por nombre/documento normalizado y listar con orden estable |
| Conexión/transacción sqlite3 | Una conexión compartida por el caso de uso, commit al completar y rollback al fallar; repositorios no hacen commits independientes |
| Interfaz futura | Recoger datos, invocar servicio y mostrar resultado/error. No interviene todavía |

No hace falta una fábrica genérica, un repositorio genérico, un framework de inyección ni otro patrón obligatorio. El diagrama en [UML de etapa 0](./UML_ETAPA_0.md) muestra clases y dependencias; el primer módulo ya está implementado y sus verificaciones se registran en el informe de etapa 1.

### Casos de uso detallados del módulo

**CU01 — Sedes:** personal solicita alta con nombre, dirección, contacto y horarios; el servicio crea la entidad válida, comprueba nombre normalizado y guarda. Devuelve su identidad. Modificar repite las validaciones y excluye al registro actual en la comprobación de unicidad. Baja/reactivación recuperan por ID, cambian estado y guardan. Consultas incluyen filtro activa/inactiva y páginas con orden por nombre normalizado e ID.

**CU02 — Socios:** personal registra documento, nombre completo y contacto; el servicio normaliza mediante el dominio, comprueba documento y guarda al socio habilitado. Modificar puede corregir datos sin cambiar identidad. Inhabilitar/habilitar cambia el estado explícitamente. Consultas permiten documento exacto y lista acotada por nombre/ID, con filtro por estado.

El atributo `documento` de CU02 representa exclusivamente DNI en esta versión. Las búsquedas exactas aplican la misma normalización que las altas y modificaciones.

Alternativas de ambos: ID inexistente → error de registro no encontrado; datos inválidos → error de validación; duplicado → conflicto identificable, sin inserción/modificación parcial. La base respalda unicidad aunque otro intento ocurra después de la comprobación del servicio. No se exponen excepciones SQL crudas al usuario final.

### Criterios de aceptación y pruebas previstas

| ID | Dado / cuando | Resultado esperado y nivel |
|---|---|---|
| D01 | Crear sede con datos válidos y reabrir conexión | Mismo ID, datos y estado activo; integración repositorio/servicio |
| D02 | Nombre o dato obligatorio vacío, o modificar con dato inválido | Rechazo sin cambiar datos previos; unidad dominio |
| D03 | Registrar o renombrar a ` centro ` cuando existe `Centro` | Conflicto; una sola sede, también si la anterior está de baja; servicio + UNIQUE |
| D04 | Dar de baja, consultar, reactivar y repetir reactivación | Registro e ID conservados, estados correctos, repetición sin efectos extras; unidad + integración |
| D05 | Crear socio con `12.345.678` y volver a leer | Documento `12345678`, nombre/contacto conservados y habilitado; unidad + integración |
| D06 | Documento con letras, símbolos no permitidos o sólo separadores | Error; no se convierten entradas arbitrarias en documentos válidos; unidad dominio |
| D07 | Crear/editar un socio con documento ya usado | Conflicto aunque el otro esté inhabilitado; sin duplicación ni modificación parcial |
| D08 | Inhabilitar, consultar y habilitar | Conserva identidad y datos; método de habilitación informa el estado correcto |
| D09 | Dos personas con mismo nombre y distinto documento; o editar sin cambiar documento | Permitido, sin falso duplicado; servicio + integración |
| D10 | Consultar o editar un ID inexistente | Error de no encontrado, sin crear registro implícitamente |
| D11 | Listar con tamaño pequeño y orden estable | Páginas acotadas sin repetidos en un conjunto sin cambios; filtros correctos; integración |
| D12 | Falla de escritura o conflicto de unicidad | Rollback; al reabrir, datos anteriores intactos; integración con base temporal |

En etapa 1 se usarán bases temporales de pytest; no se escribirán pruebas sobre bases reales. La pertenencia de ejemplares y el rechazo de nuevas operaciones con sede inactiva se verifican cuando existan esos casos de uso; la etapa 1 sólo almacena y expone el estado.

## 6. Recorridos de escritorio del circuito principal

Los nombres de estados siguientes explican el modelo propuesto; los plazos numéricos se acordarán en cada módulo. El [UML](./UML_ETAPA_0.md) resume relaciones y transiciones.

### L — Préstamo local y devolución

1. Socio habilitado; sede Centro activa; ejemplar E1 pertenece a Centro, está allí, sano y disponible.
2. Crear solicitud con origen Centro y retiro Centro. Asignar E1 lo bloquea para otras solicitudes.
3. Estrategia local verifica que no se necesita traslado. Al entregar, revalidar socio, sede y asignación; crear préstamo y calcular vencimiento desde esa fecha. E1 pasa a PRESTADO y no tiene ubicación física en una sede mientras lo posee el socio.
4. Consultar en una fecha posterior al vencimiento informa atraso; no crea otra deuda ni cambia por sí solo la habilitación.
5. Devolver en Centro registra fecha y condición física y cierra ese préstamo una única vez. Si está sano se evalúan reservas antes de liberarlo; si está dañado queda no disponible. No hay remito local ni de retorno.

Resultado comprobado en el diseño: solicitud y préstamo son diferentes; la fecha de transporte no interviene; las dos devoluciones del mismo préstamo no son válidas.

### I — Préstamo interbibliotecario, devolución y retorno

1. Socio habilitado, Centro y Norte activas. E2 pertenece a Centro, está allí y está disponible. Origen Centro, retiro Norte.
2. Asignar E2 a la solicitud, aplicar estrategia interbibliotecaria y generar remito de ida Centro → Norte con detalle vinculado a esa solicitud. No existe aún préstamo al socio.
3. Remito pasa por Pendiente → Empaquetado → Despachado → En tránsito; cada cambio queda en historial. Desde el despacho E2 deja de estar físicamente en Centro y continúa bloqueado.
4. Recepción conforme ubica E2 en Norte, manteniendo Centro como propietaria. Queda asignado para retiro, no disponible para otra persona. Un daño o faltante impide su entrega.
5. Entregar al socio en Norte revalida las condiciones; recién aquí nace el préstamo y su vencimiento. La regla de pertenencia compara Centro con Centro; la regla de entrega compara ubicación Norte con retiro Norte.
6. El socio devuelve en Norte. Registrar recepción física y cerrar su préstamo. E2 queda pendiente de retorno, bloqueado para nuevos préstamos.
7. Crear otro remito Norte → Centro, de tipo retorno, vinculado al préstamo cerrado. Aquí el origen logístico es Norte: no se aplica la regla de propiedad como si fuese un nuevo préstamo. El retorno no cambia la propietaria.
8. Recibir en Centro, revisar condición física y evaluar reservas antes de liberar. El historial conserva ambos remitos y el préstamo cerrado.

Resultado comprobado en el diseño: recibir una devolución no afirma que el material ya regresó a su propietaria; el viaje de retorno no prolonga el préstamo del socio.

### Rechazos y situaciones límite

| ID | Situación | Resultado esperado |
|---|---|---|
| N1 | Socio inhabilitado al solicitar o al entregar | No iniciar ni entregar préstamo; una solicitud previa no evita revalidar |
| N2 | Ejemplar ya asignado, prestado o en tránsito | No asignar de nuevo; conservar operación original |
| N3 | E2 pertenece a Centro pero se indica Sur como origen del préstamo | Rechazar; cambiar ubicación no cambia la propietaria |
| N4 | Origen o destino de baja al iniciar una operación nueva | Rechazar préstamo/reserva/envío; conservar historial previo |
| N5 | Se intenta entregar en Norte antes de recibir conforme el remito | Rechazar; no crear préstamo ni vencimiento |
| N6 | Se intenta recibir un remito pendiente o cancelarlo ya despachado | State rechaza transición y no cambia estado/ubicación |
| N7 | Remito con un ejemplar conforme y otro faltante | Registrar resultados por detalle; sólo el conforme tiene ubicación de destino; faltante bloqueado y trazable |
| N8 | Ejemplar devuelto dañado | Registrar devolución y cerrar préstamo, pero no liberar para circulación; registrar condición observada |

## 7. State, Strategy y decisiones que se cerrarán más adelante

**State:** conservar el ciclo del diagrama existente. Remito ofrece operaciones como `empaquetar`, `despachar`, `registrar_transito`, `recibir` y `cancelar`; el objeto de estado permite o rechaza cada una. Servicios coordinan efectos sobre ejemplares y persistencia atómica. El estado de un remito no equivale al resultado físico de cada detalle.

**Strategy:** un contrato común procesa las diferencias local/interbibliotecario al aprobar y preparar la solicitud. La estrategia local permite preparar la entrega en origen; la interbibliotecaria exige traslado y recepción antes de entregar. Las estrategias no ejecutan SQL: el servicio materializa los pasos necesarios en una transacción. Sólo se diferenciarán plazos si hay una política real que lo justifique; no se inventa una diferencia de días para mostrar polimorfismo.

Pendientes acotados, a resolver antes de sus etapas:

| Antes de | Política pendiente | Base propuesta |
|---|---|---|
| Etapa 4 | Plazo y cálculo de vencimiento | Días configurados explícitamente, calculados desde entrega; vencido cuando la fecha consultada supera el vencimiento y no está devuelto |
| Etapas 4–5 | Cancelación de solicitud asignada y material no retirado | Liberar sólo si no fue despachado; después coordinar retorno, nunca liberarlo ficticiamente |
| Etapa 5 | Recepción parcial y resolución de incidencias | No agregar ahora estados intermedios sin necesidad; definir cuándo se cierra el remito y cómo registrar recuperación de un faltante sin borrar el hecho original |
| Etapas 5–6 | Operaciones pendientes al dar de baja una sede | Bloquear lo nuevo; permitir registrar hechos físicos de operaciones previas sin ocultarlos. Acordar cómo completar retornos sin eludir el bloqueo de nuevos envíos |
| Etapa 6 | Sede de devolución | Primera versión: sede donde se entregó al socio. Otros puntos de devolución sólo si se acuerdan |
| Etapa 7 | Cola y plazo de retiro | Orden de creación con desempate por ID, duración explícita y asignación atómica; definir alcance de cola por obra/sede |

Estos pendientes no impiden implementar sedes/socios, pero sí impiden dar por terminado el diseño detallado de esos módulos futuros. No se declara acordada ninguna de estas políticas por el mero paso del tiempo.

## 8. Revisión y salida de etapa 0

- Los ocho procesos y las siete validaciones obligatorias tienen caso de uso, responsable y comprobación prevista.
- Se separan propiedad, ubicación, condición física y disponibilidad; la decisión de propiedad fue acordada con el usuario.
- Se recorrieron en el diseño préstamo local e interbibliotecario con devolución y retorno, y los rechazos básicos, sin detectar contradicción con la regla de sede propietaria/origen.
- Se propone identidad local compatible con el UML sin modificar el contrato ni los scripts de Open Library.
- Sedes y socios cuentan con datos, comportamiento, casos de uso, diseño de repositorios y pruebas de aceptación concretas.
- Se autoriza avanzar con sedes y socios: DNI único en la red, horarios informativos y UUID estable. Las políticas de los módulos posteriores se revisarán antes de su implementación.
