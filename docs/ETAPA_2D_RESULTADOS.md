# Incremento 2D — Open Library conectado al backend

Fecha: 3 de noviembre de 2026. Estado: implementado y verificado. Suite completa: **340 pruebas aprobadas**, con 66 casos nuevos de validación, fuente, integración y migración. Se concretó el [diseño previo](./ETAPA_2D_DISENO.md) y se actualizó el [UML](./UML_ETAPA_2.md).

## Resultado efectivo

Se procesaron offline las 1.000 candidatas de la base de referencia y los 30 JSON originales disponibles, haciendo correspondencia por ID exacto de edición y obra:

| Resultado en la base de destino | Cantidad |
|---|---:|
| Ediciones evaluadas | 1.000 |
| VALIDADA automáticamente e integrada | 5 |
| ENRIQUECIDA, pendiente de revisión bibliográfica | 2 |
| PENDIENTE de detalle/controles | 993 |
| RECHAZADA | 0 |
| Obras distintas integradas | 5 |
| Ejemplares creados | 0 |

Las cinco ediciones incorporadas son Choque de reyes, El ladrón del rayo, La Espada de la Asesina, La Rueda del Tiempo. El Ojo del Mundo y La sangre de los elfos. Son datos reales recibidos de Open Library, aceptados por política automática OL-1; no se afirma revisión humana individual de cada campo ni certificación bibliográfica universal.

Las dos candidatas señaladas son:

- **Mort:** título de cuatro caracteres. La heurística no demuestra error; requiere confirmación selectiva.
- **Haunting Adeline:** el detalle original contiene title=Meow y otro full_title; además difiere del título preparado. Se conserva la contradicción como alerta y no se inventa una corrección.

Estas dos revisiones reales siguen sin resolver; las pruebas de aceptación manual usan datos sintéticos aislados. Las otras 993 candidatas no se aceptan porque el indicador de Search API o de la base preparada no sustituye los JSON específicos de la edición. Ampliar el catálogo requiere más evidencia real, no relajar esos controles para alcanzar una cantidad.

La base creada está en [datos/generados/integracion_2d/biblioteca.db](../datos/generados/integracion_2d/biblioteca.db). Se conserva localmente, fuera del control de versiones; se puede reconstruir sobre un destino nuevo con el comando del README. Las entradas originales, el pipeline y el contrato externo permanecen intactos.

## Responsabilidades implementadas

| Componente | Resultado |
|---|---|
| [FuenteOpenLibrary](../biblioteca/importacion/fuente_openlibrary.py) | SQLite de preparación en modo sólo lectura y consulta por flujo; detalles JSON asociados por ID exacto. Si un mismo ID tiene detalles contradictorios, no elige uno arbitrariamente. |
| [CandidatoOpenLibrary y resultados técnicos](../biblioteca/importacion/modelos.py) | Instantánea JSON canónica inmutable, huella SHA-256, controles y normalizados; seguimiento diferencia última evaluación y evidencia de la decisión vigente. |
| [ValidadorOpenLibrary](../biblioteca/importacion/validador_openlibrary.py) | Política OL-1: identidades, relaciones, autoría, detalle, idioma, ISBN, portada y campos; alertas bibliográficas separadas. |
| [ImportacionRepository](../biblioteca/repositorios/importacion_repository.py) | Evaluaciones/versionado, decisiones manuales/automáticas, correcciones, historial y correspondencia con UUID local; no confirma transacciones. |
| [ImportacionService](../biblioteca/servicios/importacion_service.py) | Evaluar, revisar, consultar evidencia nueva/aprobada e integrar por ID OL, con detección de duplicados y transacción completa. |
| [ProcesadorMaterias](../biblioteca/servicios/procesador_materias.py) | Comparte el procesamiento de 2C con importación, dentro de la transacción del caso de uso; conserva revisiones humanas. |
| [Comando de importación](../biblioteca/importacion/__main__.py) | Composición de componentes, evaluación/carga offline y resumen; fuente/destino distintos, límite configurable y modo sólo evaluación. |

No se añadieron dependencias, estados de importación a Edicion ni patrones nuevos. ClasificacionService mantiene su API; se extrajo su procesamiento para evitar transacciones anidadas y duplicación de reglas. La clasificación, los metadatos y la correspondencia se guardan juntos al integrar.

## Política y límites importantes

La validación contrasta identidades y vínculos contra el detalle original, exige español en la edición, ISBN con formato/control válido y portada positiva de esa edición. Una portada de obra no la sustituye. No acredita disponibilidad remota ni contenido visual de la portada. La autoría proviene de la obra, conservando su orden; los colaboradores que aparezcan en la edición no se agregan automáticamente.

Las alertas de título breve/discrepante, múltiples ISBN, edición multilingüe, rechazo en fuente y muchos autores requieren revisión cuando los controles están completos. Las contradicciones objetivas o estructuras inválidas no se pueden aprobar omitiendo los controles. El estado preparado VALIDADA no evita una comprobación nueva. Repetir la misma instantánea/política conserva la evaluación y la decisión automática; cambiar su resultado exige otra versión de política.

Los campos opcionales no bloquean una edición técnicamente completa. Fechas textuales complejas quedan en la instantánea sin adivinar año. No se importa una sinopsis como española sólo porque la edición declare spa. Las clasificaciones exploratorias no se heredan: sólo se procesan materias mediante las reglas explícitas de 2C; las desconocidas se conservan sin inventar géneros.

Una aceptación manual puede resolver alertas con motivo y títulos corregidos explícitamente. La decisión queda vinculada a la instantánea revisada. Una nueva fuente no hereda esa aprobación: se conserva como última evaluación aparte, accesible mediante evidencia, y la integración sigue usando la evaluación de la decisión vigente. Los rechazos humanos también prevalecen al reevaluar o cambiar de política.

La reimportación **conserva todos los metadatos, autorías y preferencias existentes**. Es una política deliberadamente conservadora: también deja vacíos existentes sin completar automáticamente. La aplicación aún no distingue propiedad por campo; las correcciones y ampliaciones se realizan explícitamente con el servicio del catálogo. Los cambios de fuente quedan en auditoría. Un rechazo posterior no borra entidades con inventario/historia.

No se fusionan autores por nombre ni obras por título/ISBN. Una coincidencia de título/autores o ISBN exige revisión antes de continuar como registro distinto. confirmar_distinta sólo permite ese caso; nunca reasigna una edición a otra obra. Los conflictos dejan el alta revertida y la evaluación previa disponible para revisión.

## Persistencia y migración

La [migración 005](../biblioteca/persistencia/migraciones/005_importacion.sql) eleva el esquema de 4 a 5 y agrega:

- evaluacion_importacion: edición, huella, política, estado, instantánea original, controles, alertas, datos normalizados y fecha.
- decision_importacion: evaluación concreta, estado, método, motivo, correcciones explícitas y fecha.
- seguimiento_importacion: última evaluación, decisión vigente y correspondencia local/integrada.

Las claves compuestas impiden usar evaluaciones o decisiones de otra candidata. La migración se probó sobre un esquema 4 construido con sus cuatro SQL originales, con sede inactiva, socio inhabilitado, ejemplar dado de baja y rechazo humano de género. Conserva todas las filas anteriores. Un fallo de DDL mantiene esquema 4 y permite reintentar sin tablas parciales.

Una integración confirma autor/obra/edición/preferencia inicial/materias/clasificación/correspondencia juntos. Un fallo de evidencia revierte todos esos registros. Evaluar es un caso independiente: la auditoría sigue disponible aunque integrar encuentre un duplicado o falle.

## Ejecución real y repetición

Desde la raíz con el entorno activado:

```bash
python -m biblioteca.importacion \
  --fuente datos/openlibrary/prevalidacion/catalogo_prevalidacion.db \
  --detalles datos/openlibrary/respuestas_originales.json \
  --destino datos/generados/integracion_2d/biblioteca.db
```

Ambas ejecuciones terminaron con código 0, sin conflictos y con los resultados de la tabla inicial. Se compararon filas de autores/obras/ediciones/relaciones antes y después de repetir: conservaron UUID y metadatos. Los SHA-256 de los tres insumos (base, detalles y catálogo exploratorio) permanecieron iguales. La base de destino informó integrity_check=ok y ninguna violación de claves foráneas.

Se conservaron 1.000 evaluaciones y 1.000 decisiones, sin duplicarlas. Las cinco obras integradas tienen 121 materias registradas. La clasificación produjo dos géneros aprobados, uno propuesto por contexto y tres vínculos de público aprobados; no se impuso un género a las otras obras ni se crearon etiquetas sin correspondencia explícita. Hay cero ejemplares: el alta física es una acción separada.

## Pruebas ejecutadas

Python 3.14.8, pytest 9.2.0:

```text
python -m pytest -q tests/test_importacion.py tests/test_validacion_openlibrary.py tests/test_fuente_openlibrary.py tests/test_migraciones_importacion.py
66 passed in 1.75s

python -m pytest -q
340 passed in 2.42s
```

Cobertura nueva: controles técnicos y datos malformados; ISBN/idioma/portada propios; autoría frente a colaboradores; títulos Meow/Mort y muchos autores; fuente de sólo lectura; detalles contradictorios; decisiones humanas/versionado/instantáneas nuevas; dos ediciones de una obra; preservación de correcciones/preferencia/UUID; clasificaciones ambiguas y rechazo humano; posibles duplicados y rollback; persistencia tras reabrir; migración y claves compuestas; CLI offline real repetida.

Además, un recorrido integra una edición, registra una copia explícitamente en una sede y consulta disponibilidad. Al inactivar esa sede, la disponibilidad pasa a cero sin borrar la copia. La prueba conecta importación, catálogo, inventario y administración. El editor no informó errores en código ni pruebas.

## Continuidad

2D cubre la conexión Open Library comprometida en la presentación y complementa catálogo/identidad de RF03 y RN05. Las 340 pruebas no sustituyen la interfaz ni los procesos de circulación pendientes. No se descargaron fuentes nuevas ni se alcanzaron 100.000 obras reales.

El próximo incremento es **2E: integración de catálogo/inventario y mediciones de escala**, con datos sintéticos identificados y consultas/planes medidos antes de incorporar Flet. Ampliar el catálogo real seguirá siendo un proceso distinto, conservando los controles y la trazabilidad implementados.
