# Incremento 2A — Núcleo bibliográfico

Fecha: 3 de noviembre de 2026. Estado: implementado y verificado; 2B–2E pendientes.

## Resultado funcional

Se implementaron [Autor](../biblioteca/dominio/autor.py), [Obra](../biblioteca/dominio/obra.py) y [Edicion](../biblioteca/dominio/edicion.py), sus repositorios y [CatalogoService](../biblioteca/servicios/catalogo_service.py). Se mantiene la separación de dominio, SQL y casos de uso de etapa 1.

El servicio permite registrar/corregir autores, obras y ediciones, registrar obra y primera edición de forma atómica, obtener detalle, seleccionar edición preferida y consultar obras/autores/ediciones con páginas acotadas.

### Búsqueda y presentación

- Buscar por fragmentos del título original y de cualquier edición española, incluso una no seleccionada.
- Mostrar preferentemente el título de la edición española seleccionada, manteniendo el original por separado. La primera edición registrada queda seleccionada; cambiarla no cambia la obra ni la identidad de la edición.
- Usar respaldo reproducible si existe edición pero no selección: la española de menor UUID. Sin edición, el detalle administrativo conserva el título original y la obra no aparece todavía en el listado utilizable.
- Devolver una ficha por obra, sin multiplicarla por sus autores o ediciones. Los filtros de título y autor pueden combinarse.
- Conservar acentos y contenido; comparar con casefold y espacios compactados, sin búsquedas aproximadas ni eliminación de acentos. Los filtros son literales, no patrones SQL.

El caso de Terramar se usa como ejemplo de búsqueda, sin atribuir ISBN, portada ni datos de una edición real a los fixtures. En la demostración, las búsquedas por «Mago de Terramar», «Wizard» y el título español alternativo encuentran la misma obra.

### Identidad, datos opcionales y duplicados

UUID local estable e ID OL opcional y único por tipo. Títulos/autores homónimos no se fusionan. Una coincidencia exacta de título y autoría se comunica como PosibleDuplicado; la confirmación explícita de que es distinta sólo omite esa alerta, nunca la unicidad del ID OL.

Los ISBN son opcionales para registros manuales. Cuando se proporcionan se normalizan y validan; el equivalente 13 del ISBN-10 sirve para detectar coincidencias entre ambos formatos. Si se proporcionan los dos deben corresponder. La coincidencia requiere revisión y puede confirmarse explícitamente como edición distinta; no se usa el ISBN como identidad de la obra ni se impone unicidad bibliográfica absoluta.

Los datos opcionales ausentes se conservan como None. No se inventan portadas, páginas o sinopsis. Años, páginas e IDs de portada requieren enteros positivos y no aceptan booleanos. Las descripciones conservan sus párrafos.

Las reglas de formato/control ISBN se contrastaron con la [explicación de la Agencia Internacional del ISBN](https://www.isbn-international.org/index.php/content/what-isbn/10) y su [aclaración sobre prefijos 979](https://www.isbn-international.org/node/331): ISBN-13 con prefijo 978/979 y control módulo 10, y sin convertir ISBN 979 a ISBN-10. El cálculo no verifica asignación editorial ni autenticidad del registro.

No hay atributos PENDIENTE/ENRIQUECIDA/VALIDADA en la entidad Edicion ni un método de aprobación del importador en el servicio de catálogo.

## Persistencia

Se agregó la [migración 002](../biblioteca/persistencia/migraciones/002_catalogo.sql) con autor, obra, obra_autor y edicion, IDs externos únicos, claves foráneas e índices para relaciones y consultas. La preferida se referencia con (edicion_preferida_id, obra.id) → (edicion.id, edicion.obra_id), impidiendo elegir una publicación de otra obra también a nivel de base.

El [ejecutor](../biblioteca/persistencia/base_datos.py) aplica las versiones pendientes en orden. La actualización versión 1 → 2 conserva los datos de sedes y socios; un fallo revierte DDL y versión, y permite reintentar. Se conserva el rechazo de bases ajenas sin versión y de versiones futuras.

Todos los repositorios de un CatalogoService deben compartir conexión. Sus escrituras se confirman juntas. No se agregaron eliminaciones físicas ni transferencias de propiedad.

## Verificación ejecutada

Entorno: Python 3.14.8 y pytest 9.2.0 del entorno virtual existente. Sin dependencias nuevas.

```bash
python -m pytest -q tests/test_bibliografia.py tests/test_catalogo.py tests/test_migraciones_catalogo.py
```

Resultado focalizado: **81 casos aprobados**.

```bash
python -m pytest -q
```

Resultado completo: **162 passed in 0.31s**, código 0. Incluye los 81 casos anteriores; los conteos incluyen parametrizaciones.

| Archivo | Evidencia |
|---|---|
| [test_bibliografia.py](../tests/test_bibliografia.py) | ISBN-10/13 y X, entradas inválidas que no deben arreglarse eliminando letras, pares incompatibles, campos opcionales/números/idioma/IDs OL, identidad y cambios atómicos |
| [test_catalogo.py](../tests/test_catalogo.py) | Terramar por original y ediciones españolas; preferencia persistida; homónimos y duplicados; filtros/páginas; alta conjunta y rollback tras inserción; relectura; claves foráneas y ausencia de inventario |
| [test_migraciones_catalogo.py](../tests/test_migraciones_catalogo.py) | Base real de esquema 1 con datos → esquema 2, conservación íntegra, repetición y fallo recuperable de la segunda migración |

La prueba de listado observó dos consultas SELECT para una página de varias obras: consulta de fichas y autores en lote; no una consulta de autoría por cada ficha. Esto no sustituye una medición de rendimiento con 100.000 obras, que sigue en 2E.

Se ejecutaron ambas demostraciones con código de salida 0:

```bash
python -m biblioteca.demo
python -m biblioteca.demo_catalogo
```

La primera conserva el recorrido de sedes/socios. La segunda verifica búsqueda de la misma obra por tres títulos y selección de otra edición persistida tras reabrir. Usan bases temporales y no modifican datos reales. El editor no informó problemas en el código y pruebas consultados.

## Ajustes acordados para los siguientes incrementos

- **2B y circulación:** conservar propiedad y ubicación separadas. Un ejemplar recibido en otra sede sigue asignado a la solicitud original; entregar ese ejemplar no es asignarlo a una nueva solicitud.
- **2C:** permitir aprobación automática de correspondencias confiables, con materia, regla/versión, método y motivo; ambiguas siguen propuestas y decisiones humanas prevalecen. Público destinatario tiene su asociación propia, separado de género y etiqueta.
- **2D:** distinguir controles técnicos automáticos, alertas bibliográficas y auditoría humana selectiva. Permitir aceptación automática por política trazable sin revisar individualmente todas las obras. El contrato conserva IDs/cardinalidades/estados; se aclaró su significado y se diseñarán campos técnicos antes de implementar esa fase.
- **Objetivo de datos:** aproximadamente 100.000 obras distintas mediante procesamiento automatizado, sin afirmar que se hayan importado ni promover los resultados existentes por cambiar la política.

No se descargaron dumps ni se aplicó aceptación automática sobre la muestra. Los casos reales siguen con siete ediciones ENRIQUECIDA y 993 PENDIENTE. La próxima implementación es sólo 2B, tras revisar su diseño detallado.
