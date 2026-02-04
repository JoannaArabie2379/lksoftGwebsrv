-- ============================================================
-- Миграция v9.0 - ТУ (object_groups): дата и основание (запрос)
-- ============================================================

ALTER TABLE IF EXISTS object_groups
    ADD COLUMN IF NOT EXISTS tu_date DATE,
    ADD COLUMN IF NOT EXISTS request_basis VARCHAR(100);

