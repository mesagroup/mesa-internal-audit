CREATE TABLE IF NOT EXISTS controls (
    id   TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    area  TEXT NOT NULL,
    description TEXT NOT NULL,
    check_points        TEXT NOT NULL DEFAULT '[]',  -- JSON array
    expected_documents  TEXT NOT NULL DEFAULT '[]',  -- JSON array
    ctrl_type           TEXT NOT NULL DEFAULT 'ai'   -- 'ai' | 'manual'
);

CREATE TABLE IF NOT EXISTS owners (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    area TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engagements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'active',   -- active | closed
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS verifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engagement_id   INTEGER NOT NULL REFERENCES engagements(id),
    control_id      TEXT    NOT NULL,
    overall_status  TEXT    NOT NULL,
    summary         TEXT    NOT NULL DEFAULT '',
    check_points    TEXT    NOT NULL DEFAULT '[]',  -- JSON
    mitigation_plan TEXT    NOT NULL DEFAULT '[]',  -- JSON
    raw_model_output TEXT   NOT NULL DEFAULT '',
    verified_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS findings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    verification_id INTEGER REFERENCES verifications(id),
    control_id      TEXT    NOT NULL,
    engagement_id   INTEGER NOT NULL REFERENCES engagements(id),
    title           TEXT    NOT NULL,
    description     TEXT    NOT NULL DEFAULT '',
    severity        TEXT    NOT NULL DEFAULT 'medio',  -- alto | medio | basso
    status          TEXT    NOT NULL DEFAULT 'open',   -- open | validated | closed
    detected_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS action_plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id  INTEGER NOT NULL REFERENCES findings(id),
    description TEXT    NOT NULL,
    owner_name  TEXT    NOT NULL,
    due_date    TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'open',  -- open | in_progress | closed_pending | closed
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    notes       TEXT    NOT NULL DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'draft',  -- draft | active | closed
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_plan_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id       INTEGER NOT NULL REFERENCES audit_plans(id),
    control_id    TEXT    NOT NULL,
    planned_date  TEXT,                          -- ISO date target
    assigned_to   TEXT    NOT NULL DEFAULT '',
    engagement_id INTEGER REFERENCES engagements(id),  -- set when engagement created
    status        TEXT    NOT NULL DEFAULT 'planned',  -- planned | in_progress | completed
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS risk_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    control_id  TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    likelihood  INTEGER NOT NULL DEFAULT 3,  -- 1-5
    impact      INTEGER NOT NULL DEFAULT 3,  -- 1-5
    notes       TEXT    NOT NULL DEFAULT '',
    scored_by   TEXT    NOT NULL DEFAULT 'system',
    scored_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(control_id, year) ON CONFLICT REPLACE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (datetime('now')),
    user_name   TEXT NOT NULL DEFAULT 'system',
    action      TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id   TEXT,
    details     TEXT
);

-- ── Risk Assessment per Rischio ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS risk_assessments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_id     INTEGER NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
    year        INTEGER NOT NULL,
    likelihood  INTEGER NOT NULL DEFAULT 3,  -- 1-5
    impact      INTEGER NOT NULL DEFAULT 3,  -- 1-5
    notes       TEXT    NOT NULL DEFAULT '',
    scored_by   TEXT    NOT NULL DEFAULT 'system',
    scored_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(risk_id, year) ON CONFLICT REPLACE
);

-- ── Processi / Procedure / Rischi / RCM ──────────────────────────────────────

CREATE TABLE IF NOT EXISTS processes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL DEFAULT '',
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    owner       TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS procedures (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL DEFAULT '',
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS risks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL DEFAULT '',
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    category    TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Processo ↔ Procedura  (M:M)
CREATE TABLE IF NOT EXISTS process_procedure (
    process_id   INTEGER NOT NULL REFERENCES processes(id)  ON DELETE CASCADE,
    procedure_id INTEGER NOT NULL REFERENCES procedures(id) ON DELETE CASCADE,
    PRIMARY KEY (process_id, procedure_id)
);

-- Procedura ↔ Rischio  (M:M)
CREATE TABLE IF NOT EXISTS procedure_risk (
    procedure_id INTEGER NOT NULL REFERENCES procedures(id) ON DELETE CASCADE,
    risk_id      INTEGER NOT NULL REFERENCES risks(id)      ON DELETE CASCADE,
    PRIMARY KEY (procedure_id, risk_id)
);

-- Rischio ↔ Controllo  (M:M)
CREATE TABLE IF NOT EXISTS risk_control (
    risk_id    INTEGER NOT NULL REFERENCES risks(id)    ON DELETE CASCADE,
    control_id TEXT    NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    PRIMARY KEY (risk_id, control_id)
);
