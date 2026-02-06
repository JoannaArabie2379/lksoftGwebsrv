-- ============================================================
-- Миграция v14.0 - Owners numbering ranges + object_types.number_code
-- ============================================================

-- Owners: диапазоны нумерации (0 = ручной ввод)
ALTER TABLE owners
    ADD COLUMN IF NOT EXISTS range_from INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS range_to   INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN owners.range_from IS 'Диапазон нумерации объектов по собственнику: значение С (0 = ручной ввод)';
COMMENT ON COLUMN owners.range_to   IS 'Диапазон нумерации объектов по собственнику: значение ДО (0 = ручной ввод)';

-- Базовая валидация: неотрицательные, и если задан диапазон — from<=to
ALTER TABLE owners
    ADD CONSTRAINT IF NOT EXISTS owners_range_nonneg CHECK (range_from >= 0 AND range_to >= 0);

ALTER TABLE owners
    ADD CONSTRAINT IF NOT EXISTS owners_range_order CHECK (
        (range_from = 0 AND range_to = 0) OR (range_from > 0 AND range_to > 0 AND range_from <= range_to)
    );

-- Object types: код, используемый в номере объекта (по умолчанию = code)
ALTER TABLE object_types
    ADD COLUMN IF NOT EXISTS number_code VARCHAR(50);

UPDATE object_types
SET number_code = code
WHERE number_code IS NULL OR number_code = '';

ALTER TABLE object_types
    ALTER COLUMN number_code SET DEFAULT '';

COMMENT ON COLUMN object_types.number_code IS 'Код номера (префикс), используемый в формировании номера объекта';

