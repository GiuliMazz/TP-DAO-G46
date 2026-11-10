# Incremento 2E — Consolidación y mediciones de etapa 2

## Alcance antes de implementar

Cerrar el backend de catálogo/inventario con evidencia de integración y escala. No ampliar circulación, interfaz ni descarga de fuentes. Se conservan las entidades, responsabilidades y contrato Open Library de los incrementos anteriores.

## Recorrido funcional

Una prueba integrada usará los servicios para conservar sedes/socios de etapa 1, importar una candidata real con aceptación automática, consultar el título original y español, administrar otra edición y copias explícitas en distintas sedes, revisar clasificación, registrar daño/baja y consultar disponibilidad. Reabrirá la base y repetirá la importación para comprobar identidades, revisiones y datos operativos. Se verificará también un fallo del procesamiento de materias que debe revertir el alta sin eliminar la evaluación previa.

Los datos bibliográficos reales y las copias/socios de prueba se distinguirán; ninguna prueba escribirá sobre la referencia o el catálogo local generado en 2D.

## Herramienta de carga

Se incorporará una herramienta de desarrollo separada del código de negocio:

- Generar una SQLite temporal en disco con UUID deterministas y datos marcados como sintéticos, sin IDs OL inventados.
- Cargar por lotes acotados, conservando claves foráneas y el esquema real; incluir varias ediciones/autores, títulos coincidentes, asociaciones aprobadas/propuestas/rechazadas y copias aptas/dañadas/de baja en sedes activas/inactivas.
- Invocar los servicios reales para listar, filtrar y consultar detalle/disponibilidad. La carga SQL directa es una fixture de volumen, no un importador ni una vía de altas de producción.
- Comprobar resultados, límites de página, ausencia de duplicados, disponibilidad esperada e integridad. Capturar planes de las consultas realmente ejecutadas mediante SQLite, sin duplicar el SQL de producción en la herramienta.
- Medir tamaños de 1.000, 10.000 y 100.000 obras; registrar tiempo de generación, mediana/máximo de consultas repetidas, pico de memoria Python de una llamada y máximo RSS del proceso cuando el sistema lo permita. El pico Python excluye memoria nativa de SQLite; el RSS incluye generación y consultas.

Escenarios: primera página, página profunda, título original, título de edición alternativa, autor, género/tema/público y filtros combinados, búsqueda sin resultados, detalle y disponibilidad/listado de ejemplares. Los resultados de consultas deben ser acotados aun cuando el catálogo crezca.

## Criterio de decisión

Como referencia inicial para este equipo se buscará una mediana inferior a 500 ms por consulta de hasta 50 resultados con caché de SQLite calentada. Es un objetivo local de evaluación, no un requisito de la consigna ni un SLA. Se informarán valores efectivos, consultas lentas y límites de generalización; los tiempos no serán aserciones de pytest.

Primero se medirá la implementación actual. Sólo si aparecen problemas se modificará el SQL o sus índices, explicando la causa observada y comparando antes/después sobre el mismo conjunto. FTS y paginación por clave quedan sujetos a evidencia; no se cambia la semántica de búsqueda por fragmento para acelerar una medición.

## Criterio de salida

Suite completa aprobada; recorrido integrado persistente; medición reproducible hasta 100.000 obras sintéticas con planes y memoria documentados; alcance de etapa 2 actualizado y límites explícitos antes de comenzar Flet. Cinco obras reales integradas en 2D siguen siendo cinco: la carga sintética no se presentará como ampliación del catálogo de Open Library.
