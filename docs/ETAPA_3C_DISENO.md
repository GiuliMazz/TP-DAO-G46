# Etapa 3C — Administración conectada

Actualización posterior: el usuario solicitó completar también condición física y baja de ejemplares en la interfaz. Ese complemento reutiliza los servicios ya existentes y está verificado en [3C.1](./ETAPA_3C_1_RESULTADOS.md). El alcance inicial descrito abajo se conserva como antecedente.

Se reutilizan las entidades, servicios y repositorios de las etapas 1 y 2. No cambia el esquema 6, el contrato Open Library, las 100 obras ni la separación entre propiedad y ubicación.

## Incrementos y responsabilidades

1. **Socios:** listado paginado de toda la red, búsqueda por nombre/DNI/contacto antes de paginar, alta, edición y habilitación/inhabilitación. `Socio` normaliza y valida los datos; `SocioService` controla la unicidad y la transacción; `SocioRepository` consulta SQLite. La presentación no vuelve a implementar estas reglas.
2. **Sedes:** listado por nombre/estado, alta, edición, baja lógica y reactivación mediante `SedeService`. Se conserva `horarios`, ya presente como información descriptiva en el modelo revisado. Tras guardar se actualizan nombres y sedes activas del encabezado; se mantiene el UUID seleccionado si sigue activo. El filtro del catálogo conserva su alcance independiente.
3. **Ejemplares:** desde una obra se consulta su inventario y se registra explícitamente un código, una edición y una sede activa mediante `InventarioService`. El alta fija inicialmente propietaria y ubicación en esa sede. No se ofrece trasladar ni transferir propiedad. Condición física y baja continúan disponibles en backend; esta entrega prioriza el alta comprometida en 3C.
4. **Demo:** herramienta separada y explícita para incorporar ocho socios ficticios mediante `SocioService`. Una marca por UUID estable permite repetir sin duplicar ni restablecer cambios humanos; rechaza conflictos. Nunca se ejecuta al iniciar Flet ni sobre una base operativa o sintética.

## Acceso local y concurrencia

`AdministracionLocal` compone servicios/repositorios con una conexión propia por operación. Las lecturas usan `mode=ro`; los guardados `mode=rw`, comprobando marca y esquema, sin crear/migrar. Sólo OPERATIVA y DEMOSTRACION admiten administración; RENDIMIENTO sigue siendo consulta.

El lector existente agrega destinos acotados para los tres listados. Las lecturas mantienen debounce, revisión de solicitudes y descarte de respuestas obsoletas. Un escritor separado admite **un solo comando en curso**, sin cola reemplazable ni reintentos automáticos. Cancelar la espera o desconectar no cancela el comando aceptado; la reconexión espera su finalización antes de releer. Un formulario bloquea dobles envíos y conserva campos al fallar. Se comunica éxito una vez confirmado, antes del refresco: un fallo posterior de lectura no ofrece repetir el alta.

Las vistas sólo capturan datos y presentan resultados. Una base ausente no habilita formularios; no se crean datos ficticios por navegación. Los formularios y tablas respetan ambos temas y el desplazamiento en ventanas pequeñas.

## Criterios de verificación

- Persistencia al reabrir; DNI/código/nombre duplicados y campos inválidos sin cambios parciales.
- Búsqueda de socios con OR antes de LIMIT; estados y paginación sin unir páginas en Flet.
- Un comando en vuelo, doble clic, cancelación y desconexión; errores recuperables y respuestas antiguas descartadas.
- Sede inactiva rechazada al registrar copia; encabezado conserva identidad tras renombrar y cambia si queda inactiva.
- Alta física refresca disponibilidad; otros ejemplares y metadatos no se alteran.
- Base inexistente, incompatible o de rendimiento rechazada sin creación/modificación.
- Semilla demo repetible, conserva cambios manuales, rechaza otra base y colisiones.
- Recorrido Flet sobre una copia temporal de demo; suite de regresión completa al cerrar.
