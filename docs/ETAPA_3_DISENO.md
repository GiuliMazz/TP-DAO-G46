# Etapa 3 — Interfaz Flet incremental

## Decisión acordada

Aplicación de escritorio para personal de la Red de Bibliotecas Horizonte. Estética clara: fondo gris suave, superficies blancas, azul petróleo, menú lateral, sede de trabajo en cabecera y formularios en diálogos. Catálogo visual por obra, administración compacta con tablas. Se adopta la propuesta de ChatGPT pegada por el usuario; las imágenes anteriores son referencias de distribución, no una obligación de usar tema oscuro.

Actualización acordada: se añadió selector claro/oscuro sin perder estado de navegación. El catálogo real inicial se acota a unas 100 obras con edición española; la demo tendrá 150 copias ficticias en base separada, conservando 100.000 sintéticas para escala. La secuencia detallada y la nueva política local prevista constan en [diseño de 3B](./ETAPA_3B_DISENO.md). [Resultados del modo oscuro y 3B.1](./ETAPA_3B_1_RESULTADOS.md).

## Incrementos

| Incremento | Resultado | Verificación |
|---|---|---|
| 3A — Prototipo visual | Inicio, catálogo y socios navegables; filtros, cambio de vista, ficha y formulario de muestra; datos de demostración sin persistencia | Construcción con Flet instalado, interacción y redimensionamiento; ninguna lectura/escritura de bases operativas |
| 3B — Catálogo conectado | Paginación SQLite, buscador único original/español/autor, género/sede/disponibilidad, ficha/portada de edición y disponibilidad | Filtros antes de LIMIT, una obra por resultado, metadatos de página en consultas acotadas, errores y respuesta no bloqueante |
| 3C — Administración conectada | Socios, sedes y alta explícita de ejemplares mediante servicios, con formularios | Validaciones de negocio existentes, cambios persistentes, habilitación/baja, refresco y navegación sin perder contexto |

El primer incremento no implementa préstamos, reservas, remitos ni reportes. Se indican como próximos módulos; no se simulan como operaciones disponibles. La sede del encabezado es contexto de trabajo, sin convertir socios/catálogo de la red en datos exclusivos de esa sede.

## Responsabilidades de 3A

- AplicacionHorizonte: composición visual, navegación, contexto de sede y ciclo de eventos.
- InicioView: resumen de los datos de muestra y accesos a catálogo/socios. Indicadores de circulación futuros se presentan como próximos, no ceros inventados.
- CatalogoView: controles de búsqueda, filtros, cuadrícula/tabla, página de 24 y diálogo de obra. Una tarjeta representa una obra; las cubiertas locales se señalan como ilustrativas.
- SociosView: tabla, búsqueda/filtro y vista previa de formulario. La acción del diálogo no registra un socio real ni reimplementa validaciones del dominio.
- DatosPrototipo: conjunto estático, explícitamente ficticio y separado de servicios/repositorios. No constituye otro modelo de negocio.
- Tema/componentes: estilos, encabezados y etiquetas compartidos.

No se introduce SQL ni reglas de préstamo en vistas. Los cambios de un formulario de muestra se descartan; se explica junto a la acción. La validación real y persistencia se incorporan en 3C usando los servicios existentes.

## Preparación para datos reales

En 3B, consultas bloqueantes se ejecutarán fuera del ciclo de interfaz con un ejecutor acotado. Cada trabajador crea y cierra su propia conexión SQLite. Debounce aproximado de 300 ms y número de revisión de búsqueda impedirán mostrar resultados obsoletos; cancelar una tarea no se asumirá como cancelación efectiva de un hilo/consulta ya iniciada. En 3A sólo hay filtros sobre una muestra pequeña en memoria y no se crea un ejecutor sin operaciones que lo necesiten.

La búsqueda única debe combinar título original, ediciones españolas y autor con OR. Los filtros actuales título/autor separados combinan AND: no se unirán páginas en la vista para fingir búsqueda global. Sede/disponibilidad y portada en ficha de página se añadirán a consultas de backend por necesidad funcional, preservando reglas y evitando una consulta por tarjeta.

La paginación y construcción gráfica diferida son distintas. Se mostrarán 24 obras por página y se usará GridView con build_controls_on_demand. Caché, keyset y FTS quedan sujetos a mediciones de la interacción conectada. No es requisito importar 100.000 obras reales antes de construir las pantallas.

## Dependencias y comprobaciones

Flet 1.0.5 y su cliente desktop se fijan como dependencias de ejecución. flet-web se limita a una dependencia opcional de verificación local: el mismo código puede abrirse en navegador cuando el agente no dispone de acceso gráfico completo. No se incorpora Flutter SDK ni otra herramienta de diseño.

Referencias oficiales consultadas: [instalación](https://flet.dev/docs/getting-started/installation/), [ejecución desktop/web](https://flet.dev/docs/getting-started/running-app/), [GridView](https://flet.dev/docs/controls/gridview/) y [AlertDialog](https://flet.dev/docs/controls/alertdialog/). Las APIs se contrastan también con la instalación local. Las pruebas de construcción no sustituyen verificar el renderizado y los clics en un cliente Flet.
