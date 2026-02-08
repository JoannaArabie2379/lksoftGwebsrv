<?php
/**
 * Контроллер колодцев кабельной канализации
 */

namespace App\Controllers;

use App\Core\Response;
use App\Core\Auth;

class WellController extends BaseController
{
    /**
     * GET /api/wells
     * Список колодцев
     */
    public function index(): void
    {
        $pagination = $this->getPagination();
        
        $filters = $this->buildFilters([
            'owner_id' => 'w.owner_id',
            'type_id' => 'w.type_id',
            'kind_id' => 'w.kind_id',
            'status_id' => 'w.status_id',
            '_search' => ['w.number', 'w.notes'],
        ]);

        $where = $filters['where'];
        $params = $filters['params'];

        // Общее количество (передаём алиас 'w' для корректной работы с WHERE)
        $total = $this->getTotal('wells', $where, $params, 'w');

        // Данные с джойнами
        $sql = "SELECT w.id, w.number, 
                       ST_X(w.geom_wgs84) as longitude, ST_Y(w.geom_wgs84) as latitude,
                       ST_X(w.geom_msk86) as x_msk86, ST_Y(w.geom_msk86) as y_msk86,
                       w.owner_id, w.type_id, w.kind_id, w.status_id,
                       w.depth, w.material, w.installation_date, w.notes,
                       o.name as owner_name, o.short_name as owner_short,
                       ot.name as type_name, ot.icon as type_icon, ot.color as type_color,
                       ok.name as kind_name,
                       os.name as status_name, os.color as status_color,
                       w.created_at, w.updated_at
                FROM wells w
                LEFT JOIN owners o ON w.owner_id = o.id
                LEFT JOIN object_types ot ON w.type_id = ot.id
                LEFT JOIN object_kinds ok ON w.kind_id = ok.id
                LEFT JOIN object_status os ON w.status_id = os.id";
        
        if ($where) {
            $sql .= " WHERE {$where}";
        }
        $orderBy = $this->getOrderBy([
            'number' => 'w.number',
            'created_at' => 'w.created_at',
        ], 'w.number');
        $sql .= " ORDER BY {$orderBy} LIMIT :limit OFFSET :offset";
        
        $params['limit'] = $pagination['limit'];
        $params['offset'] = $pagination['offset'];
        
        $data = $this->db->fetchAll($sql, $params);

        Response::paginated($data, $total, $pagination['page'], $pagination['limit']);
    }

    /**
     * GET /api/wells/geojson
     * GeoJSON всех колодцев для карты
     */
    public function geojson(): void
    {
        $filters = $this->buildFilters([
            'owner_id' => 'w.owner_id',
            'type_id' => 'w.type_id',
            'kind_id' => 'w.kind_id',
            'status_id' => 'w.status_id',
        ]);

        $where = $filters['where'];
        $params = $filters['params'];

        // Обязательно фильтруем по наличию геометрии
        $geomCondition = 'w.geom_wgs84 IS NOT NULL';
        if ($where) {
            $where = "{$geomCondition} AND ({$where})";
        } else {
            $where = $geomCondition;
        }

        $sql = "SELECT w.id, w.number, 
                       ST_AsGeoJSON(w.geom_wgs84)::json as geometry,
                       w.owner_id, w.type_id, w.kind_id, w.status_id,
                       o.name as owner_name,
                       ot.name as type_name, ot.color as type_color,
                       ok.name as kind_name,
                       os.name as status_name, os.color as status_color
                FROM wells w
                LEFT JOIN owners o ON w.owner_id = o.id
                LEFT JOIN object_types ot ON w.type_id = ot.id
                LEFT JOIN object_kinds ok ON w.kind_id = ok.id
                LEFT JOIN object_status os ON w.status_id = os.id
                WHERE {$where}";
        
        $data = $this->db->fetchAll($sql, $params);

        $features = [];
        foreach ($data as $row) {
            $geometry = is_string($row['geometry']) ? json_decode($row['geometry'], true) : $row['geometry'];
            unset($row['geometry']);
            
            // Пропускаем записи с невалидной геометрией
            if (empty($geometry) || !isset($geometry['type'])) {
                continue;
            }
            
            $features[] = [
                'type' => 'Feature',
                'geometry' => $geometry,
                'properties' => $row,
            ];
        }

        Response::geojson($features, ['layer' => 'wells', 'count' => count($features)]);
    }

    /**
     * GET /api/wells/{id}
     * Получение колодца
     */
    public function show(string $id): void
    {
        $well = $this->db->fetch(
            "SELECT w.*, 
                    ST_X(w.geom_wgs84) as longitude, ST_Y(w.geom_wgs84) as latitude,
                    ST_X(w.geom_msk86) as x_msk86, ST_Y(w.geom_msk86) as y_msk86,
                    o.name as owner_name,
                    ot.name as type_name,
                    ok.name as kind_name,
                    os.name as status_name, os.color as status_color,
                    uc.login as created_by_login,
                    uu.login as updated_by_login
             FROM wells w
             LEFT JOIN owners o ON w.owner_id = o.id
             LEFT JOIN object_types ot ON w.type_id = ot.id
             LEFT JOIN object_kinds ok ON w.kind_id = ok.id
             LEFT JOIN object_status os ON w.status_id = os.id
             LEFT JOIN users uc ON w.created_by = uc.id
             LEFT JOIN users uu ON w.updated_by = uu.id
             WHERE w.id = :id",
            ['id' => (int) $id]
        );

        if (!$well) {
            Response::error('Колодец не найден', 404);
        }

        // Получаем фотографии
        $photos = $this->db->fetchAll(
            "SELECT id, filename, original_filename, file_path, description, created_at 
             FROM object_photos 
             WHERE object_table = 'wells' AND object_id = :id 
             ORDER BY sort_order",
            ['id' => (int) $id]
        );
        $well['photos'] = $photos;

        // Получаем связанные направления
        $directions = $this->db->fetchAll(
            "SELECT cd.id, cd.number, 
                    CASE WHEN cd.start_well_id = :id THEN 'start' ELSE 'end' END as connection_type,
                    CASE WHEN cd.start_well_id = :id THEN ew.number ELSE sw.number END as connected_well_number
             FROM channel_directions cd
             LEFT JOIN wells sw ON cd.start_well_id = sw.id
             LEFT JOIN wells ew ON cd.end_well_id = ew.id
             WHERE cd.start_well_id = :id OR cd.end_well_id = :id",
            ['id' => (int) $id]
        );
        $well['directions'] = $directions;

        Response::success($well);
    }

    /**
     * POST /api/wells
     * Создание колодца
     */
    public function store(): void
    {
        $this->checkWriteAccess();

        $errors = $this->request->validate([
            'number' => 'required|string|max:50',
            'owner_id' => 'required|integer',
            'type_id' => 'required|integer',
            'kind_id' => 'required|integer',
            'status_id' => 'required|integer',
        ]);

        if (!empty($errors)) {
            Response::error('Ошибка валидации', 422, $errors);
        }

        $data = $this->request->only([
            'number', 'owner_id', 'type_id', 'kind_id', 'status_id',
            'depth', 'material', 'installation_date', 'notes'
        ]);

        // Убедиться, что все необязательные поля присутствуют (даже если null)
        $optionalFields = ['depth', 'material', 'installation_date', 'notes'];
        foreach ($optionalFields as $field) {
            if (!array_key_exists($field, $data)) {
                $data[$field] = null;
            }
        }

        // Координаты - либо WGS84, либо МСК86
        $longitude = $this->request->input('longitude');
        $latitude = $this->request->input('latitude');
        $xMsk86 = $this->request->input('x_msk86');
        $yMsk86 = $this->request->input('y_msk86');

        if (!$longitude && !$xMsk86) {
            Response::error('Необходимо указать координаты (WGS84 или МСК86)', 422);
        }

        $user = Auth::user();
        $data['created_by'] = $user['id'];
        $data['updated_by'] = $user['id'];

        try {
            $this->db->beginTransaction();

            // Создаём геометрию
            if ($longitude && $latitude) {
                // WGS84 -> автоматически пересчитается в МСК86 триггером
                $sql = "INSERT INTO wells (number, geom_wgs84, owner_id, type_id, kind_id, status_id, 
                                           depth, material, installation_date, notes, created_by, updated_by)
                        VALUES (:number, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), 
                                :owner_id, :type_id, :kind_id, :status_id,
                                :depth, :material, :installation_date, :notes, :created_by, :updated_by)
                        RETURNING id";
                $data['lon'] = $longitude;
                $data['lat'] = $latitude;
            } else {
                // МСК86 -> WGS84
                // PostgreSQL PDO не поддерживает повторное использование именованных параметров,
                // поэтому используем подзапрос с CTE для создания геометрии один раз
                $sql = "WITH geom_point AS (
                            SELECT ST_SetSRID(ST_MakePoint(:x, :y), 200004) as msk86_point
                        )
                        INSERT INTO wells (number, geom_wgs84, geom_msk86, owner_id, type_id, kind_id, status_id,
                                           depth, material, installation_date, notes, created_by, updated_by)
                        SELECT :number, 
                               ST_Transform(msk86_point, 4326),
                               msk86_point,
                               :owner_id, :type_id, :kind_id, :status_id,
                               :depth, :material, :installation_date, :notes, :created_by, :updated_by
                        FROM geom_point
                        RETURNING id";
                $data['x'] = $xMsk86;
                $data['y'] = $yMsk86;
            }

            $stmt = $this->db->query($sql, $data);
            $id = $stmt->fetchColumn();

            $this->db->commit();

            $well = $this->db->fetch(
                "SELECT *, ST_X(geom_wgs84) as longitude, ST_Y(geom_wgs84) as latitude,
                        ST_X(geom_msk86) as x_msk86, ST_Y(geom_msk86) as y_msk86
                 FROM wells WHERE id = :id",
                ['id' => $id]
            );

            $this->log('create', 'wells', $id, null, $well);

            Response::success($well, 'Колодец создан', 201);
        } catch (\PDOException $e) {
            $this->db->rollback();
            if (strpos($e->getMessage(), 'unique') !== false) {
                Response::error('Колодец с таким номером уже существует', 400);
            }
            throw $e;
        }
    }

    /**
     * PUT /api/wells/{id}
     * Обновление колодца
     */
    public function update(string $id): void
    {
        $this->checkWriteAccess();
        $wellId = (int) $id;

        $oldWell = $this->db->fetch("SELECT * FROM wells WHERE id = :id", ['id' => $wellId]);
        if (!$oldWell) {
            Response::error('Колодец не найден', 404);
        }

        $data = $this->request->only([
            'number', 'owner_id', 'type_id', 'kind_id', 'status_id',
            'depth', 'material', 'installation_date', 'notes'
        ]);
        $data = array_filter($data, fn($v) => $v !== null);

        $user = Auth::user();
        $data['updated_by'] = $user['id'];

        try {
            $this->db->beginTransaction();

            // Обновляем координаты если переданы
            $longitude = $this->request->input('longitude');
            $latitude = $this->request->input('latitude');
            $xMsk86 = $this->request->input('x_msk86');
            $yMsk86 = $this->request->input('y_msk86');

            if ($longitude && $latitude) {
                // PostgreSQL PDO не поддерживает повторное использование именованных параметров
                $this->db->query(
                    "UPDATE wells SET 
                        geom_wgs84 = wgs_point.geom,
                        geom_msk86 = ST_Transform(wgs_point.geom, 200004)
                     FROM (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) as geom) as wgs_point
                     WHERE wells.id = :id",
                    ['lon' => $longitude, 'lat' => $latitude, 'id' => $wellId]
                );
            } elseif ($xMsk86 && $yMsk86) {
                // PostgreSQL PDO не поддерживает повторное использование именованных параметров
                $this->db->query(
                    "UPDATE wells SET 
                        geom_msk86 = msk_point.geom,
                        geom_wgs84 = ST_Transform(msk_point.geom, 4326)
                     FROM (SELECT ST_SetSRID(ST_MakePoint(:x, :y), 200004) as geom) as msk_point
                     WHERE wells.id = :id",
                    ['x' => $xMsk86, 'y' => $yMsk86, 'id' => $wellId]
                );
            }

            // Обновляем остальные поля
            if (!empty($data)) {
                $this->db->update('wells', $data, 'id = :id', ['id' => $wellId]);
            }

            $this->db->commit();

            $well = $this->db->fetch(
                "SELECT *, ST_X(geom_wgs84) as longitude, ST_Y(geom_wgs84) as latitude,
                        ST_X(geom_msk86) as x_msk86, ST_Y(geom_msk86) as y_msk86
                 FROM wells WHERE id = :id",
                ['id' => $wellId]
            );

            $this->log('update', 'wells', $wellId, $oldWell, $well);

            Response::success($well, 'Колодец обновлён');
        } catch (\PDOException $e) {
            $this->db->rollback();
            if (strpos($e->getMessage(), 'unique') !== false) {
                Response::error('Колодец с таким номером уже существует', 400);
            }
            throw $e;
        }
    }

    /**
     * DELETE /api/wells/{id}
     * Удаление колодца
     */
    public function destroy(string $id): void
    {
        $this->checkDeleteAccess();
        $wellId = (int) $id;

        $well = $this->db->fetch("SELECT * FROM wells WHERE id = :id", ['id' => $wellId]);
        if (!$well) {
            Response::error('Колодец не найден', 404);
        }

        // Проверяем связанные направления
        $directions = $this->db->fetch(
            "SELECT COUNT(*) as cnt FROM channel_directions WHERE start_well_id = :id OR end_well_id = :id",
            ['id' => $wellId]
        );
        if ($directions['cnt'] > 0) {
            Response::error('Нельзя удалить колодец, так как он связан с направлениями каналов', 400);
        }

        try {
            // Удаляем фотографии
            $this->db->delete('object_photos', "object_table = 'wells' AND object_id = :id", ['id' => $wellId]);
            
            // Удаляем колодец
            $this->db->delete('wells', 'id = :id', ['id' => $wellId]);

            $this->log('delete', 'wells', $wellId, $well, null);

            Response::success(null, 'Колодец удалён');
        } catch (\PDOException $e) {
            if (strpos($e->getMessage(), 'foreign key') !== false) {
                Response::error('Нельзя удалить колодец, так как он используется в других объектах', 400);
            }
            throw $e;
        }
    }

    /**
     * POST /api/wells/{id}/dismantle
     * Демонтаж колодца (только если связано ровно 2 направления)
     */
    public function dismantle(string $id): void
    {
        $this->checkWriteAccess();
        $wellId = (int) $id;

        $well = $this->db->fetch("SELECT id, number FROM wells WHERE id = :id", ['id' => $wellId]);
        if (!$well) {
            Response::error('Колодец не найден', 404);
        }

        $directions = $this->db->fetchAll(
            "SELECT id, start_well_id, end_well_id, owner_id, type_id
             FROM channel_directions
             WHERE start_well_id = :id OR end_well_id = :id
             ORDER BY id",
            ['id' => $wellId]
        );

        if (count($directions) !== 2) {
            Response::error('Для демонтажа требуется ровно 2 связанных направления', 422);
        }

        $dirA = $directions[0];
        $dirB = $directions[1];

        $otherWellA = ((int) $dirA['start_well_id'] === $wellId) ? (int) $dirA['end_well_id'] : (int) $dirA['start_well_id'];
        $otherWellB = ((int) $dirB['start_well_id'] === $wellId) ? (int) $dirB['end_well_id'] : (int) $dirB['start_well_id'];

        if ($otherWellA === $otherWellB) {
            Response::error('Неверные связанные направления: одинаковый конечный колодец', 422);
        }

        $user = Auth::user();
        $ownerId = $dirA['owner_id'] ?: $dirB['owner_id'];
        $typeId = $dirA['type_id'] ?: $dirB['type_id'];

        $newNumber = 'DEM-' . $otherWellA . '-' . $otherWellB . '-' . date('YmdHis');
        $notes = 'Демонтаж колодца ' . ($well['number'] ?? '');

        try {
            $this->db->beginTransaction();

            // Создаём новое направление между соседними колодцами
            $sql = "WITH well_geoms AS (
                        SELECT 
                            sw.geom_wgs84 as start_wgs84, sw.geom_msk86 as start_msk86,
                            ew.geom_wgs84 as end_wgs84, ew.geom_msk86 as end_msk86
                        FROM wells sw, wells ew
                        WHERE sw.id = :start_well_id AND ew.id = :end_well_id
                    )
                    INSERT INTO channel_directions (number, geom_wgs84, geom_msk86, owner_id, type_id,
                                                    start_well_id, end_well_id, length_m, notes, created_by, updated_by)
                    SELECT :number,
                           ST_MakeLine(start_wgs84, end_wgs84),
                           ST_MakeLine(start_msk86, end_msk86),
                           :owner_id, :type_id, :start_well_id2, :end_well_id2,
                           ROUND(ST_Length(ST_MakeLine(start_wgs84, end_wgs84)::geography)::numeric, 2),
                           :notes, :created_by, :updated_by
                    FROM well_geoms
                    RETURNING id";

            $params = [
                'number' => $newNumber,
                'owner_id' => $ownerId,
                'type_id' => $typeId,
                'start_well_id' => $otherWellA,
                'end_well_id' => $otherWellB,
                'start_well_id2' => $otherWellA,
                'end_well_id2' => $otherWellB,
                'notes' => $notes,
                'created_by' => $user['id'],
                'updated_by' => $user['id'],
            ];

            $stmt = $this->db->query($sql, $params);
            $newDirectionId = (int) $stmt->fetchColumn();

            // Каналы двух направлений
            $dirIdA = (int) $dirA['id'];
            $dirIdB = (int) $dirB['id'];
            $channels = $this->db->fetchAll(
                "SELECT id, direction_id, channel_number, kind_id, status_id, diameter_mm, material, notes
                 FROM cable_channels
                 WHERE direction_id IN ({$dirIdA}, {$dirIdB})"
            );

            $byNumber = [];
            $maxNumber = 0;
            foreach ($channels as $ch) {
                $num = (int) $ch['channel_number'];
                $maxNumber = max($maxNumber, $num);
                if (!isset($byNumber[$num]) || (int) $ch['direction_id'] === $dirIdA) {
                    $byNumber[$num] = $ch;
                }
            }

            $newChannelIds = [];
            for ($i = 1; $i <= $maxNumber; $i++) {
                $src = $byNumber[$i] ?? [];
                $newChannelIds[$i] = $this->db->insert('cable_channels', [
                    'channel_number' => $i,
                    'direction_id' => $newDirectionId,
                    'kind_id' => $src['kind_id'] ?? null,
                    'status_id' => $src['status_id'] ?? null,
                    'diameter_mm' => $src['diameter_mm'] ?? null,
                    'material' => $src['material'] ?? null,
                    'notes' => $src['notes'] ?? null,
                    'created_by' => $user['id'],
                    'updated_by' => $user['id'],
                ]);
            }

            // Обновляем маршруты кабелей
            $routeRows = $this->db->fetchAll(
                "SELECT crc.cable_id, crc.route_order, cc.channel_number
                 FROM cable_route_channels crc
                 JOIN cable_channels cc ON crc.cable_channel_id = cc.id
                 WHERE cc.direction_id IN ({$dirIdA}, {$dirIdB})
                 ORDER BY crc.cable_id, crc.route_order"
            );

            $cableOrders = [];
            foreach ($routeRows as $row) {
                $cid = (int) $row['cable_id'];
                $num = (int) $row['channel_number'];
                $order = (int) $row['route_order'];
                if (!isset($cableOrders[$cid][$num]) || $order < $cableOrders[$cid][$num]) {
                    $cableOrders[$cid][$num] = $order;
                }
            }

            foreach ($cableOrders as $cableId => $ordersByNumber) {
                // Удаляем старые каналы маршрута
                $this->db->query(
                    "DELETE FROM cable_route_channels crc
                     USING cable_channels cc
                     WHERE crc.cable_channel_id = cc.id
                       AND cc.direction_id IN ({$dirIdA}, {$dirIdB})
                       AND crc.cable_id = :cid",
                    ['cid' => (int) $cableId]
                );

                // Вставляем новые каналы маршрута
                asort($ordersByNumber);
                foreach ($ordersByNumber as $num => $order) {
                    $newChannelId = $newChannelIds[$num] ?? null;
                    if (!$newChannelId) {
                        continue;
                    }
                    $this->db->insert('cable_route_channels', [
                        'cable_id' => (int) $cableId,
                        'cable_channel_id' => $newChannelId,
                        'route_order' => (int) $order,
                    ]);
                }

                // Пересобираем маршрут колодцев
                $this->db->delete('cable_route_wells', 'cable_id = :id', ['id' => (int) $cableId]);
                $routeRowsNew = $this->db->fetchAll(
                    "SELECT crc.route_order, cd.start_well_id, cd.end_well_id
                     FROM cable_route_channels crc
                     JOIN cable_channels cc ON crc.cable_channel_id = cc.id
                     JOIN channel_directions cd ON cc.direction_id = cd.id
                     WHERE crc.cable_id = :cid
                     ORDER BY crc.route_order",
                    ['cid' => (int) $cableId]
                );
                $routeWells = [];
                foreach ($routeRowsNew as $r) {
                    foreach ([(int) $r['start_well_id'], (int) $r['end_well_id']] as $wid) {
                        if ($wid > 0 && !in_array($wid, $routeWells, true)) {
                            $routeWells[] = $wid;
                        }
                    }
                }
                foreach ($routeWells as $order => $wid) {
                    $this->db->insert('cable_route_wells', [
                        'cable_id' => (int) $cableId,
                        'well_id' => (int) $wid,
                        'route_order' => (int) $order,
                    ]);
                }

                // Пересчёт длины кабеля в канализации
                $this->db->query(
                    "UPDATE cables SET length_calculated = (
                        (SELECT COALESCE(SUM(DISTINCT cd.length_m), 0)
                         FROM cable_route_channels crc
                         JOIN cable_channels cc ON crc.cable_channel_id = cc.id
                         JOIN channel_directions cd ON cc.direction_id = cd.id
                         WHERE crc.cable_id = :cable_id)
                        +
                        (SELECT 3 * COALESCE(COUNT(DISTINCT crw.well_id), 0)
                         FROM cable_route_wells crw
                         WHERE crw.cable_id = :cable_id)
                    )
                    WHERE id = :cable_id",
                    ['cable_id' => (int) $cableId]
                );
            }

            // Чистим связи со старым колодцем в маршрутах кабеля
            $this->db->delete('cable_route_wells', 'well_id = :id', ['id' => $wellId]);

            // Удаляем фотографии удаляемых объектов
            $this->db->delete('object_photos', "object_table = 'wells' AND object_id = :id", ['id' => $wellId]);
            $this->db->query("DELETE FROM object_photos WHERE object_table = 'channel_directions' AND object_id IN ({$dirIdA}, {$dirIdB})");

            // Удаляем старые каналы и направления
            $this->db->query("DELETE FROM cable_channels WHERE direction_id IN ({$dirIdA}, {$dirIdB})");
            $this->db->query("DELETE FROM channel_directions WHERE id IN ({$dirIdA}, {$dirIdB})");

            // Удаляем колодец
            $this->db->delete('wells', 'id = :id', ['id' => $wellId]);

            $this->db->commit();

            $this->log('dismantle', 'wells', $wellId, $well, ['new_direction_id' => $newDirectionId]);

            Response::success([
                'new_direction_id' => $newDirectionId,
            ], 'Колодец демонтирован');
        } catch (\PDOException $e) {
            $this->db->rollback();
            throw $e;
        }
    }

    /**
     * GET /api/wells/export
     * Экспорт колодцев в CSV
     */
    public function export(): void
    {
        $filters = $this->buildFilters([
            'owner_id' => 'owner_id',
            'type_id' => 'type_id',
            'status_id' => 'status_id',
        ]);

        $where = $filters['where'];
        $params = $filters['params'];

        $sql = "SELECT w.number, 
                       ST_X(w.geom_wgs84) as longitude, ST_Y(w.geom_wgs84) as latitude,
                       ST_X(w.geom_msk86) as x_msk86, ST_Y(w.geom_msk86) as y_msk86,
                       o.name as owner, ot.name as type, ok.name as kind, os.name as status,
                       w.depth, w.material, w.installation_date, w.notes
                FROM wells w
                LEFT JOIN owners o ON w.owner_id = o.id
                LEFT JOIN object_types ot ON w.type_id = ot.id
                LEFT JOIN object_kinds ok ON w.kind_id = ok.id
                LEFT JOIN object_status os ON w.status_id = os.id";
        
        if ($where) {
            $sql .= " WHERE {$where}";
        }
        $sql .= " ORDER BY w.number";
        
        $data = $this->db->fetchAll($sql, $params);

        // Формируем CSV
        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename="wells_' . date('Y-m-d') . '.csv"');

        $output = fopen('php://output', 'w');
        
        // BOM для UTF-8
        fprintf($output, chr(0xEF).chr(0xBB).chr(0xBF));
        
        // Заголовки
        fputcsv($output, ['Номер', 'Долгота', 'Широта', 'X (МСК86)', 'Y (МСК86)', 
                         'Собственник', 'Вид', 'Тип', 'Состояние', 'Глубина', 'Материал', 
                         'Дата установки', 'Примечания'], ';');
        
        // Данные
        foreach ($data as $row) {
            fputcsv($output, array_values($row), ';');
        }
        
        fclose($output);
        exit;
    }
}
