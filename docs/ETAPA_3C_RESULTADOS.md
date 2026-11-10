# Etapa 3C — Administración conectada

Verificación: 10 de noviembre de 2026. Python 3.14.10, Flet 1.0.5 y SQLite mediante sqlite3. **451 pruebas aprobadas**, incluidas 20 nuevas de administración. [Diseño previo](./ETAPA_3C_DISENO.md).

## Funcionalidad entregada

- **Socios:** alta, edición, habilitación/inhabilitación y listado de toda la red. Búsqueda única por nombre, DNI con separadores o contacto, aplicada en SQLite antes de paginar. Se conservan los filtros anteriores por nombre/estado.
- **Sedes:** alta, edición, baja lógica y reactivación, con dirección, contacto y horarios descriptivos. El encabezado conserva el UUID elegido después de renombrar; si se inactiva, elige otra sede activa o queda sin selección. No altera el filtro independiente del catálogo.
- **Ejemplares:** botón «Administrar ejemplares» en la ficha de obra; listado paginado con edición, propietaria, ubicación, condición y situación. Alta explícita con código único, edición española y sede activa. Inicialmente es apto, libre y está en su propietaria. Al regresar al catálogo/ficha se relee la disponibilidad.
- **Demo:** ocho socios ficticios, seis habilitados y dos inhabilitados. Nombres identificados con «Demo», contactos example.test y carga exclusivamente explícita. No se crean datos al iniciar Flet.

Cada listado muestra hasta 50 registros y consulta una fila adicional para determinar si existe otra página. No se filtran listados completos ni se unen páginas en la interfaz.

## Responsabilidades y guardado

[SociosLocalView](../biblioteca/interfaz/socios_local_view.py), [SedesLocalView](../biblioteca/interfaz/sedes_local_view.py) e [InventarioLocalView](../biblioteca/interfaz/inventario_local_view.py) sólo presentan y capturan datos. [AdministracionView y su formulario](../biblioteca/interfaz/administracion_view.py) comparten mecánica visual. [AdministracionLocal](../biblioteca/administracion_local.py) compone servicios/repositorios existentes con conexión propia por operación; las vistas no contienen SQL ni validaciones duplicadas.

Se conserva DNI único incluso en inhabilitados, baja lógica e identidad estable. El alta física vuelve a verificar sede activa y relaciones bibliográficas dentro de la transacción. No se incorporan otros documentos, cambios libres de propietaria ni traslados administrativos. No cambian esquema 6, entidades del UML, contrato Open Library ni las 100 obras. Una función SQLite casefold en el repositorio de socios permite comparar contactos Unicode sin añadir columnas o índices.

El lector agrega tres destinos acotados y mantiene un trabajador, debounce y descarte de respuestas antiguas. [EscritorAsincrono](../biblioteca/interfaz/escritor_asincrono.py) admite un comando por sesión en curso, sin cola reemplazable ni reintento automático. Como máximo hay un trabajador de lectura y otro de guardado por sesión. Cada uno abre y cierra sus conexiones en su propio hilo.

El formulario bloquea campos/botones al guardar y conserva datos si falla. Cancelar la espera o desconectar no interrumpe un comando aceptado. La reconexión espera su finalización, descarta el formulario anterior y relee. El éxito se comunica después del commit y se cierra el formulario antes del refresco: si falla la lectura, se reintenta esa lectura, sin repetir el alta. Un fallo de configuración de sedes se comunica como guardado confirmado con actualización pendiente.

Lecturas mode=ro y comandos mode=rw, comprobando marca y esquema: no se crean ni migran bases desde Flet. RENDIMIENTO no habilita administración y el acceso de escritura también rechaza ese tipo.

## Datos y reproducción

```bash
python -m herramientas.preparar_catalogo_local
python -m herramientas.preparar_socios_demo
python main.py
```

El segundo comando afecta exclusivamente una base DEMOSTRACION. Se ejecutó dos veces: creó ocho socios y luego cero. Los UUID se conservan en su identificador de tipo. Repetir respeta cambios manuales de DNI, nombre, contacto y habilitación; no adopta DNI existentes sin marca.

| Base al cerrar | Obras | Ediciones | Autores | Sedes | Socios | Ejemplares |
|---|---:|---:|---:|---:|---:|---:|
| Operativa | 100 | 100 | 87 | 0 | 0 | 0 |
| Demo principal | 100 | 100 | 87 | 3 | 8 | 150 |
| Copia de revisión visual | 100 | 100 | 87 | 4 | 9 | 151 |

Las tres pasaron integrity_check y foreign_key_check, sin relaciones inválidas. La copia está en datos/generados/etapa3c, ignorada por Git; sus altas de prueba no se incorporaron a la demo principal.

La marca se guarda por reemplazo de archivo temporal después del alta del servicio. SQLite y JSON no forman una transacción conjunta: si se interrumpe entre ambos, la siguiente ejecución detecta el DNI sin marca y exige revisar el conflicto, sin duplicar ni sobrescribir. No ejecutar dos preparadores simultáneamente. Los guardados normales de Flet sólo escriben SQLite.

## Verificación

[Pruebas nuevas](../tests/test_administracion_conectada.py): persistencia al reabrir, cambios inválidos sin efectos parciales, duplicados, búsqueda OR y paginación, baja/reactivación, rechazo de sede inactiva, recuperación del formulario, doble clic, lectura fallida después de commit, respuestas obsoletas, salida de pantalla, cancelación/reconexión durante un comando, bases ausentes/incompatibles/de rendimiento, semilla repetible y conflictos.

```text
python -m pytest -q
451 passed in 4.05s
```

Recorrido con cliente Flet web local sobre copia de demo:

1. Listado de socios, rechazo de DNI duplicado conservando campos, corrección, alta y búsqueda por DNI.
2. Alta de sede, cambio de nombre, baja y reactivación, con refresco de configuración.
3. Obra «127 horas»: inventario inicial con dos copias; alta REVISION-3C-001 en Centro y regreso a la ficha. Centro pasó de 0/0/0 a **1 propio, 1 ubicado y 1 disponible**, conservando las copias de Norte y Sur.
4. Modo claro/oscuro, tablas con desplazamiento y navegación en ventana de 929 × 548.

Se corrigió una barra de filtros que combinaba TextField expandido y Wrap y dejaba un bloque gris. La distribución final se verificó visualmente. La aplicación nativa también se inició desde la tarea de escritorio y emitió avisos GTK/Atk de accesibilidad/cursor. Los clics y formularios se comprobaron en el cliente web local; no se afirma una automatización completa de la ventana nativa.

## Continuidad

3C queda cerrada con administración básica y alta física explícita. Cambios de condición y baja de ejemplares siguen disponibles en backend; no se añadió su mantenimiento visual ni un módulo general de inventario independiente de la obra.

Sigue la **etapa 4: solicitudes y préstamo local**, revisando reglas y UML antes de programar. Después: flujo interbibliotecario con Strategy, remitos con State, recepción, entrega y retorno según el [plan](../PLAN_DESARROLLO.md). No se amplía el catálogo ni se añaden optimizaciones sin evidencia.
