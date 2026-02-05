-- ============================================================
-- Миграция v11.0 - Настройки: внешний растровый слой WMTS
-- ============================================================

INSERT INTO app_settings (code, value)
VALUES
    ('url_wmts', 'https://karta.yanao.ru/ags1/rest/services/basemap/ags1_Imagery_bpla/MapServer/WMTS/1.0.0/WMTSCapabilities.xml')
ON CONFLICT (code) DO NOTHING;

