-- ============================================================
-- Миграция v5.0 - Контракты: Арендодатель (FK owners)
-- ============================================================

ALTER TABLE IF EXISTS contracts
    ADD COLUMN IF NOT EXISTS landlord_id INTEGER REFERENCES owners(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_contracts_landlord ON contracts(landlord_id);

