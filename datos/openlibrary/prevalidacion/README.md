# Prevalidación histórica: salidas locales

Los SQLite, CSV y métricas de esta carpeta son salidas anteriores del pipeline y no se suben a Git. No son las bases operativa/demo de la aplicación.

Los dos insumos JSON se conservan en la carpeta superior. Se pueden reprocesar offline mediante el [pipeline](../../../herramientas/openlibrary/README.md), con salida en datos/generados/prevalidacion. La [guía de colaboración](../../../docs/COLABORACION.md) contiene el comando completo.

Las pruebas reconstruyen una muestra equivalente en un directorio temporal por sesión. No dependen de una base binaria conservada en este directorio ni modifican las fuentes originales.
