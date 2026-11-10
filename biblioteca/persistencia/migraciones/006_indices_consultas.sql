-- Filtrar copias libres/aptas de una sede y paginar por código sin ordenar todas.
CREATE INDEX ix_ejemplar_sede_estado_codigo ON ejemplar (
    sede_actual_id, situacion_operativa, condicion_fisica, codigo_inventario, id
);
