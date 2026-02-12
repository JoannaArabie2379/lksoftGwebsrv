-- ============================================================
-- Миграция v16.0 - Duct cables route: allow repeated channels
-- ============================================================
--
-- Требование: при построении кабеля по точкам (колодцам) трасса должна проходить
-- через все выбранные пользователем колодцы. Для этого маршрут может требовать
-- повторного прохождения одного и того же канала (например, "заехать" в колодец
-- на тупиковой ветке и вернуться).
--
-- Ранее этому мешало ограничение уникальности:
--   UNIQUE (cable_id, cable_channel_id)
-- в таблице cable_route_channels.
--
-- Данная миграция снимает ограничение и добавляет индекс для выборок по порядку.

ALTER TABLE IF EXISTS cable_route_channels
    DROP CONSTRAINT IF EXISTS uq_cable_route_channel;

-- Индекс для частых операций: получить маршрут кабеля в порядке route_order
CREATE INDEX IF NOT EXISTS idx_cable_route_channels_cable_order
    ON cable_route_channels (cable_id, route_order);

