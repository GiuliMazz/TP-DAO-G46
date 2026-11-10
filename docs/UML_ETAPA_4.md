# UML propuesto — Etapa 4, sin implementación

Complementa el [diseño para revisión](./ETAPA_4_DISENO.md). Las clases de circulación y sus métodos son propuestas; Sede, Socio, Obra, Edicion y Ejemplar ya existen, pero los métodos de circulación de Ejemplar aún no. Se omiten atributos bibliográficos para centrar el análisis.

## Clases y relaciones

```mermaid
classDiagram
    direction TB
    class SolicitudPrestamo {
        -UUID id
        -UUID socio_id
        -UUID obra_id
        -UUID origen_id
        -UUID retiro_id
        -date fecha_solicitud
        -EstadoSolicitud estado
        -date fecha_cancelacion
        -str motivo_cancelacion
        +asignar(asignacion, fecha)
        +marcar_entregada(fecha)
        +cancelar(motivo, fecha)
    }
    class AsignacionEjemplar {
        -UUID id
        -UUID solicitud_id
        -UUID ejemplar_id
        -date fecha_asignacion
        -date fecha_liberacion
        -str motivo_liberacion
        +esta_activa() bool
        +liberar(fecha, motivo)
    }
    class Prestamo {
        -UUID id
        -UUID asignacion_id
        -date fecha_entrega
        -date fecha_vencimiento
        +esta_vencido(fecha_consulta) bool
    }
    class Ejemplar {
        -UUID id
        -UUID edicion_id
        -UUID sede_propietaria_id
        -UUID sede_actual_id
        -CondicionFisica condicion_fisica
        -SituacionOperativa situacion_operativa
        +esta_disponible() bool
        +asignar()
        +entregar_a_socio()
        +liberar_asignacion()
    }
    class EstadoSolicitud {
        <<enumeration>>
        PENDIENTE
        ASIGNADA
        ENTREGADA
        CANCELADA
    }
    class SolicitudPrestamoService {
        +solicitar(socio, obra, origen, retiro, fecha)
        +asignar(solicitud, ejemplar, fecha)
        +cancelar(solicitud, motivo, fecha)
        +consultar_candidatos(solicitud, pagina)
    }
    class PrestamoService {
        +entregar(solicitud, fecha)
        +obtener(id)
        +listar(filtros, pagina)
    }
    Socio "1" -- "0..*" SolicitudPrestamo : titular
    Obra "1" -- "0..*" SolicitudPrestamo : solicitada
    Sede "1" -- "0..*" SolicitudPrestamo : origen
    Sede "1" -- "0..*" SolicitudPrestamo : retiro
    SolicitudPrestamo --> EstadoSolicitud
    SolicitudPrestamo "1" -- "0..1" AsignacionEjemplar : compromiso
    Ejemplar "1" -- "0..*" AsignacionEjemplar : historial
    AsignacionEjemplar "1" -- "0..1" Prestamo : entrega efectiva
    Obra "1" -- "0..*" Edicion
    Edicion "1" -- "0..*" Ejemplar
    Sede "1" -- "0..*" Ejemplar : propietaria
    Sede "0..1" -- "0..*" Ejemplar : ubicacion
    SolicitudPrestamoService ..> SolicitudPrestamo
    SolicitudPrestamoService ..> AsignacionEjemplar
    SolicitudPrestamoService ..> Ejemplar
    PrestamoService ..> SolicitudPrestamo
    PrestamoService ..> AsignacionEjemplar
    PrestamoService ..> Prestamo
    PrestamoService ..> Ejemplar
```

La cardinalidad histórica Ejemplar–AsignacionEjemplar no permite varias activas: se garantiza una sola asignación no liberada por ejemplar mediante restricción y transacción. Como cada solicitud tiene una asignación como máximo y cada asignación un préstamo como máximo, una solicitud no puede producir dos préstamos. La entrega no libera la asignación.

Fechas opcionales se informan sólo al ocurrir el hecho correspondiente; no se rellenan con fechas ficticias. Los repositorios específicos, omitidos del diagrama para legibilidad, comparten la conexión del servicio y no confirman escrituras por separado.

## Solicitud y situación física

```mermaid
stateDiagram-v2
    [*] --> PENDIENTE : solicitar
    PENDIENTE --> ASIGNADA : asignar copia exclusiva
    PENDIENTE --> CANCELADA : cancelar sin copia
    ASIGNADA --> ENTREGADA : entregar y crear prestamo
    ASIGNADA --> CANCELADA : cancelar y liberar su asignacion
    CANCELADA --> CANCELADA : repetir cancelacion sin efectos
    ENTREGADA --> [*]
```

ENTREGADA finaliza la solicitud, no el préstamo. En etapa 4 un préstamo efectivo permanece activo hasta incorporar devolución en etapa 6. Vencido es una consulta por fecha sobre el préstamo abierto, no otro estado de solicitud.

```mermaid
stateDiagram-v2
    LIBRE --> ASIGNADO : asignacion valida
    ASIGNADO --> PRESTADO : entrega efectiva
    ASIGNADO --> LIBRE : cancelacion compatible
    LIBRE --> BAJA : baja administrativa
```

Diagrama limitado a circulación local prevista. Condición física es independiente: LIBRE + DANIADO no significa disponible. Si ya existe una baja, cancelar no la revierte. PRESTADO carece de ubicación de sede; la propietaria permanece. Devoluciones y logística ampliarán este diagrama en sus etapas, sin trasladar propiedad.

## Entrega atómica

```mermaid
sequenceDiagram
    actor Personal
    participant Vista as Vista Flet
    participant Servicio as PrestamoService
    participant BD as Repositorios / SQLite
    participant Dominio as Entidades
    Personal->>Vista: Confirmar entrega
    Vista->>Servicio: entregar(solicitud_id, fecha)
    Servicio->>BD: BEGIN IMMEDIATE y recuperar datos actuales
    Servicio->>Dominio: Validar solicitud, asignacion, socio, sedes y ejemplar
    alt Hay una condicion invalida
        Servicio->>BD: ROLLBACK
        Servicio-->>Vista: Error sin cambios
    else Entrega permitida
        Servicio->>Dominio: Crear Prestamo y calcular vencimiento desde entrega
        Servicio->>Dominio: Marcar solicitud ENTREGADA y ejemplar PRESTADO
        Servicio->>BD: Guardar los tres, conservando asignacion activa
        alt Falla alguna escritura
            Servicio->>BD: ROLLBACK de todo
            Servicio-->>Vista: Error sin entrega confirmada
        else Todo correcto
            Servicio->>BD: COMMIT
            Servicio-->>Vista: Prestamo confirmado
            Vista-->>Personal: Mostrar vencimiento y releer disponibilidad
        end
    end
```

## Cancelación sin liberar una asignación ajena

```mermaid
flowchart TD
    A[Cancelar solicitud por ID] --> B[BEGIN IMMEDIATE y releer solicitud]
    B --> C{Estado actual}
    C -->|CANCELADA| D[Devolver cancelacion original sin tocar ejemplar]
    C -->|ENTREGADA| E[Rechazar: corresponde devolucion]
    C -->|PENDIENTE| F[Cancelar sin liberar copias]
    C -->|ASIGNADA| G[Recuperar su asignacion exacta y ejemplar]
    G --> H[Validar relacion y liberar ese compromiso]
    H --> I[Quitar ASIGNADO sin modificar condicion, propietaria ni ubicacion]
    I --> J[Conservar BAJA si corresponde; nunca reactivar]
    J --> K[Guardar solicitud, asignacion y ejemplar juntos]
    F --> L[COMMIT]
    D --> L
    K --> L
    E --> M[ROLLBACK]
```

Cualquier fallo de validación/persistencia también revierte todo. Las futuras estrategias local/interbibliotecaria se extraerán al tener comportamientos reales de ambas variantes; por ahora no se agregan clases del patrón al modelo implementado.
