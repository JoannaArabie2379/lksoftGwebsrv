<?php
/**
 * Контроллер импорта данных
 */

namespace App\Controllers;

use App\Core\Response;
use App\Core\Auth;

class ImportController extends BaseController
{
    /**
     * POST /api/import/csv
     * Импорт из CSV с сопоставлением колонок
     */
    public function importCsv(): void
    {
        $this->checkWriteAccess();

        $file = $this->request->file('file');
        if (!$file || $file['error'] !== UPLOAD_ERR_OK) {
            Response::error('Файл не загружен', 400);
        }

        $targetTable = $this->request->input('target_table');
        $columnMapping = $this->request->input('column_mapping');
        $coordinateSystem = $this->request->input('coordinate_system', 'wgs84');

        if (!$targetTable || !$columnMapping) {
            Response::error('Необходимо указать target_table и column_mapping', 422);
        }

        $allowedTables = ['wells', 'marker_posts', 'ground_cables', 'aerial_cables', 'duct_cables'];
        if (!in_array($targetTable, $allowedTables)) {
            Response::error('Недопустимая таблица для импорта', 400);
        }

        try {
            $handle = fopen($file['tmp_name'], 'r');
            
            // Определяем разделитель
            $firstLine = fgets($handle);
            rewind($handle);
            $delimiter = strpos($firstLine, ';') !== false ? ';' : ',';

            // Читаем заголовки
            $headers = fgetcsv($handle, 0, $delimiter);
            if (!$headers) {
                Response::error('Не удалось прочитать заголовки CSV', 400);
            }

            $columnMapping = json_decode($columnMapping, true);
            $imported = 0;
            $errors = [];
            $user = Auth::user();

            $this->db->beginTransaction();

            $lineNumber = 1;
            while (($row = fgetcsv($handle, 0, $delimiter)) !== false) {
                $lineNumber++;
                
                try {
                    $data = [];
                    foreach ($columnMapping as $csvColumn => $dbColumn) {
                        $csvIndex = array_search($csvColumn, $headers);
                        if ($csvIndex !== false && isset($row[$csvIndex])) {
                            $data[$dbColumn] = trim($row[$csvIndex]);
                        }
                    }

                    if (empty($data)) {
                        continue;
                    }

                    // Обработка координат
                    $this->processCoordinates($data, $coordinateSystem, $targetTable);

                    $data['created_by'] = $user['id'];
                    $data['updated_by'] = $user['id'];

                    // Удаляем пустые значения
                    $data = array_filter($data, fn($v) => $v !== null && $v !== '');

                    $this->insertWithGeometry($targetTable, $data, $coordinateSystem);
                    $imported++;
                } catch (\Exception $e) {
                    $errors[] = "Строка {$lineNumber}: " . $e->getMessage();
                }
            }

            fclose($handle);

            $this->db->commit();

            $this->log('import', $targetTable, null, null, ['count' => $imported]);

            Response::success([
                'imported' => $imported,
                'errors' => $errors,
            ], "Импортировано {$imported} записей");
        } catch (\Exception $e) {
            $this->db->rollback();
            Response::error('Ошибка импорта: ' . $e->getMessage(), 500);
        }
    }

    /**
     * POST /api/import/preview
     * Предпросмотр CSV файла
     */
    public function previewCsv(): void
    {
        $file = $this->request->file('file');
        if (!$file || $file['error'] !== UPLOAD_ERR_OK) {
            Response::error('Файл не загружен', 400);
        }

        $handle = fopen($file['tmp_name'], 'r');
        
        // Определяем разделитель
        $firstLine = fgets($handle);
        rewind($handle);
        $delimiter = strpos($firstLine, ';') !== false ? ';' : ',';

        $headers = fgetcsv($handle, 0, $delimiter);
        $preview = [];
        $count = 0;

        while (($row = fgetcsv($handle, 0, $delimiter)) !== false && $count < 10) {
            $preview[] = array_combine($headers, $row);
            $count++;
        }

        fclose($handle);

        // Доступные поля для сопоставления
        $targetFields = [
            'wells' => ['number', 'longitude', 'latitude', 'x_msk86', 'y_msk86', 'depth', 'material', 'installation_date', 'notes'],
            'marker_posts' => ['number', 'longitude', 'latitude', 'x_msk86', 'y_msk86', 'height_m', 'material', 'notes'],
            'ground_cables' => ['number', 'cable_type', 'fiber_count', 'length_m', 'installation_date', 'notes'],
            'aerial_cables' => ['number', 'cable_type', 'fiber_count', 'length_m', 'height_m', 'notes'],
            'duct_cables' => ['number', 'cable_type', 'fiber_count', 'length_m', 'notes'],
        ];

        Response::success([
            'headers' => $headers,
            'preview' => $preview,
            'total_rows' => $this->countCsvRows($file['tmp_name']),
            'target_fields' => $targetFields,
        ]);
    }

    /**
     * POST /api/import/mapinfo
     * Импорт из MapInfo (.TAB, .DAT, .MAP, .ID)
     */
    public function importMapInfo(): void
    {
        $this->checkWriteAccess();

        $files = $this->request->files();
        
        $tabFile = null;
        $datFile = null;
        
        foreach ($files as $file) {
            if ($file['error'] === UPLOAD_ERR_OK) {
                $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
                if ($ext === 'tab') $tabFile = $file;
                if ($ext === 'dat') $datFile = $file;
            }
        }

        if (!$tabFile) {
            Response::error('Необходим .TAB файл', 400);
        }

        $targetTable = $this->request->input('target_table');
        if (!$targetTable) {
            Response::error('Необходимо указать target_table', 422);
        }

        try {
            // Читаем структуру из .TAB файла
            $tabContent = file_get_contents($tabFile['tmp_name']);
            $structure = $this->parseTabFile($tabContent);

            // Читаем данные из .DAT файла (если есть)
            $data = [];
            if ($datFile) {
                $data = $this->parseDatFile($datFile['tmp_name'], $structure);
            }

            Response::success([
                'structure' => $structure,
                'preview' => array_slice($data, 0, 10),
                'total_rows' => count($data),
                'message' => 'Файл разобран. Требуется подтверждение для импорта.',
            ]);
        } catch (\Exception $e) {
            Response::error('Ошибка чтения MapInfo: ' . $e->getMessage(), 500);
        }
    }

    /**
     * POST /api/import/mapinfo/confirm
     * Подтверждение импорта MapInfo
     */
    public function confirmMapInfoImport(): void
    {
        $this->checkWriteAccess();

        $targetTable = $this->request->input('target_table');
        $data = $this->request->input('data');
        $columnMapping = $this->request->input('column_mapping');
        $coordinateSystem = $this->request->input('coordinate_system', 'wgs84');

        if (!$targetTable || !$data || !$columnMapping) {
            Response::error('Недостаточно данных', 422);
        }

        try {
            $this->db->beginTransaction();

            $imported = 0;
            $errors = [];
            $user = Auth::user();

            foreach ($data as $index => $row) {
                try {
                    $mappedData = [];
                    foreach ($columnMapping as $srcCol => $dbCol) {
                        if (isset($row[$srcCol])) {
                            $mappedData[$dbCol] = $row[$srcCol];
                        }
                    }

                    if (empty($mappedData)) continue;

                    $this->processCoordinates($mappedData, $coordinateSystem, $targetTable);

                    $mappedData['created_by'] = $user['id'];
                    $mappedData['updated_by'] = $user['id'];

                    $mappedData = array_filter($mappedData, fn($v) => $v !== null && $v !== '');

                    $this->insertWithGeometry($targetTable, $mappedData, $coordinateSystem);
                    $imported++;
                } catch (\Exception $e) {
                    $errors[] = "Запись " . ($index + 1) . ": " . $e->getMessage();
                }
            }

            $this->db->commit();

            $this->log('import_mapinfo', $targetTable, null, null, ['count' => $imported]);

            Response::success([
                'imported' => $imported,
                'errors' => $errors,
            ], "Импортировано {$imported} записей");
        } catch (\Exception $e) {
            $this->db->rollback();
            Response::error('Ошибка импорта: ' . $e->getMessage(), 500);
        }
    }

    /**
     * Обработка координат
     */
    private function processCoordinates(array &$data, string $coordinateSystem, string $table): void
    {
        // Для точечных объектов
        if (in_array($table, ['wells', 'marker_posts'])) {
            if ($coordinateSystem === 'wgs84') {
                if (isset($data['longitude']) && isset($data['latitude'])) {
                    $data['_lon'] = (float) $data['longitude'];
                    $data['_lat'] = (float) $data['latitude'];
                    unset($data['longitude'], $data['latitude']);
                }
            } else {
                if (isset($data['x_msk86']) && isset($data['y_msk86'])) {
                    $data['_x'] = (float) $data['x_msk86'];
                    $data['_y'] = (float) $data['y_msk86'];
                    unset($data['x_msk86'], $data['y_msk86']);
                }
            }
        }
    }

    /**
     * Вставка записи с геометрией
     */
    private function insertWithGeometry(string $table, array $data, string $coordinateSystem): void
    {
        if (in_array($table, ['wells', 'marker_posts'])) {
            if (isset($data['_lon']) && isset($data['_lat'])) {
                $lon = $data['_lon'];
                $lat = $data['_lat'];
                unset($data['_lon'], $data['_lat']);

                $columns = implode(', ', array_keys($data));
                $placeholders = implode(', ', array_map(fn($k) => ":$k", array_keys($data)));

                $sql = "INSERT INTO {$table} ({$columns}, geom_wgs84, geom_msk86) 
                        VALUES ({$placeholders}, 
                                ST_SetSRID(ST_MakePoint({$lon}, {$lat}), 4326),
                                ST_Transform(ST_SetSRID(ST_MakePoint({$lon}, {$lat}), 4326), 200004))";

                $this->db->query($sql, $data);
            } elseif (isset($data['_x']) && isset($data['_y'])) {
                $x = $data['_x'];
                $y = $data['_y'];
                unset($data['_x'], $data['_y']);

                $columns = implode(', ', array_keys($data));
                $placeholders = implode(', ', array_map(fn($k) => ":$k", array_keys($data)));

                $sql = "INSERT INTO {$table} ({$columns}, geom_wgs84, geom_msk86) 
                        VALUES ({$placeholders}, 
                                ST_Transform(ST_SetSRID(ST_MakePoint({$x}, {$y}), 200004), 4326),
                                ST_SetSRID(ST_MakePoint({$x}, {$y}), 200004))";

                $this->db->query($sql, $data);
            } else {
                throw new \Exception('Не указаны координаты');
            }
        } else {
            $this->db->insert($table, $data);
        }
    }

    /**
     * Подсчёт строк в CSV
     */
    private function countCsvRows(string $filename): int
    {
        $count = 0;
        $handle = fopen($filename, 'r');
        while (fgets($handle) !== false) {
            $count++;
        }
        fclose($handle);
        return max(0, $count - 1); // Минус заголовок
    }

    /**
     * Парсинг .TAB файла
     */
    private function parseTabFile(string $content): array
    {
        $structure = [
            'columns' => [],
            'type' => null,
        ];

        $lines = explode("\n", $content);
        $inFields = false;

        foreach ($lines as $line) {
            $line = trim($line);
            
            if (stripos($line, 'Fields') === 0) {
                $inFields = true;
                continue;
            }

            if ($inFields) {
                if (preg_match('/^\s*(\w+)\s+(\w+)/i', $line, $matches)) {
                    $structure['columns'][] = [
                        'name' => $matches[1],
                        'type' => $matches[2],
                    ];
                }
                
                if (stripos($line, ';') === 0) {
                    $inFields = false;
                }
            }

            if (stripos($line, 'Type') === 0) {
                if (preg_match('/Type\s+"(\w+)"/i', $line, $matches)) {
                    $structure['type'] = $matches[1];
                }
            }
        }

        return $structure;
    }

    /**
     * Парсинг .DAT файла
     */
    private function parseDatFile(string $filename, array $structure): array
    {
        $data = [];
        $handle = fopen($filename, 'r');

        if (!$handle) {
            return $data;
        }

        // DAT файлы обычно бинарные или CSV-подобные
        // Пробуем читать как CSV
        while (($row = fgetcsv($handle, 0, "\t")) !== false) {
            if (count($row) === count($structure['columns'])) {
                $record = [];
                foreach ($structure['columns'] as $i => $col) {
                    $record[$col['name']] = $row[$i] ?? null;
                }
                $data[] = $record;
            }
        }

        fclose($handle);
        return $data;
    }
}
