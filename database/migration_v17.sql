-- ============================================================
-- Миграция v17.0 - Duct cables route: enforce unique channels
-- ============================================================
--
-- Требование:
-- - маршрут кабеля НЕ может содержать повтор одного и того же канала
-- - в БД должно оставаться ограничение UNIQUE (cable_id, cable_channel_id)
--
-- Если ранее ограничение снималось/маршруты уже содержат дубликаты — удаляем
-- повторные записи (оставляем первую по route_order) и восстанавливаем constraint.

-- Индекс по порядку маршрута (полезен независимо от уникальности)
CREATE INDEX IF NOT EXISTS idx_cable_route_channels_cable_order
    ON cable_route_channels (cable_id, route_order);

-- Удаляем дубликаты (на случай, если constraint снимался ранее)
WITH ranked AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY cable_id, cable_channel_id
            ORDER BY COALESCE(route_order, 0), id
        ) AS rn
    FROM cable_route_channels
)
DELETE FROM cable_route_channels
WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_cable_route_channel'
          AND conrelid = 'cable_route_channels'::regclass
    ) THEN
        ALTER TABLE cable_route_channels
            ADD CONSTRAINT uq_cable_route_channel UNIQUE (cable_id, cable_channel_id);
    END IF;
END $$;

