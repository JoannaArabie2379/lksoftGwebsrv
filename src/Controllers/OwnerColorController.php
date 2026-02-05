<?php
/**
 * Персональные цвета собственников (для легенды по собственникам)
 */

namespace App\Controllers;

use App\Core\Response;
use App\Core\Auth;

class OwnerColorController extends BaseController
{
    /**
     * GET /api/owners/colors
     * Получить список собственников с учётом персональных цветов пользователя
     */
    public function index(): void
    {
        $user = Auth::user();
        if (!$user) {
            Response::error('Требуется авторизация', 401);
        }

        try {
            $rows = $this->db->fetchAll(
                "SELECT o.id, o.code, o.name, o.short_name,
                        COALESCE(uoc.color, o.color, '#3b82f6') as color
                 FROM owners o
                 LEFT JOIN user_owner_colors uoc
                   ON uoc.owner_id = o.id AND uoc.user_id = :uid
                 ORDER BY COALESCE(o.short_name, o.name, o.code)",
                ['uid' => (int) $user['id']]
            );
            Response::success($rows);
        } catch (\PDOException $e) {
            // Если миграция не применена — отдаём глобальные цвета
            $rows = $this->db->fetchAll("SELECT id, code, name, short_name, COALESCE(color, '#3b82f6') as color FROM owners ORDER BY COALESCE(short_name, name, code)");
            Response::success($rows);
        }
    }

    /**
     * PUT /api/owners/colors/{id}
     * Установить персональный цвет собственника для текущего пользователя
     */
    public function update(string $id): void
    {
        $user = Auth::user();
        if (!$user) {
            Response::error('Требуется авторизация', 401);
        }

        $ownerId = (int) $id;
        $owner = $this->db->fetch("SELECT id FROM owners WHERE id = :id", ['id' => $ownerId]);
        if (!$owner) {
            Response::error('Собственник не найден', 404);
        }

        $color = (string) ($this->request->input('color') ?? '');
        $color = trim($color);
        if ($color === '') {
            Response::error('Не указан color', 422);
        }
        // Валидируем hex (#RGB / #RRGGBB)
        if (!preg_match('/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/', $color)) {
            Response::error('Некорректный цвет. Ожидается HEX, например #3b82f6', 422);
        }

        try {
            $this->db->query(
                "INSERT INTO user_owner_colors(user_id, owner_id, color, updated_at)
                 VALUES (:uid, :oid, :c, NOW())
                 ON CONFLICT (user_id, owner_id) DO UPDATE SET color = EXCLUDED.color, updated_at = NOW()",
                ['uid' => (int) $user['id'], 'oid' => $ownerId, 'c' => $color]
            );
        } catch (\PDOException $e) {
            Response::error('Таблица персональных цветов не создана. Примените миграцию database/migration_v12.sql', 500);
        }

        Response::success(['owner_id' => $ownerId, 'color' => $color], 'Цвет сохранён');
    }

    /**
     * DELETE /api/owners/colors/{id}
     * Сбросить персональный цвет (вернуться к глобальному)
     */
    public function destroy(string $id): void
    {
        $user = Auth::user();
        if (!$user) {
            Response::error('Требуется авторизация', 401);
        }

        $ownerId = (int) $id;

        try {
            $this->db->delete('user_owner_colors', 'user_id = :uid AND owner_id = :oid', ['uid' => (int) $user['id'], 'oid' => $ownerId]);
        } catch (\PDOException $e) {
            // ignore if table not exists
        }

        Response::success(null, 'Цвет сброшен');
    }
}

