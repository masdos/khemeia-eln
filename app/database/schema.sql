CREATE TABLE IF NOT EXISTS projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    description  TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS protocols (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    content_markdown  TEXT NOT NULL,
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL,
    protocol_id     INTEGER NOT NULL,
    title           TEXT NOT NULL,
    state           TEXT NOT NULL CHECK (state IN ('Running', 'Success', 'Fail')),
    question                        TEXT,
    experimental_procedure_markdown  TEXT,
    result_markdown                 TEXT,
    conclusions                     TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id)  REFERENCES projects (id)  ON DELETE RESTRICT,
    FOREIGN KEY (protocol_id) REFERENCES protocols (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_experiments_project_id  ON experiments (project_id);
CREATE INDEX IF NOT EXISTS idx_experiments_protocol_id ON experiments (protocol_id);
CREATE INDEX IF NOT EXISTS idx_experiments_state        ON experiments (state);


CREATE TABLE IF NOT EXISTS reagents (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    name                     TEXT NOT NULL,
    cas_number               TEXT,
    smiles                   TEXT,
    in_stock                 INTEGER NOT NULL DEFAULT 0 CHECK (in_stock IN (0, 1)),
    lot_number               TEXT,
    supplier                 TEXT,
    expiry_date              DATE,
    state                    TEXT CHECK (state IS NULL OR state IN ('solid', 'liquid', 'gas')),
    purity                   REAL,
    is_explosive             INTEGER NOT NULL DEFAULT 0 CHECK (is_explosive IN (0, 1)),
    is_flammable             INTEGER NOT NULL DEFAULT 0 CHECK (is_flammable IN (0, 1)),
    is_oxidizer              INTEGER NOT NULL DEFAULT 0 CHECK (is_oxidizer IN (0, 1)),
    is_gas_under_pressure    INTEGER NOT NULL DEFAULT 0 CHECK (is_gas_under_pressure IN (0, 1)),
    is_corrosive             INTEGER NOT NULL DEFAULT 0 CHECK (is_corrosive IN (0, 1)),
    is_acute_toxic           INTEGER NOT NULL DEFAULT 0 CHECK (is_acute_toxic IN (0, 1)),
    is_harmful_irritant      INTEGER NOT NULL DEFAULT 0 CHECK (is_harmful_irritant IN (0, 1)),
    is_health_hazard         INTEGER NOT NULL DEFAULT 0 CHECK (is_health_hazard IN (0, 1)),
    is_environmental_hazard  INTEGER NOT NULL DEFAULT 0 CHECK (is_environmental_hazard IN (0, 1)),
    created_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reagents_cas_number ON reagents (cas_number);

CREATE TABLE IF NOT EXISTS equipment (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    description  TEXT,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS experiment_reagents (
    experiment_id  INTEGER NOT NULL,
    reagent_id     INTEGER NOT NULL,
    amount_used    REAL,
    unit           TEXT,
    PRIMARY KEY (experiment_id, reagent_id),
    FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE,
    FOREIGN KEY (reagent_id)    REFERENCES reagents (id)    ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_experiment_reagents_reagent_id ON experiment_reagents (reagent_id);

CREATE TABLE IF NOT EXISTS experiment_equipment (
    experiment_id  INTEGER NOT NULL,
    equipment_id   INTEGER NOT NULL,
    PRIMARY KEY (experiment_id, equipment_id),
    FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE,
    FOREIGN KEY (equipment_id)  REFERENCES equipment (id)   ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_experiment_equipment_equipment_id ON experiment_equipment (equipment_id);

CREATE TABLE IF NOT EXISTS reports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name     TEXT NOT NULL,
    stored_name   TEXT NOT NULL,
    extension     TEXT NOT NULL,
    upload_date   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiment_reports (
    experiment_id  INTEGER NOT NULL,
    report_id      INTEGER NOT NULL,
    PRIMARY KEY (experiment_id, report_id),
    FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE,
    FOREIGN KEY (report_id)     REFERENCES reports (id)     ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_experiment_reports_report_id ON experiment_reports (report_id);

CREATE TABLE IF NOT EXISTS attachments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id  INTEGER NOT NULL,
    file_name      TEXT NOT NULL,
    stored_name    TEXT NOT NULL,
    extension      TEXT NOT NULL,
    upload_date    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attachments_experiment_id ON attachments (experiment_id);
