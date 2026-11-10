# Open Library — Etapa 1 de preparación de catálogo

Este documento conserva el pipeline histórico de prevalidación. Para el catálogo inicial acotado del TP, usar el [paquete local de 100 obras](../../datos/catalogo_local/README.md) y el comando offline `python -m herramientas.preparar_catalogo_local`. La [captura acotada](./capturar_catalogo_local.py) se usó sólo para completar sus fuentes/portadas antes de generar las bases; no se ejecuta al abrir Flet ni al reproducir las SQLite. [Resultados de 3B.2](../../docs/ETAPA_3B_2_RESULTADOS.md).

## Objetivo

Reprocesar **offline** los archivos de las muestras ya obtenidas (1.000 obras exploratorias y 30 JSON originales), sin realizar llamadas nuevas a Open Library.

Esta etapa **no genera aún un catálogo final de 100.000 libros**. Deja una base normalizada con obras, ediciones candidatas, autores, géneros, etiquetas y materias originales; identifica los casos que deben revisarse antes de ampliar la importación.

## Archivos vigentes

- [ejecutar_etapa1.py](./ejecutar_etapa1.py): ejecución completa con un solo comando.
- [preparar_catalogo.py](./preparar_catalogo.py): normalización de la muestra de 1.000 y auditoría.
- [enriquecer_con_muestra_30.py](./enriquecer_con_muestra_30.py): aprovecha los JSON de edición completos de la primera muestra, sólo cuando la edición es exactamente la misma.
- [CONTRATO_PARA_UML.md](./CONTRATO_PARA_UML.md): contrato compartido con las actualizaciones de alcance/política identificadas; las cardinalidades se mantienen.
- [Salidas históricas locales](../../datos/openlibrary/prevalidacion/README.md): SQLite/CSV previos, excluidos de Git. Las pruebas regeneran su fixture en temporales y los comandos escriben en datos/generados.

## Ejecutar desde la raíz del proyecto

Con el entorno virtual activado, usar los insumos ya disponibles en [datos/openlibrary/](../../datos/openlibrary/):

- [catalogo_exploratorio.json](../../datos/openlibrary/catalogo_exploratorio.json) (muestra de 1.000).
- [respuestas_originales.json](../../datos/openlibrary/respuestas_originales.json) (JSON reales de la muestra de 30, opcional).

Ejecutar:

```bash
python herramientas/openlibrary/ejecutar_etapa1.py \
  --catalogo datos/openlibrary/catalogo_exploratorio.json \
  --detalles datos/openlibrary/respuestas_originales.json \
  --salida datos/generados/prevalidacion
```

No requiere instalar paquetes: usa sólo la biblioteca estándar de Python.

Si no se dispone de la muestra de 30, omitir `--detalles`.

La salida se genera aparte de la referencia conservada. Este pipeline reconstruye su base de salida: no usar como destino una base operativa ni una base con revisiones manuales que deban preservarse. Los resultados nuevos en datos/generados quedan fuera del control de versiones.

## Archivos de salida

- `catalogo_prevalidacion.db`: SQLite con entidades normalizadas, estados de edición y claves foráneas.
- `auditoria_prioritaria.csv`: hasta 100 candidatos ordenados por señales de revisión. Las alertas no prueban que el dato esté mal.
- `catalogo_resumido.csv`: vista simple con los 1.000 registros tal como se recibieron de la muestra exploratoria (el título de la tabla SQLite puede mejorar por fuentes originales).
- `informe_prevalidacion.md`: métricas y ejemplos.
- `metricas_prevalidacion.json`: métricas estructuradas.
- `errores_importacion.json`: problemas estructurales al leer la muestra.

Los CSV usan `;` como separador y UTF-8 con BOM para facilitar su apertura en software de planillas con configuración regional española.

## Estado de los datos

Con los archivos proporcionados se obtuvieron 1.000 obras, 1.000 ediciones candidatas, 993 autores y 10.987 materias originales distintas (después de compactar espacios de las materias).

Siete ediciones coincidieron exactamente con los JSON completos de la muestra anterior. Pudimos incorporar datos específicos de esas siete: idioma registrado, ISBN con suma de control válida, editorial y portada de edición. **ENRIQUECIDA no significa VALIDADA**: no se completó una auditoría humana ni la revisión a escala.

Se detectaron 214 obras con al menos una alerta heurística y se creó una auditoría priorizada de 100. Un título corto como `Nada` no es necesariamente incorrecto: estas señales requieren interpretación, no rechazo automático.

## Integración en la aplicación (incremento 2D)

La aplicación ya dispone de un adaptador que lee esta salida y los JSON originales en modo de sólo lectura. Su política OL-1 evalúa controles y alertas, y guarda decisiones en una **base operativa separada**. Sobre la muestra actual integra cinco obras/ediciones, deja dos para revisión bibliográfica y 993 pendientes de detalle. No cambia el estado de esta referencia ni reconstruye el catálogo operativo. Ver [comando y reglas](../../README.md#integrar-la-muestra-real-de-open-library) y [resultados de 2D](../../docs/ETAPA_2D_RESULTADOS.md).

## Ampliación futura mediante dumps

Estas opciones no reemplazan el [plan vigente](../../PLAN_DESARROLLO.md): alcanzar 100.000 obras reales no es una condición de entrega. Los dumps sólo se evaluarán si hace falta ampliar los datos después de estabilizar la integración.

1. Construir un importador por flujo del dump de ediciones (`/type/edition`) y filtrar `languages: /languages/spa`, ISBN y portadas específicas.
2. Relacionar cada edición con su `works` (ID de obra) y elegir candidatos representativos sin duplicar obras.
3. Completar atributos de obra, autores y materias desde los dumps de obras y autores.
4. Aplicar normalización de géneros/etiquetas con evidencias y controles de calidad. Revisar primero los casos de auditoría.
5. Generar un catálogo final para SQLite separado del inventario físico administrado por la aplicación.

No extraer 100.000 libros mediante cientos o miles de solicitudes individuales a la API. Open Library solicita utilizar sus dumps para acceso masivo.

- https://openlibrary.org/developers/dumps
- https://openlibrary.org/developers/api
- https://openlibrary.org/dev/docs/api/search
