-- Tres vocabularios lógicos, sin duplicar su estructura ni su ciclo de revisión.
CREATE TABLE termino_clasificacion (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('GENERO', 'ETIQUETA', 'PUBLICO')),
    nombre TEXT NOT NULL CHECK (length(trim(nombre)) > 0),
    nombre_normalizado TEXT NOT NULL,
    UNIQUE (tipo, nombre_normalizado),
    UNIQUE (id, tipo)
);

CREATE TABLE clasificacion_obra (
    obra_id TEXT NOT NULL REFERENCES obra(id),
    termino_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('PROPUESTO', 'APROBADO', 'RECHAZADO')),
    metodo TEXT NOT NULL CHECK (metodo IN ('MANUAL', 'AUTOMATICO')),
    motivo TEXT NOT NULL CHECK (length(trim(motivo)) > 0),
    fecha TEXT NOT NULL,
    regla_id TEXT,
    regla_version TEXT,
    PRIMARY KEY (obra_id, termino_id),
    FOREIGN KEY (termino_id, tipo) REFERENCES termino_clasificacion(id, tipo),
    FOREIGN KEY (regla_id, regla_version) REFERENCES regla_clasificacion(id, version),
    CHECK ((metodo = 'MANUAL' AND regla_id IS NULL AND regla_version IS NULL)
        OR (metodo = 'AUTOMATICO' AND length(trim(regla_id)) > 0
            AND regla_id IS NOT NULL AND length(trim(regla_version)) > 0
            AND regla_version IS NOT NULL AND estado != 'RECHAZADO'))
);
CREATE INDEX idx_clasificacion_filtro ON clasificacion_obra(tipo, termino_id, estado, obra_id);

CREATE TABLE materia_original (
    id INTEGER PRIMARY KEY,
    obra_id TEXT NOT NULL REFERENCES obra(id),
    fuente TEXT NOT NULL CHECK (length(trim(fuente)) > 0),
    texto TEXT NOT NULL CHECK (length(trim(texto)) > 0),
    UNIQUE (obra_id, fuente, texto),
    UNIQUE (id, obra_id)
);

CREATE TABLE evidencia_clasificacion (
    id INTEGER PRIMARY KEY,
    obra_id TEXT NOT NULL,
    termino_id TEXT NOT NULL,
    materia_id INTEGER NOT NULL,
    regla_id TEXT NOT NULL,
    regla_version TEXT NOT NULL,
    resultado TEXT NOT NULL CHECK (resultado IN ('PROPUESTO', 'APROBADO')),
    motivo TEXT NOT NULL,
    fecha TEXT NOT NULL,
    contexto TEXT NOT NULL,
    FOREIGN KEY (obra_id, termino_id) REFERENCES clasificacion_obra(obra_id, termino_id),
    FOREIGN KEY (materia_id, obra_id) REFERENCES materia_original(id, obra_id),
    FOREIGN KEY (regla_id, regla_version) REFERENCES regla_clasificacion(id, version),
    UNIQUE (obra_id, termino_id, materia_id, regla_id, regla_version, contexto)
);

CREATE TABLE regla_clasificacion (
    id TEXT NOT NULL,
    version TEXT NOT NULL,
    termino_id TEXT NOT NULL REFERENCES termino_clasificacion(id),
    materia TEXT NOT NULL,
    aprobacion_automatica INTEGER NOT NULL CHECK (aprobacion_automatica IN (0, 1)),
    PRIMARY KEY (id, version)
);

CREATE TABLE decision_clasificacion (
    id INTEGER PRIMARY KEY,
    obra_id TEXT NOT NULL,
    termino_id TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('PROPUESTO', 'APROBADO', 'RECHAZADO')),
    metodo TEXT NOT NULL CHECK (metodo IN ('MANUAL', 'AUTOMATICO')),
    motivo TEXT NOT NULL,
    fecha TEXT NOT NULL,
    regla_id TEXT,
    regla_version TEXT,
    FOREIGN KEY (obra_id, termino_id) REFERENCES clasificacion_obra(obra_id, termino_id),
    FOREIGN KEY (regla_id, regla_version) REFERENCES regla_clasificacion(id, version)
);
CREATE INDEX idx_decision_historial ON decision_clasificacion(obra_id, termino_id, id);
CREATE INDEX idx_evidencia_asociacion ON evidencia_clasificacion(obra_id, termino_id, id);
