# Etapa 3B — Catálogo local conectado

## Cambio de alcance acordado

Se prioriza circulación interbibliotecaria. La meta inicial pasa de 100.000 obras reales a aproximadamente **100 obras reales con edición española** y **150 ejemplares ficticios** entre Centro, Norte y Sur. Las 100.000 obras sintéticas se conservan exclusivamente como prueba de escala. No se rehace etapa 2 ni se incorporan motores o dependencias nuevos.

El dominio ya permite ISBN, portada y sinopsis ausentes. La política de importación OL-1 exige ISBN/portada: se conservará para reproducir evaluaciones anteriores y se añadirá OL-2-LOCAL, explícita y versionada, que permite ausencias, no contradicciones ni ISBN inválidos. Se mantienen identidad OL de obra/edición/autor, relación edición–obra y evidencia de idioma español. Los casos dudosos requieren revisión; corregir títulos se registra con motivo mediante el servicio existente. Nunca se inventan metadatos bibliográficos. En 3B.4, por pedido del usuario, la presentación admite cubiertas tipográficas identificadas como «Portada ilustrativa» sin asignarles una identidad de portada ni guardarlas como imagen de la edición.

## Datos reproducibles y separados

1. Reutilizar instantáneas existentes. Completar una selección acotada mediante API oficial; guardar respuestas, URL/fecha/huella y metadatos de procedencia. Priorizar consultas por lotes y respetar límites; no construir un importador masivo.
2. Preparar un manifiesto local auditable con una edición española por obra. Obra OL...W, edición OL...M y autores OL...A siguen siendo las identidades externas; UUID sigue siendo la identidad interna. No deduplicar sólo por título ni unir ediciones como si fueran obras distintas. Las posibles coincidencias se mantienen como conflictos para revisar.
3. Integrar con ImportacionService y repositorios existentes: repetir mantiene UUID, ediciones preferidas, metadatos corregidos y decisiones humanas. ISBN/portada ausentes se conservan como None.
4. Base operativa: bibliografía real, sin personas/copias ficticias. Base demo independiente: misma bibliografía y altas explícitas de sedes/150 copias de demostración a través de servicios, códigos DEMO identificables. No usar SQL directo para inventar estados de préstamos o traslados. Nunca reconstruir ni reemplazar una base operativa existente para regenerar la demo.
5. Portadas locales preparadas junto con los datos; si no están disponibles, cubierta ilustrativa local con título, autor y rótulo explícito (ajuste acordado en 3B.4). Flet no consulta Open Library al ejecutarse. Una desconexión de internet no debe impedir búsquedas ni detalle.

## Incrementos

| Paso | Alcance | Evidencia de aceptación |
|---|---|---|
| Ajuste 3A | Tema claro/oscuro con un botón; conservar navegación, filtros y sede | Escritorio iniciado; inspección visual de controles, tabla y diálogos; pruebas de estado |
| 3B.1 | Consulta SQL paginada y buscador OR, filtros de género y disponibilidad local, DTO de página | Varias ediciones/autores sin duplicados; filtros antes de LIMIT; propiedad/ubicación/sede inactiva; cero resultados; compatibilidad de consultas anteriores |
| 3B.2 | Preparación de datos locales y demo separada, repetible | Conteos reales auditados, identidad conservada al repetir, ausencia válida de metadatos opcionales, integridad SQLite, 150 códigos demo únicos |
| 3B.3 | Conectar progresivamente catálogo/ficha a servicios | Cargas/errores; debounce; respuestas obsoletas descartadas; conexiones por trabajador; cierre de recursos; ninguna consulta SQL en Flet |
| 3B.4 | Medición completa sobre 100.000 sintéticas | Desde acción del cliente hasta resultado renderizado, separando backend y envío; ventana interactiva; no denominar renderizado al simple retorno de page.update() |

Se verifica cada incremento antes del siguiente. Socios/sedes conectados y altas desde formularios corresponden a 3C. Préstamos, Strategy, remitos/State, reservas y reportes conservan su orden posterior.

Estado al cerrar 3B.2: consulta 3B.1 y datos reproducibles 3B.2 completados. Hay 100 obras/ediciones reales en ambas bases, 87 autores y 86 portadas locales; la demo tiene 150 copias, 50 por sede. Se conservó OL-1 y se implementó OL-2-LOCAL sin cambiar el esquema operativo 6. Flet continúa con el prototipo hasta 3B.3. [Resultados y verificaciones de 3B.2](./ETAPA_3B_2_RESULTADOS.md).

Actualización 3B.3: el catálogo y la ficha ya usan la base local mediante servicios, con lectura sin escrituras y ejecución fuera del ciclo gráfico. Se prepararon cobertura y auditoría visual, sin ampliar la selección. Socios sigue pendiente de 3C; no se muestran los socios de la maqueta como datos de la demo. [Resultados de 3B.3](./ETAPA_3B_3_RESULTADOS.md).

Actualización 3B.4: medidos 35 recorridos de cliente sobre 100.000 obras sintéticas, con ocho calentamientos y tres muestras por escenario. Se observaron por separado backend, envío del parche y captura del cliente, y se verificó interacción durante una lectura. La disponibilidad local utiliza ahora identidades de obra en lugar de recorrer las copias de la sede para cada obra; se conserva esquema 6 y reglas de negocio. Las cubiertas faltantes tienen diseño ilustrativo identificado. No se añadieron FTS5 ni cachés. [Resultados de 3B.4](./ETAPA_3B_4_RESULTADOS.md).

## Consulta y ejecución

El buscador único usa OR entre título original, todas las ediciones españolas y autor en SQL; género/sede/disponibilidad se combinan antes de paginar. Se devuelve una obra por fila, portada de la edición preferida, autores y disponibilidad sin una consulta por tarjeta. Se conserva comparación casefold existente (no se promete ignorar acentos si el backend no lo hace).

El filtro se denominará disponibilidad en sede. Con Todas muestra toda la red; con una sede, la cantidad disponible corresponde a esa sede, y el selector de disponibilidad decide si exigir alguna o ninguna disponible. La selección de sede por sí sola no oculta obras sin stock: permite detectarlas y buscar copias en otras sedes. La ficha siempre discrimina copias propias, ubicadas y disponibles de cada sede. Recibir una copia ajena no la vuelve disponible para otra solicitud.

Las lecturas SQLite se ejecutan fuera del ciclo gráfico. Un acceso acotado evita enviar una consulta por cada tecla. Cada operación abre/cierra su propia conexión; no se usa check_same_thread=False para compartir una conexión. Debounce de 300 ms y revisión por petición; ninguna respuesta atrasada modifica pantalla, mensajes o estado de carga de una nueva. Cancelar la espera no se considera cancelar una consulta iniciada. Sin FTS5, caché avanzada ni keyset hasta medir.

## Referencias

Se conserva el [contrato bibliográfico](../herramientas/openlibrary/CONTRATO_PARA_UML.md). Esta decisión modifica el alcance y la política de aceptación local, no el esquema de prevalidación original ni el significado histórico de OL-1.

APIs oficiales consultadas: [Open Library API](https://openlibrary.org/developers/api), [búsqueda](https://openlibrary.org/dev/docs/api/search). Open Library recomienda usar lotes para varias obras y conservar respuestas; la preparación queda fuera de la ejecución cotidiana de Flet.
