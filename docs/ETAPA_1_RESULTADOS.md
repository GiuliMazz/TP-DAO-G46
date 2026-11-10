# Etapa 1 — Sedes y socios

Fecha de verificación: 3 de noviembre de 2026.

## Resultado

Implementados los casos de uso de administración de sedes y socios acordados en la [etapa 0](./ETAPA_0_DISENO.md). La etapa incorpora código y pruebas, sin interfaz gráfica ni módulos posteriores.

| Capa | Implementación |
|---|---|
| Dominio | [Sede](../biblioteca/dominio/sede.py) y [Socio / EstadoSocio](../biblioteca/dominio/socio.py): datos validados, identidad estable, cambios por métodos y modificación atómica de atributos |
| Servicios | [SedeService](../biblioteca/servicios/sede_service.py) y [SocioService](../biblioteca/servicios/socio_service.py): casos de uso, comprobación de duplicados y coordinación transaccional |
| Repositorios | [Sedes](../biblioteca/repositorios/sede_repository.py) y [socios](../biblioteca/repositorios/socio_repository.py): SQL parametrizado, reconstrucción y listados paginados sin commits propios |
| Persistencia | [Conexión y transacciones](../biblioteca/persistencia/base_datos.py), [migración 001](../biblioteca/persistencia/migraciones/001_sedes_socios.sql): versión de esquema, unicidad y rollback |
| Demostración | [demo](../biblioteca/demo.py): datos ficticios en SQLite temporal, sin cambiar bases existentes |

Sedes incluye registrar, modificar, obtener, listar, dar de baja y activar. Socios incluye registrar, modificar, obtener, buscar por DNI, listar, inhabilitar y habilitar. Los UUID se conservan al editar y al reabrir la base. No hay eliminación física en los casos de uso.

## Decisiones aplicadas

- Nombre general: Red de Bibliotecas Horizonte. No se repite como atributo de cada sede; Norte, Centro y Sur sólo se crean en la demostración temporal.
- Horarios obligatorios como texto informativo para cubrir la consigna; no condicionan automáticamente un préstamo.
- DNI argentino como único documento admitido en esta versión, sin atributos de nacionalidad, tipo o país. El número se almacena como texto y no cambia la identidad interna.
- Unicidad de nombre de sede normalizado y de DNI incluso cuando el registro esté inactivo. En los nombres se compactan espacios y se usa casefold sin eliminar acentos. La clave de búsqueda se guarda separada del nombre mostrado.
- El DNI admite separadores entre cifras; no signos iniciales, letras, dígitos no ASCII ni puntuación en los extremos. Se conservan ceros iniciales y no se exige longitud exacta ni se verifica autenticidad.
- Listados por nombre, estado y página: de 1 a 100 resultados, 50 por defecto, orden estable por nombre normalizado e ID. La búsqueda de fragmentos es literal y no interpreta comodines SQL.
- Un caso de uso de escritura abre una transacción `BEGIN IMMEDIATE` sobre la conexión de su repositorio; todas sus escrituras se confirman juntas. No se anidan servicios de escritura dentro de otra transacción.
- Los conflictos se expresan mediante errores de aplicación; la causa SQLite se conserva para diagnóstico sin usar su mensaje crudo como mensaje de interfaz.
- El esquema operativo está separado del importador. La migración no elimina tablas: rechaza una base sin versión que ya contiene tablas ajenas, y rechaza una versión futura. Repetir la migración conserva los registros.

El [UML](./UML_ETAPA_0.md) conserva estas responsabilidades. La conexión y transacción son infraestructura de sqlite3; no se introducen nuevos patrones de diseño ni repositorios genéricos.

## Verificación ejecutada

Entorno: Python 3.14.8, SQLite de la biblioteca estándar, pytest 9.2.0 en [entorno virtual](../.venv). La única dependencia añadida es pytest en [requirements-dev.txt](../requirements-dev.txt).

Desde la raíz del proyecto, con el entorno activado:

```bash
python -m pytest -q
```

Resultado: **81 passed in 0.70s**, código de salida 0. Las parametrizaciones cuentan como casos separados.

| Evidencia | Casos cubiertos |
|---|---|
| [Pruebas de dominio](../tests/test_dominio.py) | Campos obligatorios, DNI, ceros iniciales, validación de estados/UUID, identidad protegida, cambios idempotentes y actualización inválida sin modificaciones parciales |
| [Pruebas de servicios](../tests/test_servicios.py) | Relectura tras cerrar/abrir, duplicados en alta/modificación, búsqueda normalizada, cambio de DNI conservando ID, filtros/paginación, registros inexistentes, entradas SQL tratadas como texto, rollback tras escritura y dos altas concurrentes |
| [Pruebas de persistencia](../tests/test_persistencia.py) | PRAGMA foreign_keys/integrity_check, versión y repetición de migración, rechazo de bases ajenas/futuras, rollback incluso del DDL, restricciones UNIQUE sin servicios, transacción compartida y errores traducidos |

La primera ejecución detectó un caso real: el normalizador eliminaba un guion inicial y aceptaba un número con signo. Se corrigió la validación antes de quitar separadores y se añadieron extremos con puntuación como regresión. La ejecución final pasó todos los casos.

Se intentó ejecutar desde el controlador de tests de VS Code, pero no había ítems descubiertos; la suite se ejecutó efectivamente con pytest en terminal. La consulta de problemas del editor sobre [biblioteca/](../biblioteca) y [tests/](../tests) no informó errores.

También se ejecutó:

```bash
python -m biblioteca.demo
```

Resultado: código de salida 0; sedes Centro/Norte/Sur; socio inhabilitado, alta duplicada rechazada, socio habilitado recuperado tras reabrir y `UUID conservado: True`. La base temporal se eliminó al terminar. No se creó una base operativa definitiva ni se modificaron las muestras de Open Library.

## Límites y siguiente incremento

Esta evidencia cubre el backend de RF01/RF02 y la parte de RN05 correspondiente a socios. La interacción gráfica se incorporará en etapa 3. No se presenta todavía como cumplimiento de todos los procesos del TP.

La habilitación y el estado de sede ya se conservan, pero sus efectos sobre préstamos, reservas y envíos se implementarán y comprobarán con esos módulos. Tampoco hay validación por autenticidad de DNI, campos de préstamos, calendarios ni suspensión automática por atraso.

Siguiente paso del plan: revisar el diseño concreto de catálogo e inventario antes de implementar etapa 2. Mantener separados obra, edición y ejemplar; conservar estados técnicos en importación, respetar el contrato y proteger revisiones humanas al importar. State y Strategy se incorporarán cuando existan sus casos de uso reales.
