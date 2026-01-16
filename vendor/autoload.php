<?php
/**
 * Простой автозагрузчик классов PSR-4
 */

spl_autoload_register(function ($class) {
    // Базовый каталог для пространства имён
    $baseDir = __DIR__ . '/../src/';
    
    // Пространство имён проекта
    $prefix = 'App\\';
    
    // Если класс не использует наш префикс, пропускаем
    $len = strlen($prefix);
    if (strncmp($prefix, $class, $len) !== 0) {
        return;
    }
    
    // Получаем относительное имя класса
    $relativeClass = substr($class, $len);
    
    // Заменяем разделители пространства имён на разделители каталогов
    $file = $baseDir . str_replace('\\', '/', $relativeClass) . '.php';
    
    // Если файл существует, подключаем его
    if (file_exists($file)) {
        require $file;
    }
});
