# Revisión de la muestra bibliográfica — 4 de noviembre de 2026

Se recorrieron las [20 fichas visuales](./auditoria_visual.html), sus metadatos locales y las 17 cubiertas disponibles. La muestra es intencional: 3 obras cuentan además con respuesta Works y 17 sólo con Search más el detalle de edición. **No** se certifica la exactitud bibliográfica completa ni se contrasta físicamente un ISBN con un ejemplar. Los enlaces permiten continuar la revisión humana. No se hicieron nuevas capturas de Open Library ni se modificaron los originales.

## Cobertura y reglas

Antes de la ampliación había 17 obras con género aprobado, 0 con etiquetas y 16 con público. Ahora hay **53, 26 y 16**, respectivamente; [distribución completa](./COBERTURA.md). Las cantidades de términos no se suman como si fueran obras distintas. Hay 47 obras sin género aprobado, 74 sin etiquetas y 84 sin público; no se exige clasificar toda obra de no ficción dentro de géneros narrativos ni se deduce público adulto por omisión.

Se agregaron 19 correspondencias automáticas exactas para géneros y temas, además de tres propuestas. Se normaliza espacio/mayúsculas, sin buscar subcadenas. Ejemplos: `Fiction, science fiction, general` → Ciencia ficción; `Historical fiction` → Novela histórica; `Dragons` → etiqueta Dragones. `Fantasy`, `History`, `Biography` y categorías comerciales mixtas no producen géneros automáticamente. El contexto de crítica/adaptación conserva propuestas y la decisión humana prevalece. `Juvenile fiction`/`Juvenile literature` se mantienen como propuestas: abarcan niños y adolescentes. `Science fiction` genérico también queda propuesto tras detectar materias cruzadas en *El castillo de cristal* (abundan biografía y memorias junto a esa materia). Sus reglas versión 2 conservan la trazabilidad de la primera evaluación; las cuatro reglas históricas no cambian.

Una correspondencia exacta es verificable, pero no garantiza que la materia original sea correcta o específica de la edición. Ejemplos detectados: *El ojo del mundo* tiene materias que originan Ciencia ficción (ahora propuesta) e Infantil; *Yo, Robot* tiene Infantil. Se señalan para revisión, sin sustituirlas por una opinión ni afirmar una recomendación de edad. Para el TP se conserva la trazabilidad y no se persigue una cobertura artificial del 100 %.

## Recorrido visual

| Nº | Obra / evidencia | Observación |
|---:|---|---|
| 1 | El ojo del mundo / Works | Título y Robert Jordan visibles en cubierta; año no informado. Revisar género secundario y público derivados de materias. |
| 2 | El Hobbit / Works | Cubierta española con Tolkien; edición e ISBN presentes. |
| 3 | Buenos Presagios / Search | Se ven Pratchett y Gaiman; se conservan ambos autores, sin reducir la coautoría. |
| 4 | Yo, Robot / Search | Título y Asimov visibles; año no informado. Público Infantil requiere revisión bibliográfica. |
| 5 | Horrorstör / Search | Cubierta española, autor y título coherentes con la ficha. |
| 6 | La casa torcida / Search | Título y Agatha Christie visibles; Policial sigue propuesto por contexto crítico, Juvenil es propuesta. |
| 7 | Un mundo sin fin / Search | Cubierta de muy bajo contraste; no permite dar por comprobados visualmente título/autor. Conservar como caso de revisión de imagen. |
| 8 | Tal vez mañana / Search | Título y Colleen Hoover visibles; amistad queda separada del género Romance. |
| 9 | El ladrón del rayo / Works | Título y Riordan visibles; Fantasía permanece propuesta por contexto, no se fuerza aprobación. |
| 10 | El jardín secreto / Search | Título y Burnett visibles; sólo ISBN-10 disponible. No inventar ISBN-13 en el registro. |
| 11 | Don Quijote / Search | Cubierta histórica con título y Cervantes; ISBN ausente válido. El año proviene del registro, no se verifica por cubierta. |
| 12 | Fin de la Muerte / Search | La cubierta dice «El fin de la muerte» y «Cixin Liu»; ficha OL conserva título bilingüe y nombre en escritura china. Candidata a normalización editorial documentada, sin alterar identidad. |
| 13 | Riding the Bullet / Search | Cubierta con King y subtítulo español «Montado en la bala»; título comercial inglés no implica edición inglesa. Año ausente. |
| 14 | Fun Home / Search | Cubierta española con Alison Bechdel y subtítulo «Una familia tragicómica»; año ausente. |
| 15 | El capital en el siglo XXI / Search | Título y Thomas Piketty visibles; no se fuerza un género de ficción para esta obra. |
| 16 | El cerebro de Broca / Search | Título y Carl Sagan visibles; Ciencia es etiqueta, no género. |
| 17 | El asombroso libro del interior de las cosas / Search | Título visible; autor no legible en esta miniatura, requiere contraste adicional. ISBN-10 presente. |
| 18 | 127 horas / Search | Sin portada: se auditan los metadatos, no se certifica cubierta. |
| 19 | Química general / Search | Sin portada ni ISBN; no se completan por conjetura. |
| 20 | Momentos de vida / Search | Sin portada; ISBN-10 presente, año y autora conservados del registro. |

No se detectó en esta muestra una cubierta inequívocamente de otro libro. Eso no equivale a aprobar las 100 obras. Las limitaciones anteriores quedan abiertas para revisión, sin bloquear el desarrollo de circulación ni ampliar el catálogo.

## Reproducir

Desde la raíz, después de la preparación explícita de datos:

```bash
python -m herramientas.auditar_catalogo_local
```

La herramienta sólo lee la base y las capturas verificadas. Regenera [cobertura.json](./cobertura.json), [COBERTURA.md](./COBERTURA.md) y el HTML autónomo con imágenes incrustadas; este documento de observaciones no se sobrescribe.
