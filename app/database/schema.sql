CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS protocols (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    content_markdown TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL,
    protocol_id INTEGER,
    title TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'Running'
        CHECK (state IN ('Running', 'Success', 'Fail')),
    reaction_onset TEXT NOT NULL DEFAULT '',
    workup TEXT NOT NULL DEFAULT '',
    purification TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    hash_sha256 TEXT,
    is_locked INTEGER NOT NULL DEFAULT 0 CHECK (is_locked IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (protocol_id) REFERENCES protocols (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS reagents (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cas_number TEXT NOT NULL DEFAULT '',
    smiles TEXT NOT NULL DEFAULT '',
    in_stock INTEGER NOT NULL DEFAULT 1 CHECK (in_stock IN (0, 1)),
    lot_number TEXT NOT NULL DEFAULT '',
    supplier TEXT NOT NULL DEFAULT '',
    expiry_date DATE,
    state TEXT NOT NULL DEFAULT '',
    purity REAL,
    is_explosive INTEGER NOT NULL DEFAULT 0 CHECK (is_explosive IN (0, 1)),
    is_flammable INTEGER NOT NULL DEFAULT 0 CHECK (is_flammable IN (0, 1)),
    is_oxidizer INTEGER NOT NULL DEFAULT 0 CHECK (is_oxidizer IN (0, 1)),
    is_gas_under_pressure INTEGER NOT NULL DEFAULT 0
        CHECK (is_gas_under_pressure IN (0, 1)),
    is_corrosive INTEGER NOT NULL DEFAULT 0 CHECK (is_corrosive IN (0, 1)),
    is_acute_toxic INTEGER NOT NULL DEFAULT 0
        CHECK (is_acute_toxic IN (0, 1)),
    is_harmful_irritant INTEGER NOT NULL DEFAULT 0
        CHECK (is_harmful_irritant IN (0, 1)),
    is_health_hazard INTEGER NOT NULL DEFAULT 0
        CHECK (is_health_hazard IN (0, 1)),
    is_environmental_hazard INTEGER NOT NULL DEFAULT 0
        CHECK (is_environmental_hazard IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiment_reagents (
    experiment_id INTEGER NOT NULL,
    reagent_id INTEGER NOT NULL,
    amount_used REAL NOT NULL,
    unit TEXT NOT NULL,
    PRIMARY KEY (experiment_id, reagent_id),
    FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE,
    FOREIGN KEY (reagent_id) REFERENCES reagents (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS experiment_equipment (
    experiment_id INTEGER NOT NULL,
    equipment_id INTEGER NOT NULL,
    PRIMARY KEY (experiment_id, equipment_id),
    FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE,
    FOREIGN KEY (equipment_id) REFERENCES equipment (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    FOREIGN KEY (experiment_id) REFERENCES experiments (id) ON DELETE CASCADE
);
