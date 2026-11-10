# Incremento 2D — Aceptación e integración de Open Library

## Alcance antes de implementar

Se conserva el [contrato externo](../herramientas/openlibrary/CONTRATO_PARA_UML.md). La base de preparación y los JSON originales se leen sin modificarlos; la aplicación registra evaluaciones, decisiones e integración en su propia SQLite. No se ejecuta el pipeline que reconstruye bases sobre un destino operativo.

La muestra observada contiene 1.000 obras/ediciones y siete ENRIQUECIDA. Los JSON completos disponibles permiten contrastar exactamente esas siete ediciones; no se atribuye a una edición el detalle de otra. Las otras 993 necesitan información adicional. Hay dos señales concretas de revisión: título breve Mort, y title=Meow frente a full_title=Haunting Adeline Nunca te dejaré. Las señales no prueban un error ni autorizan a inventar la corrección.

## Responsabilidades

| Componente | Responsabilidad |
|---|---|
| FuenteOpenLibrary | Leer por flujo la SQLite de preparación en modo de sólo lectura; resolver detalles JSON por ID exacto, conservando el registro original. |
| CandidatoOpenLibrary | Instantánea técnica de obra, edición, autores, materias y detalle; no es una entidad de circulación. |
| ValidadorOpenLibrary | Comprobar identidad, relaciones, autoría de obra, idioma de edición, ISBN y portada propia. Separar faltantes, contradicciones y alertas bibliográficas. |
| ImportacionRepository | Persistir evaluaciones con huella/política, historial de decisiones y correspondencia con la edición local; consultas paginadas. |
| ImportacionService | Evaluar/revisar/integrar, controlar duplicados y coordinar repositorios en una transacción por integración. |
| ProcesadorMaterias | Compartir el procesamiento ya implementado en 2C, sin iniciar una transacción propia, para integrar clasificación con el catálogo. |

Autor, Obra y Edicion conservan sus responsabilidades y UUID. Los estados PENDIENTE/ENRIQUECIDA/VALIDADA/RECHAZADA permanecen en importación. No se añade State a este proceso ni otra dependencia.

## Política inicial

1. ID OL correcto para cada tipo y vínculos de la edición con su obra coherentes entre preparación y detalle original.
2. Autores identificados por ID de la obra original y nombres disponibles; no incorporar traductores/ilustradores de la edición como autores de obra. Discrepancias requieren corregir la fuente o revisar, nunca inventar identidades.
3. Español declarado en el JSON exacto de la edición; un indicador de Search API o idioma_verificado de la preparación no sustituye esa evidencia.
4. Al menos un ISBN con formato/control válido y una portada positiva de la edición. No usar portada de obra como sustituto. Las portadas sólo se comprueban como referencias, sin afirmar accesibilidad ni corrección visual.
5. Datos opcionales ausentes no impiden aceptar. Fechas textuales complejas y descripciones sin idioma acreditado se conservan en evidencia sin adivinar año o español.
6. Incompleto queda PENDIENTE; una contradicción objetiva queda RECHAZADA; técnicamente completo con alertas queda ENRIQUECIDA para revisión; completo sin alertas queda VALIDADA por política automática versionada.
7. Revisión manual puede aprobar alertas bibliográficas, con motivo y corrección explícita de título, pero no omitir controles técnicos. Un rechazo humano se preserva ante nuevas evaluaciones.
8. Una nueva instantánea no hereda silenciosamente una aprobación humana de otra instantánea: la decisión conserva la evidencia que se aprobó. El nuevo material queda registrado para revisar diferencias.

## Integración y conservación

- Resolver autor/obra/edición por ID OL; crear UUID sólo para identidades nuevas. No fusionar por nombres o títulos.
- Detectar posibles duplicados de título/autores e ISBN contra el catálogo, con confirmación explícita de registro distinto cuando corresponda. Una edición existente no puede reasignarse a otra obra.
- Reimportar no modifica metadatos, autoría ni edición preferida ya existentes. Esta política conservadora protege correcciones manuales sin exigir identificar cada campo editado. Completar/corregir registros existentes seguirá siendo una acción explícita; las versiones nuevas de la fuente quedan en evidencia.
- Guardar nuevas entidades, preferencia inicial, materias y asociaciones en una transacción. Un fallo de clasificación no deja un libro importado a medias. Evaluar es una acción durable independiente: un conflicto posterior de integración no borra la auditoría.
- Usar únicamente las reglas explícitas de 2C; las categorías y clasificaciones exploratorias no se promueven automáticamente. Conservar materias fuente y revisiones humanas de clasificación.
- No crear ni modificar ejemplares, sedes, socios ni operaciones. Rechazar una fuente posteriormente no elimina registros operativos existentes; las correcciones del catálogo se realizan explícitamente.

## Verificaciones previstas

Pruebas de controles técnicos, datos malformados y alertas; títulos Meow/Mort; muchos autores; materias compuestas y ciencia/ciencia ficción sin herencia ciega; aprobación/rechazo humano; cambios de fuente/política; duplicados; varias ediciones de la misma obra; conservación de UUID/correcciones/preferencia; rollback completo; reconstrucción tras reabrir; migración desde esquema 4 y protección de inventario/clasificación.

Finalmente se procesará la muestra real offline hacia un destino nuevo separado, se repetirá la integración y se medirán los resultados efectivos. No se afirma de antemano cuántas ediciones serán aceptadas ni rendimiento con 100.000 obras.
