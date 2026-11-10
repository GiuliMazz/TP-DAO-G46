# Clonar, reproducir y compartir Horizonte

El repositorio contiene código, pruebas, documentación y fuentes bibliográficas necesarias. Las bases de trabajo se preparan en cada equipo: no se comparten estados operativos mediante archivos SQLite en Git.

## Primer arranque

Repositorio del equipo: [GiuliMazz/TP-DAO-G46](https://github.com/GiuliMazz/TP-DAO-G46).

```bash
git clone https://github.com/GiuliMazz/TP-DAO-G46.git
cd TP-DAO-G46
```

Desde la raíz del clon, con Python 3.14:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m herramientas.preparar_catalogo_local
python -m herramientas.preparar_socios_demo
python main.py
```

En Windows: `py -3.14 -m venv .venv` y `.venv\Scripts\Activate.ps1` en PowerShell. La verificación realizada corresponde a Linux; no se afirma una prueba completa en Windows. Las tareas de VS Code son opcionales y contemplan ambas rutas del intérprete.

Las pruebas no requieren preparar bases primero. Una fixture de sesión reproduce la prevalidación histórica a partir de los dos JSON fuente y trabaja en temporales. Los preparadores de demo no consultan Open Library: las 100 obras y las 86 portadas disponibles ya tienen sus capturas locales. El arranque de Flet no crea datos.

La vista web es opcional: instalar requirements-preview.txt y ejecutar `python main.py --web --port 8550`. El destino principal sigue siendo escritorio.

## Qué se versiona

| Contenido | Motivo |
|---|---|
| Código, migraciones y tests | Implementación y regresiones |
| README, AGENTS y plan | Incorporación del equipo y continuidad de los agentes |
| Diseño, UML, informes y evidencias pequeñas de medición | Contexto y defensa académica; distinguir resultados de propuestas |
| Consigna, apuntes de referencia y presentación original | Requisitos del TP |
| datos/catalogo_local: manifiesto, capturas y portadas | Reproducir offline y verificar procedencia/huellas |
| Dos JSON de la muestra histórica de Open Library | Regresiones y reconstrucción de prevalidación |
| DOT, PNG de diagramas y documento de continuidad inicial | Referencia histórica, separada del diseño vigente |
| Tareas comunes de VS Code | Ejecutar, preparar datos y probar sin rutas personales |

Quedan excluidos mediante .gitignore: entornos, cachés, SQLite y sus archivos auxiliares, datos/generados, ZIP, muestras y extractores duplicados, salidas históricas reconstruibles, configuración privada de agentes/credenciales, logs y temporales. Los PNG de diagramas sí se incluyen. El archivo local puede seguir existiendo en el equipo del autor aunque no forme parte del clon.

Las capturas bibliográficas verificadas no se normalizan al cambiar de sistema operativo: .gitattributes conserva sus bytes para no romper SHA-256. No editar capturas para corregir títulos del catálogo; usar los servicios y documentar revisiones.

## Recuperar el recorrido histórico opcional de etapa 2

```bash
python herramientas/openlibrary/ejecutar_etapa1.py \
  --catalogo datos/openlibrary/catalogo_exploratorio.json \
  --detalles datos/openlibrary/respuestas_originales.json \
  --salida datos/generados/prevalidacion
python -m biblioteca.demo_etapa2
```

No hace falta para iniciar la aplicación actual ni ejecutar pytest. No se reconstruye encima de una base operativa.

## Trabajo del equipo

Leer [AGENTS](../AGENTS.md), el [plan](../PLAN_DESARROLLO.md) y el [diseño pendiente de etapa 4](./ETAPA_4_DISENO.md). Usar ramas por incremento y revisar cambios pequeños. Antes de integrar, ejecutar pytest y probar visualmente las pantallas modificadas. No confundir un documento de diseño con autorización para implementar todos los módulos.

## Primera publicación en GitHub

Git local se inicia con rama main. Crear en la cuenta elegida un repositorio vacío, copiar su URL real y luego:

```bash
git status --short
git diff --cached --stat
git commit -m "Base del TP Horizonte hasta etapa 3C.1"
git remote add origin URL_DEL_REPOSITORIO
git push -u origin main
```

El contenido inicial queda preparado en el índice después de la revisión. Si se modifican archivos después, revisar con `git diff` y agregar únicamente los cambios deseados antes del commit. No se incluyen usuario, correo, credenciales ni una URL de repositorio inventada. Crear el repositorio remoto y publicarlo requiere elegir la cuenta y la URL con el equipo.

## Verificación de la preparación

El 10/11/2026 se exportaron los **266 archivos del índice** a una carpeta temporal, sin entorno virtual, cachés ni bases locales. El contenido seleccionado ocupa aproximadamente **6,6 MB**. Se reutilizó el intérprete/dependencias ya instalados; no fue una instalación nueva de paquetes.

Después de esa verificación, a pedido del usuario, se incorporaron también los 13 PNG de los diagramas históricos. Este agregado documental no modifica código ni datos de las pruebas.

- Suite completa sobre esa exportación: **455 passed in 6.74s**.
- Preparación offline de catálogo y socios desde cero; segunda carga de socios creó cero y repetir catálogo conservó los ocho socios.
- Operativa: 100 obras, 100 ediciones, 87 autores y cero sedes/socios/ejemplares ficticios.
- Demo: misma bibliografía, tres sedes, ocho socios y 150 ejemplares; integridad y claves foráneas correctas.
- Reconstrucción del pipeline histórico y demostración integrada de etapa 2 funcionando sin las muestras/ZIP excluidos.
- Capturas y portadas exportadas conservan exactamente sus bytes y SHA-256.
- Índice sin SQLite, ZIP, bytecode, entornos, datos/generados ni configuración privada; revisión de patrones habituales de credenciales sin coincidencias. Esa revisión no equivale a una garantía exhaustiva de ausencia de secretos.

La limpieza afecta la selección para versionar; las bases de trabajo originales se conservan fuera del repositorio. El primer commit y el push corresponden a la publicación posterior en el repositorio del equipo.
