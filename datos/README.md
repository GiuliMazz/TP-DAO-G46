# Datos de trabajo

El [catálogo local de 3B.2](./catalogo_local/README.md) reúne 100 obras reales con edición española y 86 portadas locales, con capturas, identidades y huellas verificables. El comando `python -m herramientas.preparar_catalogo_local` reproduce, sin red, dos bases independientes en [generados/catalogo_local/](./generados/catalogo_local/): operativa bibliográfica y demo con 150 ejemplares ficticios. Ese directorio también contiene el CSV de auditoría. Conservar los identificadores de tipo junto a las bases; repetir no reemplaza bases ajenas ni reinicia datos operativos.

Los [insumos de Open Library](./openlibrary/) que seguimos utilizando son:

- [catalogo_exploratorio.json](./openlibrary/catalogo_exploratorio.json): muestra de 1.000 obras candidatas.
- [respuestas_originales.json](./openlibrary/respuestas_originales.json): respuestas detalladas de la muestra anterior.
- [prevalidacion/](./openlibrary/prevalidacion/README.md): explicación de las salidas históricas locales, no versionadas. Se reconstruyen offline; pytest genera su propia copia temporal.

Para ejecutar el proceso, ver el [pipeline vigente](../herramientas/openlibrary/README.md). Las salidas nuevas se escriben en datos/generados, ruta ignorada por Git, y no deben sobrescribir estos insumos o la referencia.

Las muestras previas, sus cachés y copias históricas pueden seguir en archivo/openlibrary de la máquina original; están excluidas del repositorio. La base operativa de la aplicación es independiente de estas bases bibliográficas.
