CREATE TABLE sede (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(id) = 36),
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    nombre_normalizado TEXT NOT NULL UNIQUE CHECK (length(trim(nombre_normalizado)) > 0),
    direccion TEXT NOT NULL CHECK (length(trim(direccion)) > 0),
    contacto TEXT NOT NULL CHECK (length(trim(contacto)) > 0),
    horarios TEXT NOT NULL CHECK (length(trim(horarios)) > 0),
    activa INTEGER NOT NULL CHECK (activa IN (0, 1))
);
CREATE TABLE socio (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(id) = 36),
    documento TEXT NOT NULL UNIQUE
        CHECK (length(documento) > 0 AND documento NOT GLOB '*[^0-9]*'),
    nombre_completo TEXT NOT NULL CHECK (length(trim(nombre_completo)) > 0),
    nombre_normalizado TEXT NOT NULL CHECK (length(trim(nombre_normalizado)) > 0),
    contacto TEXT NOT NULL CHECK (length(trim(contacto)) > 0),
    estado TEXT NOT NULL CHECK (estado IN ('HABILITADO', 'INHABILITADO'))
);
CREATE INDEX ix_sede_orden ON sede(nombre_normalizado, id);
CREATE INDEX ix_socio_orden ON socio(nombre_normalizado, id);
