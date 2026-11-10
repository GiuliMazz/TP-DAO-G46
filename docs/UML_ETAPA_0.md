# UML inicial — Etapa 0

Estos diagramas Mermaid expresan el diseño del [análisis de etapa 0](./ETAPA_0_DISENO.md). Se pueden visualizar en un visor compatible con Mermaid. Sedes y socios ya están implementados según este modelo; las relaciones generales y los patrones corresponden a etapas futuras. Los [DOT originales](../archivo/diagramas) se conservan como referencia histórica.

## 1. Dominio del primer módulo

`UUID` es identidad local estable; los atributos se exponen para consulta, pero las modificaciones deben pasar por operaciones que preserven invariantes. Los parámetros agrupados en `datos` representan los campos indicados en cada clase, no una nueva clase obligatoria.

Decisiones del primer módulo: `horarios` se conserva como texto informativo para cubrir la consigna. `documento` representa DNI argentino normalizado y único en toda la red; no hay tipo de documento ni país emisor. Red de Bibliotecas Horizonte es el nombre general de la aplicación; no es atributo de Sede. Norte, Centro y Sur son datos de demostración.

```mermaid
classDiagram
    direction LR
    class Sede {
        -UUID id
        -str nombre
        -str direccion
        -str contacto
        -str horarios
        -bool activa
        +actualizar_datos(nombre, direccion, contacto, horarios)
        +activar()
        +dar_de_baja()
        +esta_activa() bool
    }
    class Socio {
        -UUID id
        -str documento
        -str nombre_completo
        -str contacto
        -EstadoSocio estado
        +actualizar_datos(documento, nombre_completo, contacto)
        +habilitar()
        +inhabilitar()
        +esta_habilitado() bool
    }
    class EstadoSocio {
        <<enumeration>>
        HABILITADO
        INHABILITADO
    }
    Socio --> EstadoSocio : estado
```

No se agrega asociación Socio–Sede: el registro de socios es de toda la red. Ambas entidades validan datos al construirse y antes de aplicar una modificación completa. Las transiciones simples no requieren clases State.

## 2. Servicios y persistencia del primer módulo

Las dependencias indican uso, no herencia. Los repositorios son clases concretas específicas; no se requiere una jerarquía genérica. La interfaz gráfica se muestra sólo como consumidor futuro.

```mermaid
classDiagram
    direction TB
    class InterfazFutura {
        <<Flet>>
    }
    class SedeService {
        +registrar(datos) Sede
        +obtener(id) Sede
        +modificar(id, datos) Sede
        +dar_de_baja(id)
        +activar(id)
        +listar(activa, nombre, limite, desplazamiento)
    }
    class SocioService {
        +registrar(datos) Socio
        +obtener(id) Socio
        +buscar_por_documento(documento) Socio
        +modificar(id, datos) Socio
        +inhabilitar(id)
        +habilitar(id)
        +listar(estado, nombre, limite, desplazamiento)
    }
    class SedeRepository {
        +agregar(sede)
        +actualizar(sede)
        +obtener(id) Sede
        +buscar_por_nombre_normalizado(nombre)
        +listar(activa, nombre, limite, desplazamiento)
    }
    class SocioRepository {
        +agregar(socio)
        +actualizar(socio)
        +obtener(id) Socio
        +buscar_por_documento(documento)
        +listar(estado, nombre, limite, desplazamiento)
    }
    class ConexionSQLite {
        <<sqlite3.Connection>>
    }
    InterfazFutura ..> SedeService
    InterfazFutura ..> SocioService
    SedeService ..> Sede : coordina comportamiento
    SocioService ..> Socio : coordina comportamiento
    SedeService --> SedeRepository
    SocioService --> SocioRepository
    SedeRepository --> ConexionSQLite
    SocioRepository --> ConexionSQLite
    SedeService ..> ConexionSQLite : delimita transaccion
    SocioService ..> ConexionSQLite : delimita transaccion
```

Las operaciones de escritura delimitan su transacción en el servicio usando una conexión compartida por sus repositorios. El servicio no contiene SQL; el repositorio no confirma transacciones independientemente. Si más adelante un caso necesita varios repositorios, usa la misma conexión. El ensamblado de dependencias se hará en el punto de entrada, sin un framework adicional.

La búsqueda de Socio por documento puede devolver ausencia cuando no hay coincidencia; obtener por ID desde un servicio informa registro no encontrado. Los repositorios devuelven ausencia al obtener un ID inexistente y no hacen inserciones implícitas al actualizarlo.

## 3. Relaciones del dominio completo

Vista de relaciones para orientar los incrementos posteriores; los métodos se detallan al preparar cada módulo. Cada asociación histórica permite muchas operaciones a lo largo del tiempo, pero no varias asignaciones activas incompatibles del mismo ejemplar.

```mermaid
classDiagram
    direction TB
    Obra "1" -- "0..*" Edicion : publicaciones
    Obra "0..*" -- "1..*" Autor : autores
    Obra "1" -- "0..*" ObraGenero
    Genero "1" -- "0..*" ObraGenero
    Obra "1" -- "0..*" ObraEtiqueta
    Etiqueta "1" -- "0..*" ObraEtiqueta
    Edicion "1" -- "0..*" Ejemplar : copias
    Sede "1" -- "0..*" Ejemplar : propietaria
    Sede "0..1" -- "0..*" Ejemplar : ubicacion fisica
    Socio "1" -- "0..*" SolicitudPrestamo : solicita
    Obra "1" -- "0..*" SolicitudPrestamo
    Sede "1" -- "0..*" SolicitudPrestamo : origen
    Sede "1" -- "0..*" SolicitudPrestamo : retiro
    Ejemplar "0..1" -- "0..*" SolicitudPrestamo : asignacion historica
    SolicitudPrestamo "1" -- "0..1" Prestamo : entrega efectiva
    Socio "1" -- "0..*" Prestamo
    Ejemplar "1" -- "0..*" Prestamo
    Prestamo "1" -- "0..1" Devolucion
    Sede "1" -- "0..*" Devolucion : recepcion
    Socio "1" -- "0..*" Reserva
    Obra "1" -- "0..*" Reserva
    Sede "1" -- "0..*" Reserva : retiro
    Ejemplar "0..1" -- "0..*" Reserva : asignacion historica
    Reserva "0..1" -- "0..1" SolicitudPrestamo : atencion
    Sede "1" -- "0..*" Remito : origen logistico
    Sede "1" -- "0..*" Remito : destino logistico
    Remito "1" *-- "1..*" DetalleRemito
    Ejemplar "1" -- "0..*" DetalleRemito
    SolicitudPrestamo "0..1" -- "0..*" DetalleRemito : ida
    Prestamo "0..1" -- "0..*" DetalleRemito : retorno
    Remito "1" *-- "1..*" EventoRemito
    DetalleRemito "1" *-- "0..1" RevisionRecepcion
    Socio "1" -- "0..*" RegistroLectura
    Obra "1" -- "0..*" RegistroLectura
    Prestamo "0..1" -- "0..1" RegistroLectura : referencia opcional
```

- Obra–Edicion permite cero ediciones en un borrador; la política de catálogo importado publicado exige al menos una edición elegible. La vista muestra obras con autor identificado; registros incompletos del staging no se publican como si cumplieran esta condición.
- ObraGenero y ObraEtiqueta tienen estado de clasificación, procedencia y revisión; no son asociaciones sin atributos.
- Propuesta revisada: el estado de preparación/validación de una edición pertenece a los registros técnicos de importación. Edicion conserva sus datos y validaciones bibliográficas propias; no modela las fases del pipeline como estados de circulación.
- Cada ejemplar conserva una propietaria. La ubicación de sede puede faltar si lo tiene un socio, está en tránsito o no está localizado; su situación operativa conserva el motivo.
- La multiplicidad de solicitudes/reservas por ejemplar es histórica; nunca habilita dos asignaciones activas simultáneas. La reserva atendida y su solicitud deben compartir la misma asignación, no competir por ella.
- Un detalle corresponde a una ida con solicitud o a un retorno con préstamo, no a ambos. Un remito agrupa un único origen, destino y tipo.
- La composición de eventos expresa dependencia de su remito, no autorización para borrar el historial en cascada desde la interfaz.
- La revisión mostrada es la evaluación de recepción inicial; el diseño de recuperación/corrección de incidencias se cerrará antes de etapa 5 sin sobrescribir la evidencia original.

## 4. Ciclo base del remito

Se conserva el [ciclo de referencia](../archivo/diagramas/06_estados_remito.dot). Las transiciones no dibujadas están prohibidas. Cancelación libera sólo las asignaciones que corresponda antes del despacho; no inventa una devolución física.

```mermaid
stateDiagram-v2
    [*] --> Pendiente : crear con detalle e historial inicial
    Pendiente --> Empaquetado : empaquetar
    Empaquetado --> Despachado : despachar
    Despachado --> EnTransito : registrar_transito
    EnTransito --> Recibido : cierre conforme
    EnTransito --> ConIncidencias : cierre con resultados por item
    Pendiente --> Cancelado : cancelar
    Empaquetado --> Cancelado : cancelar
```

El instante de despacho marca la salida física; registrar tránsito añade el hito de seguimiento. Recibido y Cancelado cierran ese recorrido; el tratamiento posterior de ConIncidencias se especificará antes de implementar logística. Un remito de retorno es otra instancia que recorre el mismo ciclo, no una transición del remito de ida.

## 5. Aplicación de los patrones

```mermaid
classDiagram
    direction LR
    class EstadoRemito {
        <<abstract>>
        +empaquetar(remito)
        +despachar(remito)
        +registrar_transito(remito)
        +recibir(remito, resultados)
        +cancelar(remito)
    }
    Remito "1" --> "1" EstadoRemito : estado actual
    EstadoRemito <|-- Pendiente
    EstadoRemito <|-- Empaquetado
    EstadoRemito <|-- Despachado
    EstadoRemito <|-- EnTransito
    EstadoRemito <|-- Recibido
    EstadoRemito <|-- ConIncidencias
    EstadoRemito <|-- Cancelado
    class EstrategiaPrestamo {
        <<abstract>>
        +validar_solicitud(solicitud, ejemplar)
        +requiere_traslado() bool
        +validar_entrega(solicitud, ejemplar)
    }
    PrestamoService --> EstrategiaPrestamo : selecciona segun tipo
    EstrategiaPrestamo <|-- EstrategiaPrestamoLocal
    EstrategiaPrestamo <|-- EstrategiaPrestamoInterbibliotecario
```

El contrato exacto de Strategy se revisará al implementar circulación: la diferencia es validación/preparación local frente a traslado con recepción, no sólo retornar un indicador. Las reglas comunes no se duplican innecesariamente en las dos variantes. No se agregan estrategias para recomendaciones por el solo hecho de contar patrones.
