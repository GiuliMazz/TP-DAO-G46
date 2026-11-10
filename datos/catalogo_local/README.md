# Catálogo local de Horizonte — selección 1

Paquete bibliográfico de 3B.2: **100 obras reales, 100 ediciones españolas y 87 identidades de autor de Open Library**, con 86 portadas de edición guardadas. Estos archivos no contienen ejemplares, socios ni sedes ficticios. No son la SQLite operativa ni una nueva versión de la base histórica de prevalidación.

## Contenido y evidencia

- [seleccion.json](./seleccion.json): identidades de las 100 obras/ediciones, política OL-2-LOCAL, huellas SHA-256 de los archivos, portadas disponibles y exclusiones durante la selección.
- [fuentes/busquedas.json](./fuentes/busquedas.json): documentos Search originales seleccionados, con URL y procedencia de la captura previa. La fecha de descarga histórica desconocida se conserva como null.
- [fuentes/ediciones.json](./fuentes/ediciones.json): JSON originales de cada edición; se reutilizaron fichas anteriores y se completaron mediante Books API por lotes. Se conserva URL/fecha de las capturas nuevas y huella del lote.
- [fuentes/obras.json](./fuentes/obras.json): 23 detalles de Works previamente disponibles. Para las otras 77 obras se usa explícitamente evidencia de Search; no se presentan proyecciones como respuestas originales de Works.
- [revision_seleccion.json](./revision_seleccion.json): 17 ediciones apartadas por dudas bibliográficas. No son rechazos definitivos ni correcciones silenciosas de Open Library.
- [portadas/](./portadas/): 86 JPEG obtenidos mediante la referencia de portada de cada edición. No se usa una portada de obra para fingir que corresponde a su edición española.

Las 100 candidatas superan controles de identidad, relación edición–obra, autoría de la obra e idioma español. Ocho ediciones no tienen ISBN; catorce no tienen referencia de portada. La ausencia se guarda como None, sin rellenar datos ficticios. Hay 23 descripciones originales de obra; pueden estar en otro idioma. Los demás campos y descripciones presentes en las respuestas originales siguen disponibles en la evidencia, sin etiquetarlos automáticamente como sinopsis española.

El título de Obra es el que informa Open Library; no se afirma haber investigado el idioma o la forma editorial original de cada título. Tampoco se certifica una revisión bibliográfica humana exhaustiva: se conserva evidencia y se apartaron los casos señalados. Por ejemplo, una edición española puede conservar un título comercial en inglés: Riding the Bullet (OL9893797M) indica español, subtítulo Montado En La Bala, ISBN 9788484504887 y portada española coincidente. No se reemplazó su título sin registrar una decisión.

## Reproducir las bases sin red

Desde la raíz del proyecto, con el entorno virtual activado:

```bash
python -m herramientas.preparar_catalogo_local
```

Genera o completa:

- [operativa.db](../generados/catalogo_local/operativa.db): las 100 obras/ediciones reales, sin datos operativos ficticios.
- [demo.db](../generados/catalogo_local/demo.db): la misma bibliografía y 150 ejemplares DEMO, con 50 propios de Centro, Norte y Sur.
- [catalogo_auditable.csv](../generados/catalogo_local/catalogo_auditable.csv): informe derivado de títulos, autores/IDs, ISBN, portadas y enlaces. No es la fuente de las altas.

Los JSON tipo de base que acompañan a las SQLite deben conservarse junto con ellas. Impiden invertir destinos o usar una base existente ajena al preparador. No usar este comando sobre una base personal sin esa identificación. Repetir conserva UUID, títulos corregidos, preferencias y decisiones humanas; no restablece condición, baja, ubicación ni habilitación de sedes.

Cada alta de ejemplar pasa por InventarioService; no se simulan préstamos/remitos ni se crean estados mediante SQL. La operativa y la demo se integran por separado a partir de los mismos insumos; sus UUID pueden diferir entre bases y son estables dentro de cada una. El plan de copias se ordena por ID externo de edición para que reordenar el manifiesto no cambie los códigos.

Los archivos de salida están ignorados por Git y pueden regenerarse. Los insumos de esta carpeta se conservan para permitir una reproducción sin internet. La aplicación Flet usa estas bases desde 3B.3. En 3C se añadió administración de socios/sedes y alta física de ejemplares. Para incorporar los ocho socios ficticios a la demo, ejecutar explícitamente `python -m herramientas.preparar_socios_demo`; no modifica la operativa ni se ejecuta al iniciar Flet.

## Captura y futuras correcciones

La [herramienta de captura](../../herramientas/openlibrary/capturar_catalogo_local.py) usa biblioteca estándar, lotes acotados, respuestas previas y un intervalo de al menos 1,1 segundos entre solicitudes nuevas. Se ejecutó para preparar esta selección; no forma parte del arranque ni de la reproducción offline. Rechaza sobrescribir una selección ya existente. La caché de captura y las imágenes de borradores descartados quedan en datos/generados, fuera de los insumos vigentes.

No editar una captura para arreglar un dato: invalidaría su huella y borraría la distinción entre evidencia y corrección. Los casos dudosos se revisan con ImportacionService; los cambios del catálogo ya integrado se realizan con CatalogoService. Reimportar conserva las decisiones y correcciones existentes. Una nueva selección de identidades requiere una preparación separada, sin reemplazar una base en uso.

Referencias oficiales: [API y pautas](https://openlibrary.org/developers/api), [Search](https://openlibrary.org/dev/docs/api/search), [Books API por lotes](https://openlibrary.org/dev/docs/api/books) y [portadas](https://openlibrary.org/dev/docs/api/covers).
