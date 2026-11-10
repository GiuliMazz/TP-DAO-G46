CREATE TABLE autor (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(id) = 36),
    id_openlibrary TEXT UNIQUE,
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    nombre_normalizado TEXT NOT NULL
);
CREATE TABLE obra (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(id) = 36),
    id_openlibrary TEXT UNIQUE,
    titulo_original TEXT NOT NULL CHECK (length(trim(titulo_original)) > 0),
    titulo_normalizado TEXT NOT NULL,
    descripcion_original TEXT,
    anio_primera_publicacion INTEGER CHECK (anio_primera_publicacion > 0),
    portada_obra_id INTEGER CHECK (portada_obra_id > 0),
    edicion_preferida_id TEXT,
    FOREIGN KEY (edicion_preferida_id, id) REFERENCES edicion(id, obra_id)
        DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE obra_autor (
    obra_id TEXT NOT NULL REFERENCES obra(id),
    autor_id TEXT NOT NULL REFERENCES autor(id),
    orden INTEGER NOT NULL CHECK (orden >= 0),
    PRIMARY KEY (obra_id, autor_id),
    UNIQUE (obra_id, orden)
);
CREATE TABLE edicion (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(id) = 36),
    obra_id TEXT NOT NULL REFERENCES obra(id),
    id_openlibrary TEXT UNIQUE,
    titulo TEXT NOT NULL CHECK (length(trim(titulo)) > 0),
    titulo_normalizado TEXT NOT NULL,
    idioma TEXT NOT NULL CHECK (idioma = 'spa'),
    isbn_10 TEXT CHECK (length(isbn_10) = 10),
    isbn_13 TEXT CHECK (length(isbn_13) = 13),
    isbn_canonico TEXT CHECK (length(isbn_canonico) = 13),
    editorial TEXT,
    anio_publicacion INTEGER CHECK (anio_publicacion > 0),
    numero_paginas INTEGER CHECK (numero_paginas > 0),
    portada_edicion_id INTEGER CHECK (portada_edicion_id > 0),
    descripcion_es TEXT,
    UNIQUE (id, obra_id)
);
CREATE INDEX ix_autor_nombre ON autor(nombre_normalizado, id);
CREATE INDEX ix_obra_titulo ON obra(titulo_normalizado, id);
CREATE INDEX ix_obra_autor_autor ON obra_autor(autor_id, obra_id);
CREATE INDEX ix_edicion_obra ON edicion(obra_id, id);
CREATE INDEX ix_edicion_titulo ON edicion(titulo_normalizado, obra_id);
CREATE INDEX ix_edicion_isbn ON edicion(isbn_canonico);
