# Incremento 2B — Ejemplares y disponibilidad

Fecha: 3 de noviembre de 2026. Estado: implementado y verificado; circulación y logística permanecen pendientes.

## Funcionalidad entregada

- Alta explícita de copias de una edición existente en una sede activa.
- Código de inventario normalizado y único en toda la red, incluso si el registro anterior está de baja; UUID estable independiente del código.
- Obtención por UUID y búsqueda por código; listados paginados por obra, edición, propietaria, ubicación, condición, situación y disponibilidad.
- Registro de condición física y baja lógica, sin borrar la copia ni reactivar automáticamente material retirado.
- Resumen por obra y sede con totales de propiedad, ubicación registrada, bajas y disponibilidad; incluye sedes sin copias con cantidades cero.

La copia inicial queda ubicada en su propietaria. No se crea inventario al registrar metadatos bibliográficos. Tampoco se ofrece una operación libre para cambiar edición, código, propietaria o ubicación.

## Clases y responsabilidades

| Componente | Responsabilidad |
|---|---|
| [Ejemplar](../biblioteca/dominio/ejemplar.py) | Identidad, referencias de edición/sedes, condición y situación. Comportamiento de disponibilidad propia, condición y baja. |
| CondicionFisica | APTO, DANIADO, DESTRUIDO. Una destrucción no se revierte mediante una corrección ordinaria a APTO/DANIADO. |
| SituacionOperativa | LIBRE o BAJA en este incremento. LIBRE significa sin asignación, no necesariamente apto para circular. |
| [InventarioService](../biblioteca/servicios/inventario_service.py) | Comprobar referencias, sede activa y obra utilizable al dar de alta; coordinar transacciones, consultas y errores. |
| [EjemplarRepository](../biblioteca/repositorios/ejemplar_repository.py) | SQL parametrizado, restricciones de identidad al actualizar, reconstrucción y agregación sin commits propios. |
| [DisponibilidadSede](../biblioteca/resultados_inventario.py) | Resultado de consulta por obra/sede, sin cargar todas las copias como objetos. |

Todos los repositorios del servicio comparten conexión. Las escrituras se confirman o revierten juntas. No se agregaron dependencias, jerarquías genéricas ni otro patrón de diseño.

El código admite caracteres imprimibles sin espacios internos y se normaliza a mayúsculas, conservando ceros. No incorpora obligatoriamente sede ni ISBN y no se calcula contando filas. Los datos leídos conservan una ubicación nula si estaba registrada así: no se reemplaza por una presencia física inventada en la propietaria. El alta pública sí exige y fija una sede inicial conocida.

## Disponibilidad y propiedad

La disponibilidad propia del objeto exige LIBRE, APTO y ubicación en la propietaria. El servicio/listado añade sede activa y obra/edición utilizables. Una copia localmente apta puede seguir existiendo como tal en una sede dada de baja, pero no se ofrece como disponible en las consultas de la red.

El resumen distingue:

| Campo | Significado |
|---|---|
| total_propios | Copias registradas a nombre de la sede, incluidas bajas, sin depender de su ubicación |
| total_ubicados | Copias cuya ubicación registrada es esa sede, incluidas bajas; no equivale a cantidad prestable |
| bajas_ubicadas | Parte de total_ubicados con situación BAJA |
| disponibles | Copias que superan las condiciones de disponibilidad para nueva asignación |

Las cantidades se agregan por copia y edición sin unir filas de autoría; varias ediciones/autores no multiplican los totales.

Se verificó con datos de prueba una copia de Centro ubicada temporalmente en Norte: conserva propietaria Centro y no se ofrece para una nueva solicitud. Esa ubicación se simuló por SQL dentro de la prueba; no es una funcionalidad de traslado entregada en 2B. La asignación a la solicitud original y la entrega al socio se implementarán con circulación: no deben confundirse con la disponibilidad para otra solicitud.

Cambiar condición a APTO no quita BAJA. La baja es idempotente y conserva el código para impedir su reutilización. Las correcciones de condición y bajas pueden registrarse aunque la sede esté inactiva; no son nuevos préstamos, reservas o envíos.

## Persistencia y migración

La [migración 003](../biblioteca/persistencia/migraciones/003_inventario.sql) agrega ejemplar, código único, claves foráneas a edición/sedes, estados permitidos e índices por edición, propiedad y ubicación. La versión operativa vigente es 3.

Las migraciones 001/002 permanecen intactas. La actualización 2 → 3 se probó sobre una base construida realmente con esas dos versiones, con sedes, socios, autores, obra, autoría y edición preferida ya registrados. Se conservaron todos sus campos y vínculos. Un fallo de la tercera migración revierte el DDL y conserva versión 2 y sus datos; reintentar completa versión 3.

Las pruebas de catálogo se adaptaron para comprobar que el registro bibliográfico deja la tabla de ejemplares vacía, en vez de exigir que esa tabla todavía no exista. Las pruebas históricas de migración desde versión 1 siguen comprobando conservación hasta la versión vigente.

## Verificación ejecutada

Entorno existente: Python 3.14.8, SQLite 3.51.2 y pytest 9.2.0. No hubo instalaciones nuevas.

```bash
python -m pytest -q
```

Resultado: **226 passed in 0.54s**, código 0; 64 casos más que al terminar 2A, incluyendo cuatro regresiones de paginación de catálogo. Los conteos incluyen parametrizaciones.

| Archivo | Casos principales |
|---|---|
| [test_ejemplar.py](../tests/test_ejemplar.py) | Código, disponibilidad por condición/situación/ubicación, propiedad e identidad sólo lectura, baja y destrucción |
| [test_inventario.py](../tests/test_inventario.py) | Altas y relectura, códigos únicos, FK, sede inactiva, conteos sin multiplicar por autores, páginas filtradas, ubicación nula/temporal, rollback y altas concurrentes |
| [test_migraciones_inventario.py](../tests/test_migraciones_inventario.py) | Base versión 2 con datos → versión 3, repetición, integridad y fallo recuperable |
| [test_catalogo.py](../tests/test_catalogo.py) | Páginas con varias ediciones/autores y registro bibliográfico sin creación automática de copias |

La primera ejecución focalizada detectó una regresión: en la consulta con varias filas de autoría y OFFSET, la segunda página repetía la primera copia disponible. Se aisló el SQL y sus parámetros en el depurador y se verificó que consultar pertenencia al conjunto de obras con autoría devolvía la copia correcta. Se corrigió esa consulta, manteniendo el filtro antes de LIMIT/OFFSET. También se verificaron páginas de catálogo con varios autores y ediciones. No se atribuye el comportamiento a una causa interna del motor sin más evidencia.

Las tres demostraciones terminaron con código 0:

```bash
python -m biblioteca.demo
python -m biblioteca.demo_catalogo
python -m biblioteca.demo_inventario
```

La nueva [demostración de inventario](../biblioteca/demo_inventario.py) produjo:

```text
Centro: propios=2, ubicados=2, bajas=0, disponibles=1
Norte: propios=2, ubicados=2, bajas=1, disponibles=1
Sur: propios=0, ubicados=0, bajas=0, disponibles=0
```

Rechazó código duplicado, ofreció cero disponibles al dar de baja Centro y conservó UUID/propietaria y el registro retirado al reabrir. Todos los datos son ficticios y la base temporal se elimina al terminar. El editor no informó problemas en el código/pruebas consultados.

## Límites del incremento

Se cubren el inventario de RF03, la consulta de RF06 y unicidad de ejemplares de RN05, a nivel de dominio/servicios/repositorios. No hay interfaz Flet todavía ni se puede prestar, reservar o trasladar desde estos métodos.

No se implementaron asignaciones, préstamos, remitos, retornos ni sus nuevos estados; tampoco se afirma rendimiento medido con 100.000 obras. El contrato y los datos del importador no se modificaron. El próximo incremento es 2C: vocabularios, clasificación trazable y público destinatario separado, según el diseño acordado.
