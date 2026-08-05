<?php

namespace PaceApi;

class JsonResponse
{
    public static function success(array $data, int $statusCode = 200): void
    {
        http_response_code($statusCode);
        echo json_encode($data, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
        exit;
    }

    public static function error(string $message, int $statusCode = 400, ?string $code = null): void
    {
        http_response_code($statusCode);
        $payload = [
            'type' => 'https://pace.dev/errors/' . ($code ?? 'bad_request'),
            'title' => $message,
            'status' => $statusCode,
            'timestamp' => gmdate('Y-m-d\TH:i:s\Z')
        ];
        echo json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
        exit;
    }
}
