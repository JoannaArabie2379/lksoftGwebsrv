-- ============================================================
-- Миграция v12.0 - Персональные цвета собственников (для легенды)
-- ============================================================

CREATE TABLE IF NOT EXISTS user_owner_colors (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    color VARCHAR(20) NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, owner_id)
);

CREATE INDEX IF NOT EXISTS idx_user_owner_colors_user ON user_owner_colors(user_id);
CREATE INDEX IF NOT EXISTS idx_user_owner_colors_owner ON user_owner_colors(owner_id);

