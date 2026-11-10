# Etapa 3B.4 — Medición integrada y cubiertas ilustrativas

Fecha: 7 de noviembre de 2026. Incremento completado. **431 pruebas aprobadas**. El siguiente incremento es 3C; no se implementaron socios, préstamos ni remitos adicionales en esta etapa.

## Cambios de presentación

Por pedido del usuario, cuando una edición no tiene imagen local o ésta falla se muestra una cubierta tipográfica: título, autor, geometría decorativa y el rótulo **PORTADA ILUSTRATIVA**. [Componente de presentación](../biblioteca/interfaz/portadas.py). La paleta depende de una huella estable de título y autor; conserva contraste en los temas claro y oscuro y no depende de red ni de archivos generados. Se utiliza en tarjetas y fichas. Las 86 portadas reales siguen teniendo prioridad; los metadatos ausentes continúan siendo `None`.

No se generaron imágenes con IA ni se añadieron dependencias. Se inspeccionó la ficha de «127 horas», cuya cubierta ilustrativa identifica a Aron Ralston, y su convivencia con las imágenes bibliográficas del catálogo. También se inició la aplicación nativa desde la tarea de escritorio. La automatización y las mediciones de cliente se realizaron en la vista web de los mismos controles, no en el ejecutable nativo.

## Base y condiciones

Se reutilizó la [fixture de volumen](../herramientas/catalogo_sintetico.py), en un archivo nuevo independiente. Contiene 100.000 obras, 120.000 ediciones, 2.000 autores, 110.000 autorías, 140.000 ejemplares y 183.333 asociaciones de clasificación. Incluye ediciones alternativas, coautorías, clasificaciones aprobadas/propuestas/rechazadas, copias dañadas/de baja y una sede inactiva. Los datos carecen de identidades OL inventadas. La preparación observada tomó 213,76 s; esa carga inicial no forma parte de las latencias de consulta.

El archivo lleva tipo `RENDIMIENTO`: tanto el inicio como el pie y los resultados muestran **datos sintéticos**, sin confundirlo con la demo de bibliografía real. Ni la aplicación normal ni el servidor de medición generan datos al abrirse. Demo y operativa conservan sus 100 obras, y la demo sus 150 ejemplares y cero socios ficticios.

Se utilizaron Python 3.14.8, Flet 1.0.5 y el navegador integrado Chrome 150/Electron 43, con viewport de 929 × 548 y escala 1. [Registro del servidor y versión de SQLite/plataforma](./mediciones_3b4/servidor.json). La sesión de consulta y el sistema de archivos estaban calientes; cada lectura SQLite abre una conexión propia, como la aplicación normal. No es una prueba de arranque frío ni un resultado universal para otros equipos.

## Método y límites de la medición

La [entrada instrumentada](../herramientas/medir_interfaz.py) utiliza los servicios/repositorios y la vista habituales. Añade observación en memoria únicamente en este servidor de prueba; el registro se exporta al desconectar. No cambia los eventos ni introduce SQL en Flet.

El [driver de cliente](../herramientas/medir_cliente.js) registra desde antes de escribir o seleccionar un filtro hasta que detecta el resultado esperado, espera dos `requestAnimationFrame` y completa una captura. Las búsquedas incluyen el debounce de 300 ms. Se verifican cantidades y fin de carga antes de capturar. La vista usa 24 obras por página; sólo se construye/renderiza la porción visible del cliente. La muestra incluye 35 recorridos: ocho calentamientos excluidos y 27 mediciones, tres por escenario. En paginación se recorren consecutivamente las páginas 2–4; no son repeticiones de un mismo OFFSET.

Se distinguen tres observaciones:

- **Backend:** duración real de `consultar_pagina`, incluida apertura/cierre de conexión, dentro del trabajador. Se toman las tres consultas correspondientes a las muestras posteriores al calentamiento.
- **Parche:** duración de `page.update()` al serializar/poner en envío la actualización. Mediana 4,14 ms; máximo 123,24 ms en los parches de resultados de esta sesión. Esto **no mide renderizado** ni confirma recepción del cliente.
- **Cliente:** tiempo observado hasta detectar semántica y hasta completar una captura después de dos frames. Incluye comunicación, controles, esperas de Playwright y la propia captura. Es una cota de observación del ensayo, no el instante exacto del primer píxel ni latencia física de una ventana de escritorio. Los relojes del navegador y del servidor no se restan entre sí.

## Resultados finales

Valores en milisegundos, mediana de tres muestras salvo la columna de máximo. [Muestras del cliente](./mediciones_3b4/cliente.json), [resumen](./mediciones_3b4/resumen.json).

| Escenario | Backend | Cliente: semántica detectada | Cliente: captura completada | Máximo de captura |
|---|---:|---:|---:|---:|
| Título original | 109,24 | 826,84 | 892,63 | 895,27 |
| Título de edición | 104,31 | 823,72 | 886,13 | 892,93 |
| Título de edición alternativa | 107,00 | 828,89 | 900,18 | 913,30 |
| Autor, 100 coincidencias | 121,34 | 825,55 | 888,28 | 901,45 |
| Sin resultados | 95,65 | 822,23 | 886,11 | 886,56 |
| Texto «sintético», 100.000 coincidencias | 2.702,63 | 3.341,32 | 3.410,36 | 3.421,82 |
| Género, 18.182 coincidencias | 770,28 | 1.368,88 | 1.430,63 | 1.475,67 |
| Disponibles en Norte, 15.824 coincidencias | 555,20 | 891,79 | 974,05 | 1.009,14 |
| Páginas siguientes sin búsqueda textual | 406,35 | 854,13 | 923,58 | 927,53 |

En disponibilidad local la sede ya estaba seleccionada al comenzar la muestra; se mide elegir «Disponibles». El escenario amplio busca un fragmento que coincide con títulos y todos los autores sintéticos. **No se afirma que toda consulta sobre 100.000 obras sea inferior a 500 ms:** el género y, especialmente, la búsqueda que devuelve todo superan esa referencia de backend usada en 2E. La aplicación prevista sigue teniendo 100 obras reales; se conservan estas limitaciones de escala explícitas, sin incorporar FTS5, caché avanzada o paginación por clave.

## Ajuste SQL justificado por el ensayo

El diagnóstico inicial de filtros encontró un cuello de botella concreto en **disponibilidad local**. El plan del `EXISTS` correlacionado elegía recorrer las copias libres/aptas de la sede para cada obra. El filtro de género no era la causa de ese producto, aunque las consultas amplias tienen su propio coste.

Se modificó sólo ese predicado en [ObraRepository](../biblioteca/repositorios/obra_repository.py): obtiene las identidades de obra disponibles con una subconsulta `IN`; «sin disponibles» utiliza `NOT IN`. `edicion.obra_id` es obligatorio, por lo que no introduce valores nulos que alteren la negación. Se preservan sede activa, propiedad igual a ubicación, situación libre, condición apta y filtrado antes de paginar. No se agregaron índices, migraciones ni tablas.

La [comparación controlada de conteo y planes](./mediciones_3b4/disponibilidad.json), sin filtro textual, interrumpió la formulación anterior a los 3.001,58 ms y completó la actual en 552,26 ms, devolviendo 15.824 obras. Es una observación acotada del `COUNT`, no una comparación de renderizado ni un factor de aceleración universal. Se conservan SQL y planes para revisar la inferencia.

La [prueba de regresión](../tests/test_medicion_interfaz.py) usa 1.000 obras y un presupuesto de 750.000 pasos de máquina virtual SQLite, independiente del reloj de CPU. Valida disponibles y su complemento: 159 y 841 obras. Los recorridos observados actuales necesitaron aproximadamente 140.000/175.000 pasos incluyendo la página y sus datos. Las 23 pruebas previas de búsqueda/stock siguen pasando, incluidas disponibilidad sobre varias ediciones, sedes inactivas y diferencias de propiedad/ubicación.

## Interactividad y resultados obsoletos

Se cambió de tema mientras la búsqueda amplia continuaba en SQLite: el navegador observó el cambio en 178,53 ms y aún mostraba carga. El registro del servidor confirma que el parche del cambio de tema ocurrió entre el inicio y el fin de esa consulta, sin retardo artificial. Esto demuestra que el ciclo gráfico puede atender otro evento durante la lectura; no sustituye una medición nativa en todos los sistemas.

Después se inició otra búsqueda amplia y se escribió «Original sintético 001234» mientras seguía pendiente. El resultado anterior de 100.000 coincidencias terminó, pero no se envió a la vista. La consulta nueva esperó el turno del único trabajador y mostró «Libro sintético 001234». Eventos 339–344 del registro: lectura anterior, nueva intención/carga, final anterior, inicio SQL nuevo, final nuevo y parche de una obra. Las lecturas siguen ejecutándose en serie; cancelar o reemplazar la espera no significa interrumpir SQLite.

[Observaciones del cliente](./mediciones_3b4/interactividad.json) y [script del ensayo](../herramientas/comprobar_interaccion.js). Las pruebas unitarias de 3B.3 también cubren errores tardíos, cierre/reconexión y cierre de fichas.

## Reproducir y continuar

```bash
# Destino nuevo; falla si ya existe, sin reemplazarlo.
python -m herramientas.medir_interfaz preparar \
  --base datos/generados/etapa3b4/sintetica.db --cantidad 100000

python -m herramientas.medir_interfaz servir \
  --base datos/generados/etapa3b4/sintetica.db \
  --registro datos/generados/etapa3b4/servidor.json --port 8552

python -m pytest -q
python main.py
```

También está la tarea **Horizonte: medición 3B.4**. La recolección automatizada del cliente usa Playwright provisto por el navegador integrado: habilitar accesibilidad, entrar a Catálogo, definir las funciones de los scripts y ejecutar `return await medirCliente(page);` y, después, `return await comprobarInteraccion(page);` con su objeto `page`. No se añadió Playwright como dependencia de la aplicación. Cerrar la página exporta el registro del servidor. El argumento opcional `--demora-ms` queda reservado a ensayos artificiales; en estos resultados fue **0**.

La suite completa terminó con **431 pruebas aprobadas** y los diagnósticos revisados no informaron errores. Se añadieron cinco pruebas de fixture/medición/regresión y se adaptó la prueba de portada faltante para la cubierta ilustrativa. No se certifica el comportamiento de futuras versiones de Flet ni de otros equipos.

Próximo incremento: **3C**, conectar socios, sedes e inventario mediante sus servicios; preparar socios de demostración sólo con una herramienta explícita. La siguiente prioridad funcional sigue siendo el préstamo interbibliotecario y su logística.
