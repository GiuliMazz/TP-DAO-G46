CREATE TABLE evaluacion_importacion (
    id INTEGER PRIMARY KEY,
    edicion_ol TEXT NOT NULL,
    huella TEXT NOT NULL,
    politica TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('PENDIENTE', 'ENRIQUECIDA', 'VALIDADA', 'RECHAZADA')),
    documento_json TEXT NOT NULL,
    controles_json TEXT NOT NULL,
    alertas_json TEXT NOT NULL,
    normalizados_json TEXT,
    fecha TEXT NOT NULL,
    UNIQUE (edicion_ol, huella, politica),
    UNIQUE (id, edicion_ol)
);
CREATE TABLE decision_importacion (
    id INTEGER PRIMARY KEY,
    edicion_ol TEXT NOT NULL,
    evaluacion_id INTEGER NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('PENDIENTE', 'ENRIQUECIDA', 'VALIDADA', 'RECHAZADA')),
    metodo TEXT NOT NULL CHECK (metodo IN ('MANUAL', 'AUTOMATICO')),
    motivo TEXT NOT NULL CHECK (length(trim(motivo)) > 0),
    correcciones_json TEXT NOT NULL,
    fecha TEXT NOT NULL,
    FOREIGN KEY (evaluacion_id, edicion_ol) REFERENCES evaluacion_importacion(id, edicion_ol),
    UNIQUE (id, edicion_ol)
);
CREATE TABLE seguimiento_importacion (
    edicion_ol TEXT PRIMARY KEY,
    ultima_evaluacion_id INTEGER NOT NULL,
    decision_id INTEGER NOT NULL,
    edicion_local_id TEXT REFERENCES edicion(id),
    decision_integrada_id INTEGER,
    FOREIGN KEY (ultima_evaluacion_id, edicion_ol) REFERENCES evaluacion_importacion(id, edicion_ol),
    FOREIGN KEY (decision_id, edicion_ol) REFERENCES decision_importacion(id, edicion_ol),
    FOREIGN KEY (decision_integrada_id, edicion_ol) REFERENCES decision_importacion(id, edicion_ol),
    CHECK ((edicion_local_id IS NULL) = (decision_integrada_id IS NULL))
);
CREATE INDEX idx_decision_importacion_historial ON decision_importacion(edicion_ol, id);
CREATE INDEX idx_decision_importacion_estado ON decision_importacion(estado, id);
