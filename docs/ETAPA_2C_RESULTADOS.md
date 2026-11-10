# Incremento 2C — Clasificación revisable del catálogo

Fecha: 3 de noviembre de 2026. Estado: implementado y verificado. Suite completa: **274 pruebas aprobadas**, incluidas 48 nuevas de clasificación y migración. Diseño de referencia: [etapa 2](./ETAPA_2_DISENO.md) y [UML actualizado](./UML_ETAPA_2.md).

## Alcance y responsabilidades

Se pueden administrar términos de género, tema y público; proponer asociaciones con una obra; aprobarlas/rechazarlas manualmente; procesar materias mediante reglas versionadas y filtrar el catálogo por asociaciones aprobadas. Se conserva el texto original y la evidencia de las evaluaciones, incluso cuando una decisión humana impide aplicar su resultado.

| Componente | Responsabilidad |
|---|---|
| [Genero, Etiqueta y PublicoDestinatario](../biblioteca/dominio/clasificacion.py) | Términos validados e inmutables, con UUID y tipo propio. Nombre único dentro de cada vocabulario. |
| [ClasificacionObra y DecisionClasificacion](../biblioteca/dominio/clasificacion.py) | Controlar aprobación/rechazo y prioridad de decisiones humanas; registrar motivo, fecha con zona horaria, método y regla/versionado cuando aplica. |
| [ReglaClasificacion](../biblioteca/servicios/reglas_clasificacion.py) | Comparar una materia exacta y evaluar el contexto antes de proponer/aprobar. No accede a SQLite. |
| [ClasificacionService](../biblioteca/servicios/clasificacion_service.py) | Coordinar términos, propuestas, revisiones y procesamiento atómico de materias. |
| [ClasificacionRepository](../biblioteca/repositorios/clasificacion_repository.py) | SQL parametrizado, reconstrucción del tipo concreto, evidencia e historial. No confirma transacciones por su cuenta. |
| [CatalogoService](../biblioteca/servicios/catalogo_service.py) y [ObraRepository](../biblioteca/repositorios/obra_repository.py) | Agregar filtros combinables por género, etiqueta y público, usando sólo APROBADO y conservando una ficha por obra. |

### Ajuste del borrador de clases

En vez de tres clases de asociación con implementación idéntica, se usa ClasificacionObra vinculada a un término tipado. Genero, Etiqueta y PublicoDestinatario siguen siendo clases distintas. Así las reglas de revisión se mantienen en un solo lugar, sin convertir público en un género ni duplicar el ciclo de vida. Se explicó antes de implementar y se actualizó el UML.

SQLite refleja esta decisión con vocabulario y asociaciones tipados, en lugar de las tablas separadas previstas inicialmente. El formato de entrada/salida del importador existente no se modificó; el adaptador de 2D resolverá el mapeo.

## Política de clasificación implementada

Las reglas iniciales se preparan explícitamente; migrar una base no crea términos ni clasificaciones:

| Materia de origen | Tipo | Término | Regla / versión |
|---|---|---|---|
| Fantasy fiction | Género | Fantasía | genero-fantasia / 1 |
| Magic -- Fiction | Etiqueta temática | Magia | tema-magia-ficcion / 1 |
| Children's fiction | Público | Infantil | publico-infantil / 1 |
| Young adult fiction | Público | Juvenil | publico-juvenil / 1 |

- Comparación exacta tras normalizar espacios y mayúsculas; el texto original se almacena intacto. No se eliminan palabras ni se separan materias compuestas para inventar varios géneros.
- Marcadores de crítica, estudio y adaptaciones en las materias de la obra impiden aprobar automáticamente un género. La coincidencia queda PROPUESTO con motivo; reglas configuradas sin aprobación automática también quedan pendientes.
- Una materia desconocida se conserva sin crear un término arbitrario. Sin evidencia de público no se asigna Adulto ni otro destinatario por defecto.
- La definición de una regla/versionado queda registrada y no puede cambiarse silenciosamente. Otra versión puede aprobar una propuesta automática anterior.
- Cada procesamiento considera todas las materias ya guardadas de esa obra. Si la misma regla detecta contexto dudoso posterior, puede devolver su aprobación automática a PROPUESTO, con nuevas evidencia e historia. Otra regla candidata no revoca una aprobación.
- Las aprobaciones y rechazos humanos prevalecen al reprocesar, incluso con otra versión o nuevo contexto. Las evaluaciones discrepantes quedan accesibles para auditoría. La revisión manual puede corregirse con otra revisión, sin borrar decisiones anteriores.
- Repetir el mismo procesamiento no duplica asociaciones, materias, evaluaciones ni decisiones. Dos fuentes o materias diferentes pueden respaldar una única asociación.

La evidencia guarda fuente, texto literal, resultado de la evaluación, motivo, regla/versionado, fecha y contexto. El historial guarda las decisiones efectivamente aplicadas en orden de registro; una evaluación automática favorable no equivale a aprobación vigente si existe rechazo humano. Las consultas de auditoría son paginadas, hasta 100 registros por llamada.

Estas reglas y sus bloqueos son una política inicial conservadora. Las pruebas comprueban su comportamiento; todavía no se midió precisión o cobertura sobre el catálogo real. Cambiar los controles de contexto requerirá versionar las reglas afectadas. No se retiran automáticamente materias ausentes de un nuevo lote ni se infiere rechazo por falta de información.

## Persistencia e integridad

La [migración 004](../biblioteca/persistencia/migraciones/004_clasificacion.sql) agrega:

- termino_clasificacion: unicidad por tipo/nombre normalizado.
- clasificacion_obra: una asociación por obra/término y clave compuesta que exige el tipo correcto.
- materia_original: fuente y texto original por obra.
- regla_clasificacion: definición inmutable por identificador/versionado.
- evidencia_clasificacion: evaluación vinculada a una materia de la misma obra y a una regla existente.
- decision_clasificacion: historial de decisiones aplicadas.

El esquema operativo pasa de 3 a 4. No se alteran migraciones previas. Las pruebas actualizan una base auténtica versión 3 con sede inactiva, socio inhabilitado, catálogo con IDs OL y ejemplar dañado dado de baja; conservan todas sus filas, identidades y relaciones. Un fallo de DDL conserva versión 3, datos previos y posibilidad de reintentar.

Los filtros usan pertenencia a conjuntos de obras aprobadas, evitando unir todas las relaciones N:M al resultado. El orden y los límites de página se mantienen. No se afirma rendimiento con 100.000 obras: corresponde medirlo en 2E.

## Verificación realizada

En Python 3.14.8 y pytest 9.2.0:

```text
python -m pytest -q tests/test_clasificacion.py tests/test_migraciones_clasificacion.py
48 passed in 0.23s

python -m pytest -q
274 passed in 0.76s
```

Las pruebas comprueban validación y cambios atómicos del dominio; vocabularios separados; reglas exactas; contexto de crítica/estudio; evidencia literal; aprobaciones/rechazos humanos preservados; versionado; repetición; fuentes múltiples; rollback de materia/asociación/historial ante fallo; persistencia al reabrir; filtros combinados con varios autores/ediciones y páginas consecutivas; migración y restricciones SQL. También verifican que clasificar no cambia catálogo, ejemplares ni sedes.

El editor no informó errores en código ni pruebas. La [demostración temporal](../biblioteca/demo_clasificacion.py) terminó con código 0:

```bash
python -m biblioteca.demo_clasificacion
```

Aprueba Magia, Fantasía y Juvenil en sus respectivos vocabularios; el filtro de Fantasía devuelve una obra. Después del rechazo humano y reprocesamiento conserva RECHAZADO, dos decisiones históricas y cero ejemplares creados. Son datos sintéticos, no registros reales validados.

## Continuidad

2C amplía la clasificación y consulta de RF03 y la prevención de duplicados bibliográficos de RN05. No completa por sí solo todos los procesos del TP. El siguiente incremento es **2D: aceptación técnica e integración de Open Library**, con controles automáticos, auditoría selectiva y preservación de identidades/revisiones. La muestra, el contrato externo y el pipeline existentes se mantienen intactos.
