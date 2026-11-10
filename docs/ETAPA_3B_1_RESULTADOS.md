# Modo oscuro y consulta de catálogo 3B.1

Fecha: 4 de noviembre de 2026. Incremento acotado para revisar la interfaz de escritorio antes de conectar datos. La etapa 3B completa permanece pendiente.

## Presentación

El botón junto a la sede alterna claro/oscuro durante la sesión. Se sustituyeron colores fijos de texto, superficies, bordes, selecciones, avatares y encabezados de tabla por colores semánticos de Flet. El tema cambia sin reconstruir vistas ni descartar filtros, selección de sede o página. Las portadas ilustrativas conservan sus colores propios. No se añadió persistencia de preferencias ni acceso a SQLite desde controles.

Se inició el cliente desktop con la tarea existente. Aparecieron avisos GTK de accesibilidad/cursor y un aviso de espera del primer fotograma OpenGL al redimensionar; no se informó excepción Python al iniciar. La inspección visual se realizó con el mismo código en Flet web local, aproximadamente 929 × 548: botón de tema, navegación, cuadrícula, cambio a tabla y ficha en modo oscuro. Se abrió también el formulario de socios en oscuro. La revisión final de distribución en el escritorio del usuario sigue siendo útil; no se automatizó el cliente nativo.

## Consulta preparada para 3B

Se añadió [CatalogoService.consultar_pagina](../biblioteca/servicios/catalogo_service.py), delegando todo el SQL a [ObraRepository](../biblioteca/repositorios/obra_repository.py). Se conservó listar_obras y todos sus llamadores anteriores.

La consulta devuelve [PaginaCatalogo y EntradaCatalogo](../biblioteca/resultados_catalogo.py): total, límite/desplazamiento, sede consultada y una entrada por obra, con su ficha bibliográfica, portada de edición preferida, géneros aprobados y cantidad disponible en el ámbito seleccionado. No carga todas las entidades ni hace una consulta por tarjeta.

- Texto único: título original, cualquier edición española o autor, con lógica OR. La unión de identidades se resuelve dentro de SQL **antes de LIMIT/OFFSET**; nunca se juntan páginas en Flet.
- Texto literal parametrizado, con la normalización casefold existente. No se introdujo una promesa nueva de equivalencia entre letras acentuadas y no acentuadas.
- Género: sólo asociaciones de tipo GENERO y estado APROBADO; etiquetas y público permanecen separados.
- Disponibilidad: disponibles=True exige copias utilizables; False exige ausencia de copias disponibles; None conserva obras con y sin disponibilidad. La sede sola cambia el ámbito de las cantidades y no oculta obras sin stock local. Una sede inexistente se informa como error.
- La proyección conserva LIBRE, APTO, sede actual igual a propietaria, sede activa y obra con autoría. Cuenta todas las ediciones de la obra. No convierte una copia ajena en disponible por estar físicamente en otra sede.
- Total y página comparten una instantánea con [lectura_consistente](../biblioteca/persistencia/base_datos.py). No se usa BEGIN IMMEDIATE para leer. Se respeta una transacción existente del llamador, sin confirmarla ni revertirla.
- Cinco SELECT para una página no vacía, seis con comprobación de sede. Autores, géneros y disponibilidad se recuperan por lote para los IDs de esa página. Una página fuera de rango queda vacía y conserva el total correcto.

La ficha futura reutilizará la consulta de disponibilidad por sede del inventario, que ya distingue propios, ubicados, bajas y disponibles. Las pruebas confirman el caso de una copia ajena ubicada en Norte: ubicada=1, propia=0, disponible=0.

## Verificación

**381 pruebas aprobadas**, sin advertencias de pytest: 357 anteriores, 23 casos nuevos de consulta y una prueba de alternancia de tema conservando estado. Ver [pruebas de consulta](../tests/test_consulta_catalogo.py) y [presentación](../tests/test_prototipo_interfaz.py).

La consulta se comprobó sobre SQLite temporal con varias ediciones/autores, desempates de título, páginas vacías, registros sin metadatos opcionales, filtros antes de LIMIT, copias dañadas/de baja/ajenas/sin ubicación, sede inactiva, género propuesto/aprobado/rechazado, filtros inválidos y cantidad acotada de SELECT. Un escritor concurrente en WAL cambia títulos entre total y página; la respuesta conserva una instantánea coherente y la consulta siguiente observa el cambio.

Diagnósticos del editor revisados para los módulos modificados: sin errores informados. No se cambió el esquema operativo (versión 6) ni se escribió en las bases reales.

También se ejecutó la consulta nueva contra la base generada de 2D, abierta con mode=ro: cinco obras, cinco entradas en la página, cero disponibles y búsqueda por autor correcta. SQLite informó cero cambios. Esto comprueba compatibilidad con el conjunto real existente, sin confundirlo con las 100 obras todavía pendientes.

## Continuidad y límites

Se analizó el camino de reutilización antes de modificar código; queda en [diseño de 3B](./ETAPA_3B_DISENO.md). El [contrato bibliográfico](../herramientas/openlibrary/CONTRATO_PARA_UML.md) registra el cambio de alcance como un agregado explícito, sin redefinir resultados históricos.

Todavía no se ha implementado OL-2-LOCAL ni se han preparado las 100 obras/150 copias. La base integrada anterior conserva sus cinco obras reales. La interfaz sigue usando los seis libros y cuatro socios de muestra de 3A; todavía no llama a la nueva consulta desde eventos Flet.

Sigue 3B.2: preparar y auditar el conjunto local, política versionada para ausencias, bases operativa/demo independientes e idempotencia. Después, 3B.3 conectará catálogo y ficha con consultas acotadas fuera del ciclo gráfico y conexiones propias por trabajador. Finalmente, 3B.4 medirá acción a renderizado sobre 100.000 obras sintéticas. Este incremento no mide ni afirma latencia integrada, ni añade FTS5, caché, keyset, préstamos o logística.

Continuidad posterior: [3B.2 completada](./ETAPA_3B_2_RESULTADOS.md), con 100 obras reales y demo de 150 copias. Las cifras de este informe describen el estado al cerrar 3B.1.
