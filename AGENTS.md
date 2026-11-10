# Continuidad para agentes y colaboradores

## Estado del proyecto

TP de Desarrollo de Aplicaciones con Objetos, grupo 46: **Red de Bibliotecas Horizonte**.
Leer primero [README](./README.md), [plan](./PLAN_DESARROLLO.md) y los documentos de la etapa que se trabajará.

- Implementado: etapas 0–3, incluido [3C.1](./docs/ETAPA_3C_1_RESULTADOS.md): catálogo, socios, sedes e inventario con condición física y baja en Flet.
- Verificación de referencia: 455 pruebas, Python 3.14.10, Flet 1.0.5, esquema SQLite 6.
- [Etapa 4](./docs/ETAPA_4_DISENO.md) y [UML](./docs/UML_ETAPA_4.md): **propuestas pendientes de revisión**, no implementadas. Los 14 días de préstamo, cancelación manual y AsignacionEjemplar no están acordados por el solo hecho de estar documentados.
- Siguiente trabajo: revisar ese diseño con el equipo antes de implementar circulación. Mantener prevista Strategy para local/interbibliotecario y State para remitos; no crear patrones vacíos anticipadamente.

## Forma de trabajo acordada

1. Antes de cada módulo, explicar requerimientos, clases, responsabilidades, relaciones y decisiones relevantes.
2. Implementar sólo el incremento autorizado, con orientación a objetos y entidades con comportamiento.
3. Incorporar pruebas de negocio e integración donde corresponda y verificar antes de continuar.
4. Explicar cualquier cambio de decisión previa antes de aplicarlo. Distinguir consigna, acuerdos y propuestas.

## Arquitectura y reglas

- Dominio: entidades y comportamiento, sin SQLite ni Flet.
- Servicios: coordinar casos de uso y transacciones; repositorios: SQL parametrizado y reconstrucción.
- Interfaz: capturar/presentar datos, sin SQL ni reglas de negocio duplicadas.
- Cada operación usa su propia conexión en el hilo que la crea; repositorios de un caso comparten conexión. No anidar transacciones de servicios.
- Lecturas y guardados no bloquean Flet. Conservar debounce, descarte de resultados obsoletos, límite de trabajadores y protección de doble envío. Cancelar una espera no cancela un comando ya aceptado.
- Obra, Edicion y Ejemplar son conceptos diferentes. Catálogo paginado desde SQLite, buscando título original, títulos españoles y autor antes de LIMIT.
- Propietaria estable; ubicación variable. Un traslado no transfiere propiedad. Disponibilidad exige condiciones físicas/operativas y sede activa coherentes.
- Socios identificados por DNI único en toda la red; no agregar otros documentos ni asociación obligatoria Socio–Sede.
- No cambiar el [contrato del importador](./herramientas/openlibrary/CONTRATO_PARA_UML.md) ni modificar capturas/huellas para corregir metadatos.
- No agregar frameworks, dependencias, patrones u optimizaciones sin necesidad demostrada. Las migraciones son explícitas; el arranque no prepara ni siembra bases.

## Entorno y comprobaciones

Usar un entorno virtual de Python 3.14 e instalar requirements-dev.txt. Comandos desde la raíz:

```bash
python -m pytest -q
python -m herramientas.preparar_catalogo_local
python -m herramientas.preparar_socios_demo
python main.py
```

El primer comando reconstruye su muestra histórica en un directorio temporal: no necesita bases previas ni red. Los dos preparadores siguientes son explícitos y offline; la demo queda con 100 obras reales, 150 copias y ocho socios ficticios. La operativa sólo recibe bibliografía. Preservar marcas de tipo junto a las bases locales.

Portadas/capturas verificables viven en datos/catalogo_local y sí se versionan. Bases, cachés, entornos y salidas generadas quedan fuera de Git. Las 100.000 obras son una carga sintética de rendimiento que se genera a demanda, no un requisito de importar más libros reales.

No usar ZIP, cachés ni extractores antiguos del archivo local como punto de partida. Los DOT históricos se conservan como referencia; los UML vigentes están en docs. Consultar [colaboración y publicación](./docs/COLABORACION.md) para reproducir un clon y preparar cambios para GitHub.
