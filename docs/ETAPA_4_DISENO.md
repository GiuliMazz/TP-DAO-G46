# Etapa 4 — Solicitudes y préstamos locales: propuesta para revisión

Estado: **diseño, sin implementación ni migración de circulación**. Se revisaron la [consigna completa](./referencias/tema1.pdf), el [análisis inicial](./ETAPA_0_DISENO.md), el [UML inicial](./UML_ETAPA_0.md), el [plan](../PLAN_DESARROLLO.md) y los servicios actuales. Este documento concreta propuestas; no convierte los plazos ni políticas nuevas en acuerdos por defecto.

## 1. Alcance y separación fundamental

En esta etapa: registrar una solicitud local, consultar candidatos, asignar exclusivamente una copia, cancelar antes de entregar, efectuar la entrega y consultar préstamos/vencimientos. La devolución física corresponde a etapa 6; el traslado interbibliotecario y los remitos, a etapa 5. Se conservan sus puntos de extensión, sin simular esos procesos ahora.

**SolicitudPrestamo** registra la intención de un socio de recibir una obra, con sede origen y retiro. Puede estar pendiente sin bloquear ningún ejemplar. **AsignacionEjemplar** registra qué copia queda comprometida exclusivamente. **Prestamo** nace con la entrega efectiva: antes no hay material en poder del socio, préstamo activo ni vencimiento de préstamo.

Local significa origen = retiro; ambos deben coincidir con la propietaria del ejemplar. La ubicación debe coincidir además al asignar y entregar. La propiedad nunca se cambia para hacer pasar una validación.

Una solicitud representa una obra y una copia como máximo en este incremento. No agrupa varios libros. La selección puede usar cualquiera de sus ediciones españolas registradas. No se permite editar socio, obra u origen/retiro después del alta: para corregirlos, cancelar y generar otra solicitud.

## 2. Clases y responsabilidades propuestas

| Clase | Datos principales | Comportamiento propio |
|---|---|---|
| SolicitudPrestamo | UUID, socio_id, obra_id, origen_id, retiro_id, fecha_solicitud, estado; fechas de asignación/entrega/cancelación y motivo de cancelación cuando correspondan | Validar datos y cronología; asignar sólo estando pendiente; marcar entrega sólo asignada; cancelar sólo antes de entrega; conservar el motivo y las fechas originales |
| AsignacionEjemplar | UUID, solicitud_id, ejemplar_id, fecha_asignacion, fecha_liberacion opcional y motivo de liberación | Representar la asociación exclusiva; informar si está activa; liberar sin reescribir su historia |
| Prestamo | UUID, asignacion_id, fecha_entrega, fecha_vencimiento | Proteger fechas; consultar si está vencido a una fecha explícita. En etapa 6 incorporará cierre/devolución única |
| Ejemplar, existente | Situación operativa ampliada con ASIGNADO y PRESTADO, conservando LIBRE y BAJA; condición y ubicación actuales | Asignar si su disponibilidad propia lo permite; entregar desde asignación válida y quitar ubicación de sede; liberar una asignación sin rehabilitar una baja ni reparar condición física |
| Socio / Sede / Obra / Edicion, existentes | Identidades y datos actuales | Conservar comportamientos existentes; los servicios consultan habilitación, actividad y relaciones actuales |

Se propone explicitar **AsignacionEjemplar**, refinando la asociación histórica Solicitud–Ejemplar del UML inicial. Su razón concreta es que la exclusividad debe continuar al pasar de solicitud asignada a préstamo efectivo. Un índice en solicitudes y otro en préstamos, por separado, no garantizan exclusividad entre ambas tablas. No se propone una jerarquía de asignaciones ni un gestor genérico de recursos.

Una solicitud tiene 0..1 asignación histórica en etapa 4, y una asignación pertenece a una sola solicitud. Un ejemplar puede tener muchas asignaciones históricas, pero como máximo una sin liberar. Un préstamo se relaciona con exactamente una asignación, que sólo puede producir un préstamo. Socio, obra, ejemplar y sedes del préstamo se consultan a través de estas relaciones inmutables, sin copiar claves redundantes que puedan contradecirse.

No se permite reasignar una solicitud ya asignada en este incremento: si la copia deja de ser utilizable, cancelar y abrir otra. No se elimina historial.

## 3. Estados, disponibilidad y cancelación

### Solicitud

| Estado actual | Operación | Resultado | Efecto físico/lógico |
|---|---|---|---|
| PENDIENTE | asignar | ASIGNADA | Crear asignación activa y marcar copia ASIGNADO en la misma transacción |
| PENDIENTE | cancelar | CANCELADA | Ninguna copia que liberar |
| ASIGNADA | entregar | ENTREGADA | Crear préstamo, marcar copia PRESTADO y ubicación de sede nula; la asignación sigue activa |
| ASIGNADA | cancelar | CANCELADA | Liberar su asignación y quitar exclusivamente ese bloqueo, atómicamente |
| CANCELADA | cancelar nuevamente | CANCELADA | Devolver el resultado existente; no cambiar motivo/fecha ni tocar la copia |
| ENTREGADA | cancelar | Rechazo | Un préstamo efectivo se resuelve mediante devolución, no cancelando la solicitud |

Los estados terminales no se reabren. Asignar dos veces o entregar dos veces se rechaza sin crear registros nuevos. Los enums y métodos de entidad son suficientes aquí; State queda reservado para el ciclo de remitos que lo justifica.

**Ejemplo crítico:** A asigna E1; se cancela A; B asigna E1; llega otra cancelación de A. El servicio reconoce que A ya está cancelada y no modifica E1 ni la asignación de B. Nunca se libera por código de ejemplar sin comprobar la identidad de la asignación y su solicitud.

Al cancelar, liberar compromiso **no significa afirmar disponibilidad**. Si el ejemplar está dañado, destruido, en sede inactiva o de baja, esas condiciones se conservan. Quitar ASIGNADO puede devolver situación LIBRE, pero la consulta sólo lo ofrece si además es APTO, está en su propietaria activa y no tiene asignación vigente. BAJA nunca se transforma en LIBRE por cancelar.

Una solicitud pendiente no es una reserva: es un trámite administrativo sin prioridad ni promesa de stock. Se propone permitirla aunque no haya una copia disponible, dejando el motivo visible al intentar asignar. No se implementa una cola automática hasta etapa 7.

**Retiro no realizado:** se propone empezar con cancelación explícita, listando fecha de asignación y antigüedad para identificar pendientes. No habrá caducidad automática, un plazo oculto ni tareas en segundo plano que liberen material. La asignación vigente sigue siendo deliberada hasta entregar o cancelar. Si se desea un plazo de retiro, se acordará y diseñará su vencimiento/liberación atómica antes de incorporarlo; no se confundirá con el vencimiento del préstamo.

## 4. Fechas y plazo de préstamo

Propuesta para acordar: **14 días corridos** desde la fecha de entrega, iguales para todos los préstamos de esta versión. La consigna exige controlar vencimientos, pero no fija esa cantidad. No se implementan feriados, multas, renovaciones ni plazos distintos para demostrar Strategy.

- Se trabaja con fechas de negocio (`date`); el adaptador de aplicación obtiene el día local de Argentina y lo pasa explícitamente al caso de uso. Las pruebas proporcionan fechas fijas.
- `fecha_vencimiento = fecha_entrega + plazo_dias`. El día de vencimiento todavía no es atraso: vencido cuando fecha_consulta > fecha_vencimiento y el préstamo sigue abierto.
- Ejemplo: solicitud 10/11, asignación 11/11, entrega 13/11 y plazo 14: vence 27/11; está vencido desde 28/11. La espera y el futuro transporte no consumen días de préstamo.
- No se aceptan fechas de asignación anteriores a solicitud ni entrega anterior a asignación. La interfaz no ofrece editar fechas de hechos ya confirmados ni registrar entregas futuras.
- El plazo debe ser un entero positivo; el vencimiento se guarda al entregar. Cambiar la configuración no modifica préstamos existentes.
- VENCIDO es una condición calculada, no un estado persistido que necesite un proceso nocturno. Al incorporarse devoluciones, un préstamo cerrado deja de contarse como activo/vencido, sin borrar su atraso histórico.

## 5. Servicios, repositorios y transacciones

Se proponen **SolicitudPrestamoService** para solicitar/asignar/cancelar y **PrestamoService** para entregar/consultar vencimientos. La frontera responde a dos momentos de negocio distintos; la regla de disponibilidad propia sigue en Ejemplar. Repositorios específicos de solicitud, asignación y préstamo persistirán y reconstruirán entidades, sin commits propios.

Cada comando usa una única conexión compartida por todos sus repositorios y la transacción existente con **BEGIN IMMEDIATE**. No se llama a otro servicio que abra una transacción anidada. El servicio de circulación coordina directamente los repositorios y los comportamientos de las entidades involucradas.

| Caso de uso | Comprobaciones dentro de la transacción | Escrituras confirmadas juntas |
|---|---|---|
| solicitar(socio, obra, origen, retiro, fecha) | Socio habilitado, obra/edición utilizable, sedes activas, origen=retiro en esta etapa | Solicitud pendiente; no asignación ni préstamo |
| asignar(solicitud, ejemplar, fecha) | Solicitud pendiente; revalidar socio/sedes; copia de la obra, propia de origen, ubicada allí, apta, libre y sin asignación vigente | Solicitud asignada + asignación activa + copia ASIGNADO |
| entregar(solicitud, fecha) | Solicitud asignada; asignación activa exacta; sin préstamo previo; revalidar socio/sedes/condición/propiedad/ubicación y plazo | Solicitud entregada + préstamo/vencimiento + copia PRESTADO sin sede actual; mantener asignación activa |
| cancelar(solicitud, motivo, fecha) | No entregada; motivo no vacío; cronología válida; identificar la asignación de esa solicitud | Solicitud cancelada + liberación exacta + cambio operativo compatible de copia, si había asignación |

Si socio/sede se inhabilitan entre pasos o la copia se daña, la entrega se rechaza sin liberar silenciosamente la asignación. Se mantiene un trámite visible que puede cancelarse. La cancelación se permite aunque el socio o la sede ya estén inactivos: bloquearla dejaría compromisos sin salida.

Fallar cualquier escritura revierte solicitud, asignación, préstamo y ejemplar. Un error de lock se comunica para releer/reintentar conscientemente, sin asumir que hubo entrega. La vista conserva la protección de doble envío; la exclusividad se garantiza también entre conexiones/procesos, no sólo con un botón deshabilitado.

Dos asignaciones de la misma copia: la primera transacción confirma; la segunda relee y se rechaza. Entrega y cancelación simultáneas: si gana cancelación no se crea préstamo; si gana entrega, cancelar se rechaza. No existe un intervalo entre liberar la solicitud y adquirir el préstamo porque la asignación no se libera al entregar.

## 6. Persistencia prevista y efecto sobre inventario

Se propone una migración posterior al esquema 6, **todavía no escrita**, con tablas solicitud_prestamo, asignacion_ejemplar y prestamo. Restricciones previstas:

- UUID y claves foráneas; solicitud_id único en asignación; asignacion_id único en préstamo.
- Índice UNIQUE parcial por ejemplar en asignaciones no liberadas: una misma copia no puede respaldar dos compromisos vigentes, aunque las solicitudes hayan pasado a entregadas.
- CHECK de estados, fechas y coherencia de liberación; índices de listados por estado/socio/sede y orden estable. Las reglas entre entidades se revalidan en el servicio dentro de la transacción.
- Cambio operativo del ejemplar con condición de estado anterior y verificación de la fila afectada, además de la validación del dominio.
- Disponibilidad del catálogo/inventario exige ausencia de asignación activa, además de las condiciones actuales. Se revisarán **todas** las consultas y las pruebas de volumen para no mostrar una copia comprometida como libre.

El CHECK actual de ejemplar sólo permite LIBRE/BAJA: deberá migrarse explícitamente para ASIGNADO/PRESTADO. La preparación será una herramienta fuera del arranque Flet, conservando UUID, códigos, relaciones, bajas, condición y ubicación; se probará desde una base de esquema 6 con datos. No se cambia el contrato bibliográfico ni se reconstruyen las obras.

**Interacción con el mantenimiento recién completado:** hoy sólo existen LIBRE/BAJA y se respetó ese backend. Antes de activar circulación se deberá impedir una baja administrativa con asignación activa o préstamo vigente: primero cancelar la solicitud o registrar devolución según el caso. Cambiar condición sí puede registrar daño de material asignado y bloquear la entrega, sin borrar el compromiso. No se implementará una cancelación oculta dentro de InventarioService. Esta ampliación de reglas se implementará y probará junto con circulación, no anticipadamente en esta entrega.

## 7. Strategy e interbibliotecarios

Se conserva el compromiso académico de Strategy para local/interbibliotecario. **No se crean ahora interfaz abstracta, clases vacías ni una estrategia que sólo devuelva un booleano.** En la etapa 4 habrá reglas locales explícitas y pequeñas; cuando la etapa 5 incorpore preparación de traslado y validación de recepción conforme, se extraerá un contrato a partir de ambos comportamientos reales.

El servicio conservará validaciones comunes y transacciones. Las futuras estrategias decidirán preparación/condiciones de entrega según modalidad, sin SQL ni commits. Remito delegará sus transiciones en State. Solicitud y préstamo seguirán separados: recepción en otra sede no crea automáticamente el préstamo ni libera su asignación. Cancelar después de despacho exige logística/retorno; no se reutilizará la liberación local como si el material ya estuviera físicamente en origen.

Esta decisión actualiza la previsión del plan inicial, que sugería introducir el contrato Strategy ya en etapa 4. Se posterga esa implementación según la indicación del usuario, conservando su aplicación prevista en etapa 5.

## 8. Incrementos propuestos después de aprobar el diseño

| Incremento | Alcance | Criterios de aceptación |
|---|---|---|
| 4A | Entidades, estados y fechas | Transiciones válidas/prohibidas, cronología, vencimiento desde entrega y límites de fecha; sin SQL ni Flet |
| 4B | Migración, repositorios, solicitud/asignación/cancelación y compatibilidad de inventario | Preservar datos previos; exclusividad con dos conexiones; cancelación repetida de A no libera B; rollback de cada paso; daño/inactividad/baja no se reactivan |
| 4C | Entrega y consulta de préstamos | Revalidaciones, un préstamo por solicitud, entrega repetida, cancelación contra entrega concurrente, rollback y vencimiento persistido |
| 4D | Pantallas reales incrementales | Solicitudes separadas de préstamos efectivos, candidatos por disponibilidad, confirmar entrega/cancelación, errores y refresco no bloqueantes; recorrido completo en demo |

Las pruebas anteriores se conservan. Casos esenciales adicionales: pendiente sin bloqueo; asignado fuera de disponibilidad; cancelar pendiente; cancelar asignada; cancelar con socio/sede inactivos; cancelación de entregada rechazada; copia dañada antes de entrega; origen/ubicación incorrectos; propietario distinto; dos intentos exclusivos; fecha exactamente igual a vencimiento y día posterior; cambio de plazo sin alterar préstamos previos; fallo entre escrituras sin asignaciones huérfanas.

## 9. Decisiones para revisar antes de implementar

1. Validar la asociación explícita AsignacionEjemplar y su continuidad al entregar.
2. Acordar plazo de préstamo: se proponen 14 días corridos.
3. Confirmar retiro con cancelación manual inicial, sin caducidad automática ni cola de reservas anticipada.
4. Validar que no se reasigna una solicitud: cancelar y crear otra mantiene un flujo menor y un historial claro.

[UML y secuencias propuestas](./UML_ETAPA_4.md). Nada de este diseño se considera implementado por haberlo documentado.
