# Complemento 3C.1 — Condición física y baja de ejemplares

Verificado el 10 de noviembre de 2026. Amplía [3C](./ETAPA_3C_RESULTADOS.md) a pedido del usuario, antes de diseñar circulación. Suite completa: **455 pruebas aprobadas** con Python 3.14.10 y Flet 1.0.5.

## Alcance y responsabilidades

[InventarioLocalView](../biblioteca/interfaz/inventario_local_view.py) ofrece en cada fila **Condición** y **Dar de baja**. El selector presenta Apto, Dañado y Destruido, con explicación de la irreversibilidad de este último. La baja requiere confirmación, conserva el registro y su código y queda deshabilitada en la fila ya dada de baja. Las tablas permiten desplazamiento horizontal para acceder a todas las columnas.

[AdministracionLocal](../biblioteca/administracion_local.py) habilita únicamente dos comandos adicionales de InventarioService: registrar_condicion y dar_de_baja. El formulario compartido conserva bloqueo de doble envío, mensajes de error, campos al fallar y guardado en trabajador separado. No se añade SQL ni se duplican validaciones en la vista.

No se modificaron entidades, reglas, servicios de inventario, esquema 6, bibliografía ni datos de la demo principal. Daño puede repararse; destrucción no puede revertirse. Cambiar condición después de baja no rehabilita el ejemplar. Propietaria y ubicación no cambian. Cancelar el diálogo no ejecuta nada.

Tras confirmar, se relee el listado. Al regresar al catálogo y abrir la ficha se releen disponibilidad y existencias, conservando filtros y página. No se añade caché ni se publica un resultado calculado sólo en Flet.

## Verificación

Se incorporaron cuatro casos en [pruebas de administración conectada](../tests/test_administracion_conectada.py), además de conservar las pruebas previas de dominio y servicios:

- Formularios reales: dañado elimina disponibilidad, apto la recupera, cancelar baja no escribe y confirmar baja no permite reactivación por condición. Se verifican catálogo y ficha con identidad, propiedad, ubicación y metadatos conservados.
- Un formulario abierto con condición anterior no puede recuperar una copia destruida entre apertura y guardado; el servicio la relee y rechaza, preservando el formulario y el dato persistido.
- Los dos nuevos comandos rechazan una base RENDIMIENTO sin escribir.

```text
python -m pytest tests/test_administracion_conectada.py tests/test_inventario.py -q
62 passed in 1.64s

python -m pytest -q
455 passed in 5.44s
```

Recorrido visual en Flet web local sobre la copia de revisión, nunca sobre la demo principal:

1. Obra «El ingenioso hidalgo Don Quijote de la Mancha», inicialmente con dos disponibles.
2. DEMO-0034 de Centro cambia a Dañado: catálogo pasa a uno disponible y la ficha muestra Centro 1 propio / 1 ubicado / 0 disponibles.
3. Cambiar a Apto recupera esa disponibilidad.
4. Confirmar baja de DEMO-0134 de Norte mantiene la fila y su código con situación BAJA; deshabilita otra baja en la fila. Al regresar, la ficha muestra Norte 1 propio / 1 ubicado / 0 disponibles, mientras Centro conserva 1 / 1 / 1.

Se reutiliza la copia de revisión de 3C, que ya contenía sus altas de prueba. No se reinicia la demo ni se cambia su plan de 150 copias. La revisión visual corresponde al cliente web local; no se declara una nueva automatización de la ventana nativa.

## Siguiente paso

El [diseño de etapa 4](./ETAPA_4_DISENO.md) y su [UML propuesto](./UML_ETAPA_4.md) están preparados para revisión. No se implementaron solicitudes, asignaciones, préstamos, nuevas situaciones operativas ni migraciones. Los plazos y políticas propuestos requieren revisión antes de programar.
