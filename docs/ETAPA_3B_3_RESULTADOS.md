# Etapa 3B.3 — Catálogo Flet conectado

## Alcance y responsabilidades

La entrada habitual abre la demo local previamente preparada. Catálogo y ficha consumen los servicios de etapas 1 y 2; conservan el esquema SQLite 6, las entidades y las reglas de propiedad/ubicación/disponibilidad. No se incorporaron dependencias, índices, FTS5 ni cachés adicionales. Socios no muestra los cuatro registros de la maqueta: queda pendiente de 3C. No se implementaron aún préstamos, reservas o remitos.

- [ConsultasCatalogoLocal](../biblioteca/consultas_locales.py) compone catálogo, clasificación, sedes e inventario. Abre `mode=ro`, verifica versión sin migrar y cierra una conexión por operación, dentro del trabajador que la creó. La página conserva la consulta SQL única previa a LIMIT; la ficha reúne ediciones, clasificaciones aprobadas y existencias de todas las sedes en una instantánea de lectura.
- [LectorAsincrono](../biblioteca/interfaz/lector_asincrono.py) ejecuta una lectura a la vez y conserva sólo la última petición pendiente por destino (catálogo, ficha, configuración). Los destinos están acotados. Cancelar una espera no libera anticipadamente el trabajador SQLite. Al desconectar se descartan pendientes; una reconexión espera asíncronamente la finalización del trabajador anterior antes de crear otro.
- [CatalogoLocalView](../biblioteca/interfaz/catalogo_local_view.py) controla debounce de 300 ms, revisión de cada petición, carga, errores, reintento, paginación y descarte de respuestas antiguas. Un error viejo tampoco reemplaza el resultado o estado de carga nuevo. Al cerrar una ficha se invalida su lectura pendiente. No contiene SQL ni reglas de disponibilidad. Reutiliza el render de tarjetas/tabla de la maqueta, sin paginar sus resultados otra vez en Python.
- [AplicacionHorizonte](../biblioteca/interfaz/aplicacion.py) compone navegación, inicio, temas y selección de sede. Obtiene sedes/géneros de la base. Los indicadores operativos se incorporarán cuando existan esos casos de uso; no presenta actividad o cantidades inventadas.

La sede superior representa el contexto de trabajo y no altera automáticamente los filtros. «Disponibilidad en sede» limita las cantidades; elegir una sede no excluye obras con cero disponibles. El selector adicional permite exigir disponibles/sin disponibles. La ficha discrimina propios, ubicados y disponibles por sede, incluso cuando la búsqueda se limita a otra sede.

## Bibliografía y separación de datos

Se conserva la selección de **100 obras, 100 ediciones españolas y 87 identidades de autor**. La demo contiene **150 ejemplares ficticios**, 50 por sede, y cero socios. La operativa tiene cero sedes/socios/ejemplares ficticios. Las bases conservan sus identificadores de tipo; iniciar la aplicación nunca ejecuta el preparador, migraciones ni altas de muestra. Una base ausente o incompatible produce un error recuperable, sin crear un archivo SQLite vacío.

Las 86 portadas se sirven desde la carpeta local de imágenes; no se consulta Open Library durante el uso. Una portada ausente, un archivo faltante o un fallo al decodificar la imagen muestran un reemplazo neutro. No se usa una cubierta ilustrativa como si fuera de una edición real. ISBN, año y sinopsis ausentes se indican expresamente. La descripción original puede estar en otro idioma y se rotula como tal.

Se prepararon [cobertura](./auditoria_catalogo/COBERTURA.md), [muestra visual autónoma de 20 obras](./auditoria_catalogo/auditoria_visual.html) y [hallazgos](./auditoria_catalogo/HALLAZGOS.md). La cobertura aprobada pasa de 17/0/16 a **53/26/16** obras con género/etiquetas/público. Hay propuestas pendientes; la evidencia parcial de Search y las cubiertas de baja legibilidad no se presentan como revisión bibliográfica definitiva. Las correspondencias locales se aplican explícitamente desde el preparador, también a materias ya integradas, preservando las decisiones humanas y los originales de Open Library.

## Verificaciones

Suite completa: **426 pruebas aprobadas** con Python 3.14.8 y Flet 1.0.5. Se agregaron 13 pruebas de conexión/presentación/concurrencia y 3 de reglas/cobertura. Las 410 anteriores siguen pasando. Ver [pruebas del catálogo conectado](../tests/test_catalogo_conectado.py) y [reglas locales](../tests/test_reglas_catalogo_local.py).

Se comprobó con bases temporales: archivo ausente no creado; esquema incompatible no migrado; hash de la base intacto después de consultar; conexiones distintas y cerradas en su mismo hilo; un trabajador aunque se cancele la espera; reemplazo de consultas pendientes; cierre/reconexión; respuestas y errores fuera de orden; salida durante debounce; cierre de ficha; error/reintento; filtros enviados antes de paginar; portadas ausentes y fallback ante error de imagen; ausencia de socios inventados al iniciar. Las reglas se prueban por coincidencia completa, separación de tipos, propuesta de descriptores ambiguos y preservación de rechazo humano.

Las pruebas de hilos se ejecutaron fuera del sandbox del agente: en este entorno la restricción de sockets locales impide la notificación de `asyncio` desde un hilo. No se introdujo un cambio en el programa para sortear esa restricción. Los diagnósticos del editor no informaron errores en los archivos revisados.

Se inició la aplicación nativa mediante la tarea de escritorio. En la vista web local con los mismos controles se verificaron: carga de 100 obras y 24 por página; búsqueda «Hobbit» y ficha real; búsqueda por título original «Lightning Thief» mostrando «El ladrón del rayo»; cambio de sede y disponibilidad; cero resultados; limpieza de filtros; segunda página (25–48); tabla y tema oscuro; portada neutra de «127 horas» y cubierta real de «El Hobbit». La ficha de este último mostró propios/ubicados/disponibles de Centro, Norte y Sur. Se inspeccionaron capturas visuales del catálogo, tabla y diálogo. La automatización visual se hizo en navegador; no se afirma automatización nativa completa ni medición de renderizado.

## Ejecución y siguiente incremento

```bash
python main.py
python main.py --base datos/generados/catalogo_local/operativa.db
python main.py --web --port 8551
python -m herramientas.auditar_catalogo_local
python -m pytest -q
```

La tarea de escritorio conserva por compatibilidad su nombre «Horizonte: prototipo de escritorio», aunque ahora abre el catálogo conectado. `--prototipo` permite revisar expresamente la maqueta histórica 3A; no se activa como alternativa automática si falta una base.

Queda pendiente 3B.4: medir la interacción completa y la respuesta del cliente con 100.000 obras sintéticas. Los tests de concurrencia no sustituyen esa medición ni se confunde `page.update()` con renderizado final. Después, 3C conectará socios/sedes e inventario y preparará socios ficticios mediante servicios explícitos. Se mantiene la prioridad de completar los procesos de préstamos interbibliotecarios.
