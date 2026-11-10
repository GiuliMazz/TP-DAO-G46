# Etapa 3B.2 — Catálogo local y demo reproducible

Fecha: 4 de noviembre de 2026. Python 3.14.8. Incremento completado; conexión Flet pendiente de 3B.3.

## Resultado

| Contenido | Operativa | Demostración |
|---|---:|---:|
| Obras reales distintas por ID OL | 100 | 100 |
| Ediciones españolas | 100 | 100 |
| Identidades de autor OL | 87 | 87 |
| Sedes ficticias | 0 | 3 |
| Socios ficticios | 0 | 0 |
| Ejemplares ficticios | 0 | 150 |

Las dos bases se crean a partir del mismo [paquete bibliográfico](../datos/catalogo_local/README.md), sin copiar datos operativos de una base a otra. Los UUID son estables dentro de cada base; no se exige que coincidan entre bases independientes.

La demo tiene **50 ejemplares propios de Centro, 50 de Norte y 50 de Sur**, códigos DEMO-0001 a DEMO-0150. Inicialmente están aptos, libres y ubicados en su sede propietaria. Cada obra tiene al menos una copia; 50 tienen una segunda copia en otra sede. Todas las altas pasan por InventarioService. No se fabricaron préstamos, reservas, remitos ni estados logísticos.

Las salidas locales son [operativa.db](../datos/generados/catalogo_local/operativa.db), [demo.db](../datos/generados/catalogo_local/demo.db) y [catálogo auditable CSV](../datos/generados/catalogo_local/catalogo_auditable.csv). Sus identificadores de tipo se guardan junto a las bases. La muestra anterior de integración 2D conserva sus cinco obras y no fue modificada.

## Evidencia bibliográfica y calidad

La selección contiene **86 portadas de edición locales**. Ocho ediciones carecen de ISBN y catorce de referencia de portada; se conservan ausencias, sin inventar datos. Hay 23 descripciones originales de obra, que pueden estar en otro idioma; no se etiquetaron automáticamente como sinopsis española. Las descripciones y demás campos originales de edición quedan guardados en la evidencia.

Se reutilizaron las 30 respuestas detalladas históricas y las búsquedas previas. Se completaron ediciones mediante seis lotes de 25 candidatas; las respuestas se conservaron en la caché de preparación y no se repitieron al revisar la selección. La selección definitiva usa detalle Works+Search para 23 obras y Search para otras 77. El adaptador registra esta diferencia: no inventa respuestas de Works para estas últimas.

El [manifiesto](../datos/catalogo_local/seleccion.json) identifica cada pareja obra/edición, conserva URL y fecha conocida, verifica archivos por SHA-256 y referencia las imágenes locales. Las capturas históricas sin fecha conocida mantienen null. El CSV permite revisar título de obra, título de edición, autores con sus IDs, ISBN y enlaces a ambas páginas de Open Library.

Se apartaron **17 ediciones por revisión bibliográfica**, además de 16 candidatas con alertas técnicas/bibliográficas y dos rechazadas antes de completar las 100 seleccionadas. Las dudas incluyen créditos de traducción/ilustración/narración, autorías mezcladas, identidades homónimas repetidas, aparentes erratas y títulos/idiomas que requerían comprobación. Los motivos están en [revision_seleccion.json](../datos/catalogo_local/revision_seleccion.json); no son declaraciones de que esas obras no existan ni modificaciones de las fuentes.

No se afirma una auditoría humana exhaustiva de cada metadato. Las 100 candidatas cumplen los controles definidos y conservan evidencia verificable. Una edición española puede conservar un título comercial en inglés: se contrastó Riding the Bullet con su subtítulo Montado En La Bala, descripción española y portada de la edición. Se conservó el título informado por la fuente.

## Reutilización y responsabilidades

- [ValidadorCatalogoLocal](../biblioteca/importacion/validador_catalogo_local.py) incorpora OL-2-LOCAL como política versionada. Permite ISBN/portada ausentes, rechaza ISBN inválidos y mantiene controles de identidad, relación e idioma. Autorías homónimas repetidas quedan para revisión. Se conserva OL-1 como política por defecto del importador histórico.
- [FuenteCatalogoLocal](../biblioteca/importacion/fuente_catalogo_local.py) valida el manifiesto y las huellas, distingue capturas Search/Works y produce CandidatoOpenLibrary. No modifica archivos fuente ni accede a internet.
- [Preparador offline](../herramientas/preparar_catalogo_local.py) coordina ImportacionService, ClasificacionService, SedeService e InventarioService. Sólo el SQL de auditoría de esta herramienta verifica conteos/integridad; las altas no evitan servicios ni reglas del dominio.
- [Captura acotada](../herramientas/openlibrary/capturar_catalogo_local.py) es una herramienta de preparación: consulta lotes, reutiliza caché y descarga las portadas antes de ejecutar la aplicación. No pertenece al arranque de Flet ni a la reproducción de las bases. Rechaza sobrescribir una selección existente.

Se mantuvo el esquema operativo **6**, las cardinalidades, el contrato de prevalidación histórica y las entidades. La nueva política no cambia retroactivamente las evaluaciones OL-1: versión, evidencia, decisiones y correcciones siguen persistidas. Los campos opcionales ya estaban admitidos por el dominio.

Los géneros y etiquetas se procesan con las reglas existentes y materias originales. La categoría usada para una búsqueda no se incorpora como clasificación aprobada. Las decisiones humanas de clasificación conservan su prioridad.

## Reproducción y protección de datos

```bash
.venv/bin/python -m herramientas.preparar_catalogo_local
.venv/bin/python -m pytest -q
```

La preparación se ejecutó **sin habilitar acceso de red**, usando sólo los archivos locales. No crea una dependencia de Open Library en tiempo de ejecución. Las portadas inexistentes se representarán con una imagen neutra al conectar la interfaz.

Antes de escribir, se validan selección, política y ambos destinos. Se rechazan rutas iguales, enlaces al mismo archivo, bases ajenas sin identificador, tipos operativa/demo invertidos y otra selección de identidades. Los archivos tipo se conservan junto a cada SQLite. No hay una opción destructiva de reconstrucción ni se adoptan silenciosamente bases existentes.

Repetir conserva identidades, títulos corregidos, edición preferida, decisiones humanas y estado operativo de copias/sedes. Los códigos se basan en el orden estable por ID externo de edición. Una copia existente con otra edición/propietaria provoca un error explícito; no se reemplaza. Una sede renombrada o inactiva no se recrea ni reactiva.

Las altas se confirman por caso de uso. Si un proceso se interrumpe, puede quedar una preparación parcial identificada: se reanuda repitiendo el comando, sin borrar lo ya registrado. No se promete una transacción única que abarque ambos archivos SQLite y sus identificadores.

## Verificación

**410 pruebas aprobadas**, incluidas 29 nuevas de esta etapa. Se comprobaron ambas políticas, ausencia frente a dato inválido, autoría respaldada por Search, homónimos para revisión, alertas de títulos/idioma/relaciones, preservación de correcciones y decisiones humanas, huellas/rutas/identidades inválidas, separación de tipos de base, 150 códigos, sedes renombradas/inactivas y reproducción sin red. El paquete real de 100 obras también se verifica en la suite. [Pruebas](../tests/test_catalogo_local.py).

Se ejecutó además la preparación real dos veces: los UUID de obras, ediciones, autores, sedes y ejemplares quedaron idénticos. Las consultas 3B.1 devolvieron páginas de **24, 24, 24, 24 y 4 obras**, sin duplicados. La operativa informó cero disponibles; la demo, 150 copias disponibles en total y 50 obras con disponibilidad local por sede. `foreign_key_check` quedó vacío e `integrity_check` informó ok en ambas bases.

No se midió rendimiento de Flet ni se modificó su fuente de datos. La interfaz continúa con las seis obras y cuatro socios ficticios del prototipo hasta 3B.3. Las pruebas de escala de 100.000 obras sintéticas siguen disponibles y la medición completa acción–renderizado corresponde a 3B.4.
