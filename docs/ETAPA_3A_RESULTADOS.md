# Etapa 3A — Prototipo visual Flet

Fecha: 4 de noviembre de 2026. Python 3.14.8, Flet 1.0.5, Linux.

## Alcance implementado

Entrada de escritorio en [main.py](../main.py). La composición [AplicacionHorizonte](../biblioteca/interfaz/aplicacion.py) mantiene navegación y sede de trabajo; las vistas de [Inicio](../biblioteca/interfaz/inicio_view.py), [Catálogo](../biblioteca/interfaz/catalogo_view.py) y [Socios](../biblioteca/interfaz/socios_view.py) comparten [componentes visuales](../biblioteca/interfaz/componentes.py).

Se adoptó fondo claro, superficies blancas, azul petróleo, menú lateral y sede en cabecera. Los módulos todavía no implementados aparecen como próximos, sin operaciones ficticias de préstamo/remito. El inicio ofrece cantidades de muestra y accesos clicables. La sede de trabajo no restringe los socios ni el catálogo de toda la red.

El catálogo incluye búsqueda única por título original/español/autor, filtros de género, sede y disponibilidad de muestra, cuadrícula/tabla, navegación de 24 obras por página y ficha modal. Hay seis obras ilustrativas. Las cubiertas se dibujan con Flet; no se descargan imágenes ni se atribuyen a ediciones bibliográficas reales. La ficha conserva la distinción entre título mostrado y original y señala las cantidades y descripciones ficticias.

Socios incluye cuatro personas ficticias, búsqueda por nombre/DNI/contacto, filtro por habilitación y formulario de muestra nuevo/existente. El diálogo permite probar campos y descarta cambios al cerrar; no tiene una acción que simule un guardado real.

Los [datos de presentación](../biblioteca/interfaz/datos_prototipo.py) son objetos inmutables de muestra, separados del dominio y de los repositorios. Este incremento no modifica servicios, esquema SQLite, reglas de disponibilidad ni contrato Open Library. No lee ni escribe bases operativas. Tampoco completa la etapa 3.

## Comprobaciones realizadas

- Suite completa: **357 pruebas aprobadas** (347 existentes y diez casos nuevos), sin advertencias en la ejecución verificada.
- [Pruebas de presentación](../tests/test_prototipo_interfaz.py): búsquedas por ambos títulos/autor, combinación de filtros y conservación al alternar vista; páginas de 24 sobre 49 obras de muestra; reinicio al filtrar; descarte de búsquedas pendientes al navegar y de revisiones obsoletas; conservación de filtros al regresar; módulos futuros inaccesibles; sede independiente del listado global; formulario descartable sin mutar datos.
- [Demo de catálogo 2A](../biblioteca/demo_catalogo.py) ejecutada: búsqueda por original y ediciones españolas, una obra por resultado y preferencia conservada al reabrir SQLite temporal.
- Cliente nativo iniciado mediante la tarea de escritorio. Emitió mensajes GTK de accesibilidad/cursor; no apareció una excepción Python al iniciar. No se realizó automatización completa del cliente nativo.
- Los mismos controles se verificaron en Flet web local con accesibilidad activada: navegación Inicio → Catálogo → Socios; buscar Terramar y obtener una obra; abrir/cerrar ficha con original, descripción y disponibilidad por sede; alternar a tabla; abrir formulario de nuevo socio, escribir y cerrar conservando cuatro socios; filtrar inhabilitados y obtener sólo Camila López.
- Inspección visual de catálogo, ficha y formulario en el navegador integrado. La vista disponible fue de aproximadamente 929 × 548; el prototipo permite desplazarse en alturas inferiores a 700. El menú compacto muestra iconos con ayudas. Se corrigió una distribución inválida en la bienvenida detectada al renderizar, que no aparecía en las pruebas de construcción.
- Comprobación de diagnósticos del editor sobre los archivos de interfaz y pruebas: sin errores informados.

Las pruebas de controles no sustituyen aprobar tipografías, tamaños y distribución en el escritorio del usuario. No se midió latencia integrada ni se ensayaron 100.000 obras en Flet: corresponde a 3B, después de conectar los servicios.

## Reproducir y revisar

Desde la raíz, con el entorno virtual activado:

```bash
python -m pip install -r requirements-dev.txt
python main.py
python -m pytest -q
```

Tarea VS Code: **Horizonte: prototipo de escritorio**, en [tasks.json](../.vscode/tasks.json). Tamaño inicial 1440 × 960; mínimo de escritorio 900 × 700. La primera preparación del cliente puede demorar. Reiniciar la aplicación después de editar código; no se configuró recarga automática.

Vista opcional de los mismos controles en navegador:

```bash
python -m pip install -r requirements-preview.txt
python main.py --web --port 8550
```

Si ese puerto ya está ocupado por una vista previa, cerrar su tarea o elegir otro con `--port`. El servidor escucha sólo en 127.0.0.1. El modo web es una herramienta de revisión local; la entrega sigue siendo de escritorio.

## Continuidad

Revisar el estilo y los recorridos antes de comenzar 3B. Después se sustituirán los datos de muestra del catálogo por consultas paginadas mediante servicios, con búsqueda OR unificada, filtros antes de LIMIT, acceso SQLite en trabajadores con conexiones propias y protección frente a resultados obsoletos. El formulario de socios se conectará en 3C. No se añadieron caché, FTS5 ni otro patrón sin mediciones que lo justifiquen.
