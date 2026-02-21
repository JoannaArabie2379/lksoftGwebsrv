-- ============================================================
-- Migration v21: Assumed cables scenarios (3 variants)
-- "Предполагаемые кабели" на основании инвентаризации/бирок/существующих кабелей
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS assumed_cable_scenarios (
    id SERIAL PRIMARY KEY,
    variant_no INTEGER NOT NULL CHECK (variant_no IN (1, 2, 3)),
    built_at TIMESTAMP NOT NULL DEFAULT NOW(),
    built_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    stats_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_assumed_cable_scenarios_variant_built_at
    ON assumed_cable_scenarios(variant_no, built_at DESC);

CREATE TABLE IF NOT EXISTS assumed_cables (
    id SERIAL PRIMARY KEY,
    scenario_id INTEGER NOT NULL REFERENCES assumed_cable_scenarios(id) ON DELETE CASCADE,
    direction_id INTEGER NOT NULL REFERENCES channel_directions(id) ON DELETE CASCADE,
    owner_id INTEGER REFERENCES owners(id) ON DELETE SET NULL,
    assumed_count INTEGER NOT NULL CHECK (assumed_count > 0),
    confidence NUMERIC(4,3) NOT NULL DEFAULT 0.000 CHECK (confidence >= 0 AND confidence <= 1),
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assumed_cables_scenario_id ON assumed_cables(scenario_id);
CREATE INDEX IF NOT EXISTS idx_assumed_cables_direction_id ON assumed_cables(direction_id);
CREATE INDEX IF NOT EXISTS idx_assumed_cables_owner_id ON assumed_cables(owner_id);

-- Уникальность записи по направлению и собственнику в рамках сценария,
-- включая "не определённого" собственника (owner_id IS NULL).
CREATE UNIQUE INDEX IF NOT EXISTS uq_assumed_cables_scenario_dir_owner
    ON assumed_cables(scenario_id, direction_id, COALESCE(owner_id, 0));

COMMIT;

