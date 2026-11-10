# Incremento 2E — Consolidación de catálogo e inventario

Fecha: 3 de noviembre de 2026. Estado: completado a nivel de backend, según el [diseño de 2E](./ETAPA_2E_DISENO.md). Suite completa: **347 pruebas aprobadas**. Etapa 2 conserva la arquitectura y las reglas de 2A–2D; la siguiente etapa es la primera interfaz Flet.

## Recorrido funcional comprobado

La [demostración consolidada](../biblioteca/demo_etapa2.py) usa el detalle real de El ladrón del rayo y crea una base temporal nueva. Las sedes, socio, segunda edición, ejemplares, correcciones y revisión humana del recorrido se identifican como **simulados**; no se incorporan al catálogo real ni se presentan como una auditoría bibliográfica auténtica.

El recorrido registra sedes y socio de etapa 1, inhabilita al socio, evalúa/importa la candidata, busca la obra por título original y español, registra otra edición y la selecciona como preferida. Agrega dos copias en Centro (una apta y otra dañada), una apta en Norte y ninguna en Sur. La disponibilidad inicial es Centro=1, Norte=1, Sur=0, sin multiplicar copias por ediciones/autores.

Después registra daño/baja e inactiva Norte; la disponibilidad final es cero en las tres sedes. Aplica un rechazo de género simulado y una corrección de título de demostración. Cierra la conexión, reabre y reimporta: conserva UUID, corrección, preferencia, socio inhabilitado, sede inactiva, tres copias y rechazo humano. Las fuentes quedan intactas; la base temporal se elimina al terminar.

```bash
python -m biblioteca.demo_etapa2
```

Terminó con código 0. La prueba pytest correspondiente verifica también integridad, conservación de las huellas de las fuentes y una sola obra con dos ediciones al finalizar. Las pruebas de 2D siguen comprobando rollback completo si falla clasificación, decisiones humanas e integración sin crear ejemplares automáticamente.

## Carga de escala reproducible

La [fixture de volumen](../herramientas/catalogo_sintetico.py) genera bases temporales con esquema real y UUID deterministas. No inventa IDs de Open Library. Los títulos y códigos identifican datos sintéticos; las clasificaciones tienen motivos de prueba. La carga SQL por lotes es exclusivamente infraestructura de medición: no evita validaciones en operaciones normales ni funciona como importador alternativo.

| Carga | Obras distintas | Ediciones | Autores | Autorías | Copias | Clasificaciones |
|---|---:|---:|---:|---:|---:|---:|
| Pequeña | 1.000 | 1.200 | 1.000 | 1.100 | 1.400 | 1.833 |
| Intermedia | 10.000 | 12.000 | 2.000 | 11.000 | 14.000 | 18.333 |
| Objetivo de medición | 100.000 | 120.000 | 2.000 | 110.000 | 140.000 | 183.333 |

Incluye segunda edición en una de cada cinco obras, dos autores en una de cada diez, títulos compartidos, distintas preferencias y asociaciones aprobadas/propuestas/rechazadas. Hay copias aptas, dañadas y de baja en tres sedes, una inactiva. La fixture conserva integridad y agrega historial de las decisiones sintéticas.

La [herramienta de medición](../herramientas/medir_etapa2.py) invoca servicios/repositorios reales, verifica resultados y captura el SQL ejecutado para obtener su EXPLAIN QUERY PLAN. No mantiene otra copia del SQL de producción. Comprueba límites, unicidad, búsquedas original/alternativa, filtros aprobados, preferencia, disponibilidad y códigos esperados en páginas iniciales/profundas de ejemplares.

```bash
python -m herramientas.medir_etapa2 \
  --tamanos 1000 10000 100000 \
  --repeticiones 5 \
  --limite-segundos 5 \
  --salida datos/generados/etapa2e/mediciones_finales.json
```

Los informes [inicial](../datos/generados/etapa2e/mediciones_iniciales.json) y [final](../datos/generados/etapa2e/mediciones_finales.json) se conservan localmente fuera del control de versiones. Incluyen muestras individuales, planes completos y contexto del entorno. Las bases de volumen se eliminaron; no se mezclaron con la base real de 2D.

## Método y resultados

Entorno observado: Python 3.14.8, SQLite 3.51.2, Linux x86_64. Cada escenario tiene una llamada previa de calentamiento y reutiliza conexión; el tamaño de página es 50. La corrida inicial registró tres muestras por escenario completado; la final cinco, con tiempo de pared y CPU. No se midió almacenamiento en frío, interfaz ni concurrencia.

El límite inicial fue dos segundos por llamada. Las consultas interrumpidas no tienen mediana y se informan como tales; la herramienta también conserva una interrupción que ocurra durante las repeticiones o la medición de memoria. La corrida final usó un límite de cinco segundos y completó todos los escenarios. La diferencia de repeticiones/límites y la variabilidad entre corridas impiden interpretar esta comparación como un benchmark estadístico controlado o garantía para otros equipos.

Con **100.000 obras sintéticas**, valores en milisegundos:

| Escenario | Inicial: mediana o límite | Mediana final | Máximo final |
|---|---:|---:|---:|
| Primera página | 563,76 | 341,28 | 344,83 |
| Página profunda de catálogo, OFFSET 99.950 | 894,43 | 465,97 | 468,79 |
| Título original | 202,38 | 20,77 | 21,33 |
| Título de edición alternativa | 200,75 | 20,68 | 21,29 |
| Autor | 215,48 | 30,20 | 31,25 |
| Género | 128,29 | 118,42 | 139,32 |
| Etiqueta temática | 245,56 | 220,70 | 224,75 |
| Público | 168,19 | 145,75 | 148,49 |
| Filtros combinados con coincidencias | 82,22 | 78,84 | 80,22 |
| Título sin resultados | 197,96 | 20,76 | 21,00 |
| Detalle de obra | 0,11 | 0,12 | 0,15 |
| Disponibilidad por sede | 292,39 | 0,35 | 0,38 |
| Ejemplares disponibles de una obra | 0,12 | 0,10 | 0,14 |
| Ejemplares disponibles de una sede | Interrumpida tras 2 s | 0,61 | 0,75 |
| Página profunda de ejemplares de una sede | Interrumpida tras 2 s | 441,74 | 443,13 |

Todas las medianas de la última corrida quedaron por debajo de la referencia local de **500 ms** planteada antes de medir. Esa referencia no es una exigencia de la consigna ni un SLA. Las páginas profundas siguen siendo las más costosas: OFFSET debe atravesar resultados anteriores y el orden de títulos preferidos aún usa ordenamiento temporal. Si crecen los datos o cambia la carga, se deberá medir de nuevo y evaluar paginación por clave.

## Cambios justificados por evidencia

1. **Listado de ejemplares.** El plan inicial combinaba la pertenencia al conjunto global de obras con autoría con las búsquedas de ediciones/copias. Con 1.000 obras se observaron aproximadamente 3.992.000 instrucciones de SQLite para una página de 50 copias; la nueva regresión agotaba un presupuesto de 500.000 instrucciones. Se reemplazó por una comprobación de autoría indexada por la obra de cada edición. La regresión pasa sin una aserción de milisegundos dependiente de CPU. No se atribuye el comportamiento a un defecto interno de SQLite sin evidencia adicional.
2. **Orden de copias por sede.** La [migración 006](../biblioteca/persistencia/migraciones/006_indices_consultas.sql) incorpora el índice por ubicación, situación, condición, código e ID. El plan final usa ix_ejemplar_sede_estado_codigo para filtrar y recorrer el orden solicitado; elimina el ordenamiento temporal de esa consulta. Agrega espacio de índice, sin alterar entidades ni registros.
3. **Disponibilidad.** El plan anterior recorría el inventario de cada sede en subconsultas correlacionadas y después verificaba la obra. Ahora agrupa primero copias de la obra por propietaria y por ubicación, usando los índices existentes de edición/obra y ejemplar/edición, y combina esos agregados con todas las sedes. Conserva ceros, bajas históricas, sedes inactivas y ubicación nula; no multiplica por autores.
4. **Páginas del catálogo.** Se evitan filtros de texto vacíos y se selecciona la página antes de contar sus ediciones. Los autores de toda la página siguen recuperándose en una consulta adicional: son dos consultas, no una por ficha. La prueba que contaba SELECT se ajustó para contar también WITH y conservar esa comprobación.
5. **Título y autor.** El título independiente obtiene un conjunto único de IDs por original o cualquier edición española, evitando búsquedas de ediciones por cada obra del catálogo. Cuando hay otros filtros se evalúa el título sobre sus candidatas, evitando construir un conjunto global amplio. El filtro de autor obtiene obras a partir de autores coincidentes. Se conserva la búsqueda literal por fragmento, acentos/mayúsculas según la normalización previa, preferencia y orden estable.

No se añadieron FTS, servidores, dependencias ni patrones. No se cambió el contrato Open Library. Las asociaciones propuestas/rechazadas siguen fuera de los filtros públicos, y una consulta nunca convierte estar ubicado en otra sede en transferencia de propiedad.

## Memoria y almacenamiento

La fixture se carga en lotes de 1.000 obras. Estas son las cifras finales:

| Obras | Base SQLite | Generación | Mayor pico Python por consulta |
|---|---:|---:|---:|
| 1.000 | 3,67 MiB | 0,10 s | 63,40 KiB |
| 10.000 | 32,86 MiB | 1,19 s | 63,85 KiB |
| 100.000 | 325,04 MiB | 19,32 s | 63,85 KiB |

El máximo RSS del proceso completo fue **34,61 MiB**, incluyendo generación, verificaciones y consultas. tracemalloc mide memoria Python de una llamada y excluye memoria nativa de SQLite; RSS no mide la caché de archivos del sistema operativo. Tampoco incluye otros procesos. Los tiempos de generación no son tiempos de importación Open Library: la fixture usa carga SQL directa. La base no replica sinopsis ni instantáneas de importación de 100.000 registros reales, por lo que su tamaño no predice el tamaño definitivo de ese catálogo.

## Persistencia e integridad

El esquema pasa de 5 a 6 agregando sólo el índice de ejemplares. Las pruebas reconstruyen el esquema 5 retirando ese único índice de una base con todo el recorrido integrado, y verifican todas las filas, integridad y migración repetida. Un fallo posterior al CREATE INDEX revierte índice y versión, conservando la posibilidad de reintentar.

También se actualizó la base real generada en 2D del esquema 5 al 6: se compararon todas las filas de sus **16 tablas** antes/después y se conservaron. Sigue teniendo cinco obras reales y cero ejemplares. integrity_check informó ok y no hubo violaciones de claves foráneas. Los datos sintéticos no se incorporaron a ella.

## Verificación final y cobertura

```text
python -m pytest -q
347 passed in 2.98s
```

Se agregaron siete casos: recorrido conjunto con fuentes intactas, reproducibilidad de la fixture, medición de los servicios y captura SQL, interrupción durante una repetición con limpieza del callback, presupuesto de instrucciones del listado y migración normal/fallida del índice. La suite anterior conserva controles de dominio, catálogo, clasificación, inventario, importación, unicidad, concurrencia de altas y migraciones. El editor no informó errores en aplicación, herramientas ni pruebas.

| Requerimiento de etapa 2 | Evidencia de backend |
|---|---|
| RF03: catálogo y ejemplares | Obra/Edicion/Ejemplar separados, varias ediciones/copias, clasificación e integración con identidades estables. |
| RF06: disponibilidad | Resumen y listado por sede, daño/baja/sede inactiva, sin conteos duplicados. |
| RN05: prevención de duplicados | IDs OL, códigos y relaciones respaldados por restricciones; coincidencias bibliográficas señaladas y reimportación repetible. |
| Datos de etapa 1 | Socio inhabilitado y sedes conservados tras cerrar/reabrir/reimportar y migrar. |
| Escala del catálogo | 100.000 obras distintas sintéticas, consultas acotadas, planes y memoria medidos. |

La etapa 2 queda consolidada a nivel de backend. La interfaz Flet, préstamos, reservas, remitos, devoluciones, State/Strategy, recomendaciones y reportes siguen pendientes en el plan; estas pruebas no equivalen a la aplicación completa. El catálogo real mantiene cinco obras incorporadas, dos candidatas en revisión y 993 pendientes de evidencia adicional.
