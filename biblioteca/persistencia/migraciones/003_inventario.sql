CREATE TABLE ejemplar (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(id) = 36),
    codigo_inventario TEXT NOT NULL UNIQUE
        CHECK (length(trim(codigo_inventario)) > 0 AND instr(codigo_inventario, ' ') = 0),
    edicion_id TEXT NOT NULL REFERENCES edicion(id),
    sede_propietaria_id TEXT NOT NULL REFERENCES sede(id),
    sede_actual_id TEXT REFERENCES sede(id),
    condicion_fisica TEXT NOT NULL CHECK (condicion_fisica IN ('APTO', 'DANIADO', 'DESTRUIDO')),
    situacion_operativa TEXT NOT NULL CHECK (situacion_operativa IN ('LIBRE', 'BAJA'))
);
CREATE INDEX ix_ejemplar_edicion ON ejemplar(edicion_id, sede_actual_id);
CREATE INDEX ix_ejemplar_propietaria ON ejemplar(sede_propietaria_id, edicion_id);
CREATE INDEX ix_ejemplar_ubicacion ON ejemplar(sede_actual_id, edicion_id, situacion_operativa, condicion_fisica);
