-- ============================================
-- ИГС Web Portal - Database Schema
-- PostgreSQL + PostGIS
-- ============================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================
-- 1. СПРАВОЧНИКИ (Reference Tables)
-- ============================================

-- 1.1 Роли пользователей
CREATE TABLE IF NOT EXISTS ref_roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ref_roles (name, description) VALUES 
    ('user', 'Пользователь'),
    ('admin', 'Администратор'),
    ('viewer', 'Визор')
ON CONFLICT (name) DO NOTHING;

-- 1.2 Виды картографических объектов
CREATE TABLE IF NOT EXISTS ref_object_kinds (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    geometry_type VARCHAR(30) NOT NULL, -- POINT, LINESTRING, MULTILINESTRING
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ref_object_kinds (name, geometry_type, description) VALUES 
    ('well', 'POINT', 'Колодец кабельной канализации'),
    ('channel_direction', 'LINESTRING', 'Направление канала кабельной канализации'),
    ('cable_channel', 'LINESTRING', 'Канал кабельной канализации'),
    ('marker_post', 'POINT', 'Указательный столбик'),
    ('ground_cable', 'LINESTRING', 'Кабель в грунте'),
    ('duct_cable', 'LINESTRING', 'Кабель в кабельной канализации'),
    ('aerial_cable', 'LINESTRING', 'Кабель воздушными переходами')
ON CONFLICT (name) DO NOTHING;

-- 1.3 Типы колодцев
CREATE TABLE IF NOT EXISTS ref_well_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(20),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ref_well_types (name, code, description) VALUES 
    ('ККС-1', 'KKS1', 'Колодец кабельной связи тип 1'),
    ('ККС-2', 'KKS2', 'Колодец кабельной связи тип 2'),
    ('ККС-3', 'KKS3', 'Колодец кабельной связи тип 3'),
    ('ККС-4', 'KKS4', 'Колодец кабельной связи тип 4'),
    ('ККС-5', 'KKS5', 'Колодец кабельной связи тип 5'),
    ('ККСП', 'KKSP', 'Колодец кабельной связи проходной')
ON CONFLICT (name) DO NOTHING;

-- 1.4 Типы каналов
CREATE TABLE IF NOT EXISTS ref_channel_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    diameter_mm INTEGER,
    material VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ref_channel_types (name, diameter_mm, material, description) VALUES 
    ('Асбестоцементная труба 100мм', 100, 'Асбестоцемент', 'АЦТ 100'),
    ('ПНД труба 63мм', 63, 'ПНД', 'Полиэтилен низкого давления'),
    ('ПНД труба 110мм', 110, 'ПНД', 'Полиэтилен низкого давления'),
    ('Стальная труба 100мм', 100, 'Сталь', 'Стальная защитная труба')
ON CONFLICT (name) DO NOTHING;

-- 1.5 Типы кабелей
CREATE TABLE IF NOT EXISTS ref_cable_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    fiber_count INTEGER,
    cable_type VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ref_cable_types (name, fiber_count, cable_type, description) VALUES 
    ('ОКГТ-24', 24, 'ОКГТ', 'Оптический кабель грозотрос'),
    ('ОКБ-48', 48, 'ОКБ', 'Оптический кабель бронированный'),
    ('ДПС-12', 12, 'ДПС', 'Кабель для прокладки в грунт'),
    ('ОКСН-8', 8, 'ОКСН', 'Кабель самонесущий')
ON CONFLICT (name) DO NOTHING;

-- 1.6 Типы указательных столбиков
CREATE TABLE IF NOT EXISTS ref_marker_post_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    material VARCHAR(50),
    height_cm INTEGER,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ref_marker_post_types (name, material, height_cm, description) VALUES 
    ('Железобетонный', 'Железобетон', 120, 'Стандартный ЖБ столбик'),
    ('Пластиковый', 'Пластик', 100, 'Пластиковый указательный столбик'),
    ('Металлический', 'Металл', 120, 'Металлический столбик')
ON CONFLICT (name) DO NOTHING;

-- 1.7 Состояния объектов
CREATE TABLE IF NOT EXISTS ref_object_states (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    color VARCHAR(7), -- HEX color for visualization
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO ref_object_states (name, color, description) VALUES 
    ('planned', '#3498db', 'Проектируемый'),
    ('emergency', '#e74c3c', 'Аварийный'),
    ('satisfactory', '#27ae60', 'Удовлетворительный')
ON CONFLICT (name) DO NOTHING;

-- 1.8 Собственники
CREATE TABLE IF NOT EXISTS owners (
    id SERIAL PRIMARY KEY,
    organization_name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    phone VARCHAR(50),
    email VARCHAR(100),
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1.9 Контракты
CREATE TABLE IF NOT EXISTS contracts (
    id SERIAL PRIMARY KEY,
    contract_number VARCHAR(100) NOT NULL,
    contract_date DATE NOT NULL,
    owner_id INTEGER REFERENCES owners(id) ON DELETE SET NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contracts_owner ON contracts(owner_id);

-- ============================================
-- 2. ПОЛЬЗОВАТЕЛИ
-- ============================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id INTEGER REFERENCES ref_roles(id) ON DELETE SET NULL,
    full_name VARCHAR(255),
    email VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ============================================
-- 3. СТИЛИ ОТОБРАЖЕНИЯ
-- ============================================

CREATE TABLE IF NOT EXISTS display_styles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    object_kind_id INTEGER REFERENCES ref_object_kinds(id) ON DELETE CASCADE,
    object_state_id INTEGER REFERENCES ref_object_states(id) ON DELETE SET NULL,
    
    -- Style properties
    stroke_color VARCHAR(7) DEFAULT '#3388ff',
    stroke_width INTEGER DEFAULT 3,
    stroke_opacity DECIMAL(3,2) DEFAULT 1.0,
    fill_color VARCHAR(7) DEFAULT '#3388ff',
    fill_opacity DECIMAL(3,2) DEFAULT 0.2,
    
    -- Point styles
    point_radius INTEGER DEFAULT 8,
    icon_url VARCHAR(255),
    icon_size INTEGER DEFAULT 24,
    
    -- Line styles
    dash_array VARCHAR(50), -- e.g., '5, 10'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_styles_kind ON display_styles(object_kind_id);
CREATE INDEX IF NOT EXISTS idx_styles_state ON display_styles(object_state_id);

-- Default styles
INSERT INTO display_styles (name, is_default, object_kind_id, stroke_color, fill_color, point_radius) 
SELECT 'Колодец - стандарт', TRUE, id, '#2ecc71', '#27ae60', 10
FROM ref_object_kinds WHERE name = 'well'
ON CONFLICT DO NOTHING;

INSERT INTO display_styles (name, is_default, object_kind_id, stroke_color, stroke_width) 
SELECT 'Направление - стандарт', TRUE, id, '#3498db', 4
FROM ref_object_kinds WHERE name = 'channel_direction'
ON CONFLICT DO NOTHING;

INSERT INTO display_styles (name, is_default, object_kind_id, stroke_color, fill_color, point_radius) 
SELECT 'Столбик - стандарт', TRUE, id, '#f39c12', '#f1c40f', 8
FROM ref_object_kinds WHERE name = 'marker_post'
ON CONFLICT DO NOTHING;

INSERT INTO display_styles (name, is_default, object_kind_id, stroke_color, stroke_width, dash_array) 
SELECT 'Кабель в грунте - стандарт', TRUE, id, '#e74c3c', 3, '10, 5'
FROM ref_object_kinds WHERE name = 'ground_cable'
ON CONFLICT DO NOTHING;

-- ============================================
-- 4. ОСНОВНЫЕ ТАБЛИЦЫ ОБЪЕКТОВ
-- ============================================

-- 4.1 Колодцы кабельной канализации
CREATE TABLE IF NOT EXISTS wells (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    
    -- Geometry in both coordinate systems
    geom_wgs84 GEOMETRY(POINT, 4326),
    geom_msk86 GEOMETRY(POINT, 2502),
    
    -- References
    owner_id INTEGER REFERENCES owners(id) ON DELETE SET NULL,
    object_kind_id INTEGER REFERENCES ref_object_kinds(id) ON DELETE SET NULL,
    well_type_id INTEGER REFERENCES ref_well_types(id) ON DELETE SET NULL,
    state_id INTEGER REFERENCES ref_object_states(id) ON DELETE SET NULL,
    
    -- Additional info
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_wells_geom_wgs84 ON wells USING GIST(geom_wgs84);
CREATE INDEX IF NOT EXISTS idx_wells_geom_msk86 ON wells USING GIST(geom_msk86);
CREATE INDEX IF NOT EXISTS idx_wells_owner ON wells(owner_id);
CREATE INDEX IF NOT EXISTS idx_wells_type ON wells(well_type_id);
CREATE INDEX IF NOT EXISTS idx_wells_state ON wells(state_id);

-- 4.2 Направления канала кабельной канализации
CREATE TABLE IF NOT EXISTS channel_directions (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    
    -- Geometry
    geom_wgs84 GEOMETRY(LINESTRING, 4326),
    geom_msk86 GEOMETRY(LINESTRING, 2502),
    
    -- References
    owner_id INTEGER REFERENCES owners(id) ON DELETE SET NULL,
    object_kind_id INTEGER REFERENCES ref_object_kinds(id) ON DELETE SET NULL,
    
    -- Start and end wells
    start_well_id INTEGER REFERENCES wells(id) ON DELETE SET NULL,
    end_well_id INTEGER REFERENCES wells(id) ON DELETE SET NULL,
    
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ch_dir_geom_wgs84 ON channel_directions USING GIST(geom_wgs84);
CREATE INDEX IF NOT EXISTS idx_ch_dir_geom_msk86 ON channel_directions USING GIST(geom_msk86);
CREATE INDEX IF NOT EXISTS idx_ch_dir_start_well ON channel_directions(start_well_id);
CREATE INDEX IF NOT EXISTS idx_ch_dir_end_well ON channel_directions(end_well_id);

-- 4.3 Каналы кабельной канализации (до 16 на направление)
CREATE TABLE IF NOT EXISTS cable_channels (
    id SERIAL PRIMARY KEY,
    channel_direction_id INTEGER NOT NULL REFERENCES channel_directions(id) ON DELETE CASCADE,
    channel_order INTEGER NOT NULL CHECK (channel_order >= 1 AND channel_order <= 16),
    
    -- References
    channel_type_id INTEGER REFERENCES ref_channel_types(id) ON DELETE SET NULL,
    state_id INTEGER REFERENCES ref_object_states(id) ON DELETE SET NULL,
    
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(channel_direction_id, channel_order)
);

CREATE INDEX IF NOT EXISTS idx_cable_ch_direction ON cable_channels(channel_direction_id);
CREATE INDEX IF NOT EXISTS idx_cable_ch_type ON cable_channels(channel_type_id);

-- 4.4 Указательные столбики
CREATE TABLE IF NOT EXISTS marker_posts (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    
    -- Geometry
    geom_wgs84 GEOMETRY(POINT, 4326),
    geom_msk86 GEOMETRY(POINT, 2502),
    
    -- References
    owner_id INTEGER REFERENCES owners(id) ON DELETE SET NULL,
    object_kind_id INTEGER REFERENCES ref_object_kinds(id) ON DELETE SET NULL,
    marker_type_id INTEGER REFERENCES ref_marker_post_types(id) ON DELETE SET NULL,
    state_id INTEGER REFERENCES ref_object_states(id) ON DELETE SET NULL,
    
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_marker_geom_wgs84 ON marker_posts USING GIST(geom_wgs84);
CREATE INDEX IF NOT EXISTS idx_marker_geom_msk86 ON marker_posts USING GIST(geom_msk86);

-- 4.5 Кабель в грунте
CREATE TABLE IF NOT EXISTS ground_cables (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    
    -- Geometry
    geom_wgs84 GEOMETRY(LINESTRING, 4326),
    geom_msk86 GEOMETRY(LINESTRING, 2502),
    
    -- References
    owner_id INTEGER REFERENCES owners(id) ON DELETE SET NULL,
    object_kind_id INTEGER REFERENCES ref_object_kinds(id) ON DELETE SET NULL,
    cable_type_id INTEGER REFERENCES ref_cable_types(id) ON DELETE SET NULL,
    contract_id INTEGER REFERENCES contracts(id) ON DELETE SET NULL,
    state_id INTEGER REFERENCES ref_object_states(id) ON DELETE SET NULL,
    
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_ground_cable_geom_wgs84 ON ground_cables USING GIST(geom_wgs84);
CREATE INDEX IF NOT EXISTS idx_ground_cable_geom_msk86 ON ground_cables USING GIST(geom_msk86);

-- 4.6 Кабель воздушными переходами
CREATE TABLE IF NOT EXISTS aerial_cables (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    
    -- Geometry
    geom_wgs84 GEOMETRY(LINESTRING, 4326),
    geom_msk86 GEOMETRY(LINESTRING, 2502),
    
    -- References
    owner_id INTEGER REFERENCES owners(id) ON DELETE SET NULL,
    object_kind_id INTEGER REFERENCES ref_object_kinds(id) ON DELETE SET NULL,
    cable_type_id INTEGER REFERENCES ref_cable_types(id) ON DELETE SET NULL,
    contract_id INTEGER REFERENCES contracts(id) ON DELETE SET NULL,
    state_id INTEGER REFERENCES ref_object_states(id) ON DELETE SET NULL,
    
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_aerial_cable_geom_wgs84 ON aerial_cables USING GIST(geom_wgs84);
CREATE INDEX IF NOT EXISTS idx_aerial_cable_geom_msk86 ON aerial_cables USING GIST(geom_msk86);

-- 4.7 Кабель в кабельной канализации
CREATE TABLE IF NOT EXISTS duct_cables (
    id SERIAL PRIMARY KEY,
    number VARCHAR(50) NOT NULL,
    
    -- Geometry (should match wells and directions)
    geom_wgs84 GEOMETRY(LINESTRING, 4326),
    geom_msk86 GEOMETRY(LINESTRING, 2502),
    
    -- References
    owner_id INTEGER REFERENCES owners(id) ON DELETE SET NULL,
    object_kind_id INTEGER REFERENCES ref_object_kinds(id) ON DELETE SET NULL,
    cable_type_id INTEGER REFERENCES ref_cable_types(id) ON DELETE SET NULL,
    contract_id INTEGER REFERENCES contracts(id) ON DELETE SET NULL,
    state_id INTEGER REFERENCES ref_object_states(id) ON DELETE SET NULL,
    
    description TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_duct_cable_geom_wgs84 ON duct_cables USING GIST(geom_wgs84);
CREATE INDEX IF NOT EXISTS idx_duct_cable_geom_msk86 ON duct_cables USING GIST(geom_msk86);

-- Связь кабеля с каналами (многие ко многим)
CREATE TABLE IF NOT EXISTS duct_cable_channels (
    id SERIAL PRIMARY KEY,
    duct_cable_id INTEGER NOT NULL REFERENCES duct_cables(id) ON DELETE CASCADE,
    cable_channel_id INTEGER NOT NULL REFERENCES cable_channels(id) ON DELETE CASCADE,
    UNIQUE(duct_cable_id, cable_channel_id)
);

-- ============================================
-- 5. ФОТОГРАФИИ ОБЪЕКТОВ
-- ============================================

CREATE TABLE IF NOT EXISTS object_photos (
    id SERIAL PRIMARY KEY,
    
    -- Polymorphic reference
    object_type VARCHAR(50) NOT NULL, -- wells, marker_posts, cable_channels, ground_cables, etc.
    object_id INTEGER NOT NULL,
    
    -- Photo data
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(50),
    
    -- Metadata
    description TEXT,
    photo_order INTEGER DEFAULT 1,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_photos_object ON object_photos(object_type, object_id);

-- Constraint: max 10 photos per object
CREATE OR REPLACE FUNCTION check_max_photos()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM object_photos 
        WHERE object_type = NEW.object_type AND object_id = NEW.object_id) >= 10 THEN
        RAISE EXCEPTION 'Maximum 10 photos allowed per object';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_check_max_photos ON object_photos;
CREATE TRIGGER trigger_check_max_photos
    BEFORE INSERT ON object_photos
    FOR EACH ROW
    EXECUTE FUNCTION check_max_photos();

-- ============================================
-- 6. ИМПОРТ ДАННЫХ (журнал импорта)
-- ============================================

CREATE TABLE IF NOT EXISTS import_logs (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL, -- csv, tab
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    total_records INTEGER DEFAULT 0,
    imported_records INTEGER DEFAULT 0,
    failed_records INTEGER DEFAULT 0,
    error_log TEXT,
    
    column_mapping JSONB, -- mapping of file columns to DB columns
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================
-- 7. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
-- ============================================

-- Function to transform coordinates from WGS84 to MSK86
CREATE OR REPLACE FUNCTION transform_to_msk86(geom_wgs84 GEOMETRY)
RETURNS GEOMETRY AS $$
BEGIN
    RETURN ST_Transform(geom_wgs84, 2502);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to transform coordinates from MSK86 to WGS84
CREATE OR REPLACE FUNCTION transform_to_wgs84(geom_msk86 GEOMETRY)
RETURNS GEOMETRY AS $$
BEGIN
    RETURN ST_Transform(geom_msk86, 4326);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Trigger to auto-populate MSK86 geometry when WGS84 is set
CREATE OR REPLACE FUNCTION sync_geometries()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.geom_wgs84 IS NOT NULL AND NEW.geom_msk86 IS NULL THEN
        NEW.geom_msk86 := ST_Transform(NEW.geom_wgs84, 2502);
    ELSIF NEW.geom_msk86 IS NOT NULL AND NEW.geom_wgs84 IS NULL THEN
        NEW.geom_wgs84 := ST_Transform(NEW.geom_msk86, 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all geometry tables
DROP TRIGGER IF EXISTS trigger_sync_geom_wells ON wells;
CREATE TRIGGER trigger_sync_geom_wells
    BEFORE INSERT OR UPDATE ON wells
    FOR EACH ROW EXECUTE FUNCTION sync_geometries();

DROP TRIGGER IF EXISTS trigger_sync_geom_ch_dir ON channel_directions;
CREATE TRIGGER trigger_sync_geom_ch_dir
    BEFORE INSERT OR UPDATE ON channel_directions
    FOR EACH ROW EXECUTE FUNCTION sync_geometries();

DROP TRIGGER IF EXISTS trigger_sync_geom_markers ON marker_posts;
CREATE TRIGGER trigger_sync_geom_markers
    BEFORE INSERT OR UPDATE ON marker_posts
    FOR EACH ROW EXECUTE FUNCTION sync_geometries();

DROP TRIGGER IF EXISTS trigger_sync_geom_ground ON ground_cables;
CREATE TRIGGER trigger_sync_geom_ground
    BEFORE INSERT OR UPDATE ON ground_cables
    FOR EACH ROW EXECUTE FUNCTION sync_geometries();

DROP TRIGGER IF EXISTS trigger_sync_geom_aerial ON aerial_cables;
CREATE TRIGGER trigger_sync_geom_aerial
    BEFORE INSERT OR UPDATE ON aerial_cables
    FOR EACH ROW EXECUTE FUNCTION sync_geometries();

DROP TRIGGER IF EXISTS trigger_sync_geom_duct ON duct_cables;
CREATE TRIGGER trigger_sync_geom_duct
    BEFORE INSERT OR UPDATE ON duct_cables
    FOR EACH ROW EXECUTE FUNCTION sync_geometries();

-- ============================================
-- 8. ПРЕДСТАВЛЕНИЯ ДЛЯ КАРТЫ
-- ============================================

-- View for all point objects
CREATE OR REPLACE VIEW v_map_points AS
SELECT 
    'well' as layer,
    w.id,
    w.number,
    ST_AsGeoJSON(w.geom_wgs84)::jsonb as geojson_wgs84,
    ST_AsGeoJSON(w.geom_msk86)::jsonb as geojson_msk86,
    wt.name as type_name,
    os.name as state_name,
    os.color as state_color,
    o.organization_name as owner_name
FROM wells w
LEFT JOIN ref_well_types wt ON w.well_type_id = wt.id
LEFT JOIN ref_object_states os ON w.state_id = os.id
LEFT JOIN owners o ON w.owner_id = o.id

UNION ALL

SELECT 
    'marker_post' as layer,
    mp.id,
    mp.number,
    ST_AsGeoJSON(mp.geom_wgs84)::jsonb as geojson_wgs84,
    ST_AsGeoJSON(mp.geom_msk86)::jsonb as geojson_msk86,
    mpt.name as type_name,
    os.name as state_name,
    os.color as state_color,
    o.organization_name as owner_name
FROM marker_posts mp
LEFT JOIN ref_marker_post_types mpt ON mp.marker_type_id = mpt.id
LEFT JOIN ref_object_states os ON mp.state_id = os.id
LEFT JOIN owners o ON mp.owner_id = o.id;

-- View for all line objects
CREATE OR REPLACE VIEW v_map_lines AS
SELECT 
    'channel_direction' as layer,
    cd.id,
    cd.number,
    ST_AsGeoJSON(cd.geom_wgs84)::jsonb as geojson_wgs84,
    ST_AsGeoJSON(cd.geom_msk86)::jsonb as geojson_msk86,
    NULL as type_name,
    NULL as state_name,
    '#3498db' as state_color,
    o.organization_name as owner_name
FROM channel_directions cd
LEFT JOIN owners o ON cd.owner_id = o.id

UNION ALL

SELECT 
    'ground_cable' as layer,
    gc.id,
    gc.number,
    ST_AsGeoJSON(gc.geom_wgs84)::jsonb as geojson_wgs84,
    ST_AsGeoJSON(gc.geom_msk86)::jsonb as geojson_msk86,
    ct.name as type_name,
    os.name as state_name,
    COALESCE(os.color, '#e74c3c') as state_color,
    o.organization_name as owner_name
FROM ground_cables gc
LEFT JOIN ref_cable_types ct ON gc.cable_type_id = ct.id
LEFT JOIN ref_object_states os ON gc.state_id = os.id
LEFT JOIN owners o ON gc.owner_id = o.id

UNION ALL

SELECT 
    'aerial_cable' as layer,
    ac.id,
    ac.number,
    ST_AsGeoJSON(ac.geom_wgs84)::jsonb as geojson_wgs84,
    ST_AsGeoJSON(ac.geom_msk86)::jsonb as geojson_msk86,
    ct.name as type_name,
    os.name as state_name,
    COALESCE(os.color, '#9b59b6') as state_color,
    o.organization_name as owner_name
FROM aerial_cables ac
LEFT JOIN ref_cable_types ct ON ac.cable_type_id = ct.id
LEFT JOIN ref_object_states os ON ac.state_id = os.id
LEFT JOIN owners o ON ac.owner_id = o.id

UNION ALL

SELECT 
    'duct_cable' as layer,
    dc.id,
    dc.number,
    ST_AsGeoJSON(dc.geom_wgs84)::jsonb as geojson_wgs84,
    ST_AsGeoJSON(dc.geom_msk86)::jsonb as geojson_msk86,
    ct.name as type_name,
    os.name as state_name,
    COALESCE(os.color, '#1abc9c') as state_color,
    o.organization_name as owner_name
FROM duct_cables dc
LEFT JOIN ref_cable_types ct ON dc.cable_type_id = ct.id
LEFT JOIN ref_object_states os ON dc.state_id = os.id
LEFT JOIN owners o ON dc.owner_id = o.id;

-- ============================================
-- DONE
-- ============================================
