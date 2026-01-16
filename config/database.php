<?php
/**
 * Конфигурация подключения к базе данных PostgreSQL
 * ИГС lksoftGwebsrv
 */

return [
    'host' => '10.16.10.150',
    'port' => '5432',
    'dbname' => 'lksoftgwebsrv',
    'user' => 'lksoftgwebsrv',
    'password' => 'lksoftGwebsrv',
    'charset' => 'UTF8',
    'options' => [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]
];
