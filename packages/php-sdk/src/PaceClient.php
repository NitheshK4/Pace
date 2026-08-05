<?php

namespace Pace;

/**
 * Official Pace Telemetry Client for PHP applications.
 */
class PaceClient {
    private string $apiKey;
    private string $endpoint;
    private int $timeout;
    private array $defaultMetadata;

    public function __construct(
        ?string $apiKey = null,
        ?string $endpoint = null,
        int $timeout = 3,
        array $defaultMetadata = []
    ) {
        $this->apiKey = $apiKey ?? getenv('PACE_API_KEY') ?: '';
        $targetEndpoint = $endpoint ?? getenv('PACE_ENDPOINT') ?: 'http://localhost:8000';
        $this->endpoint = rtrim($targetEndpoint, '/');
        $this->timeout = $timeout;
        $this->defaultMetadata = $defaultMetadata;
    }

    /**
     * Records a single LLM telemetry event.
     *
     * @param array $data Event data (provider, model, input_tokens, output_tokens, latency_ms, etc.)
     * @return array Ingestion response array or error details
     */
    public function record(array $data): array {
        $eventId = $data['event_id'] ?? ('evt_' . bin2hex(random_bytes(10)));
        $metadata = array_merge($this->defaultMetadata, $data['metadata'] ?? []);
        $sanitizedMetadata = $this->sanitizeMetadata($metadata);

        $payload = [
            'event_id'             => $eventId,
            'time'                 => $data['time'] ?? gmdate('Y-m-d\TH:i:s\Z'),
            'provider'             => strtolower($data['provider'] ?? 'openai'),
            'model'                => $data['model'] ?? 'unknown',
            'endpoint'             => $data['endpoint'] ?? '/v1/chat/completions',
            'input_tokens'         => (int)($data['input_tokens'] ?? 0),
            'output_tokens'        => (int)($data['output_tokens'] ?? 0),
            'cached_input_tokens'  => (int)($data['cached_input_tokens'] ?? 0),
            'reasoning_tokens'     => (int)($data['reasoning_tokens'] ?? 0),
            'cost_usd'             => isset($data['cost_usd']) ? (float)$data['cost_usd'] : null,
            'latency_ms'           => (int)($data['latency_ms'] ?? 0),
            'status_code'          => (int)($data['status_code'] ?? 200),
            'metadata'             => !empty($sanitizedMetadata) ? $sanitizedMetadata : null
        ];

        return $this->sendHttpRequest('/v1/ingest/events', $payload);
    }

    /**
     * Records multiple LLM telemetry events in a single batch request.
     *
     * @param array $events Array of event arrays
     * @return array Ingestion response array
     */
    public function recordBatch(array $events): array {
        $formattedEvents = [];
        foreach ($events as $data) {
            $eventId = $data['event_id'] ?? ('evt_' . bin2hex(random_bytes(10)));
            $metadata = array_merge($this->defaultMetadata, $data['metadata'] ?? []);
            $sanitizedMetadata = $this->sanitizeMetadata($metadata);

            $formattedEvents[] = [
                'event_id'             => $eventId,
                'time'                 => $data['time'] ?? gmdate('Y-m-d\TH:i:s\Z'),
                'provider'             => strtolower($data['provider'] ?? 'openai'),
                'model'                => $data['model'] ?? 'unknown',
                'endpoint'             => $data['endpoint'] ?? '/v1/chat/completions',
                'input_tokens'         => (int)($data['input_tokens'] ?? 0),
                'output_tokens'        => (int)($data['output_tokens'] ?? 0),
                'cached_input_tokens'  => (int)($data['cached_input_tokens'] ?? 0),
                'reasoning_tokens'     => (int)($data['reasoning_tokens'] ?? 0),
                'cost_usd'             => isset($data['cost_usd']) ? (float)$data['cost_usd'] : null,
                'latency_ms'           => (int)($data['latency_ms'] ?? 0),
                'status_code'          => (int)($data['status_code'] ?? 200),
                'metadata'             => !empty($sanitizedMetadata) ? $sanitizedMetadata : null
            ];
        }

        return $this->sendHttpRequest('/v1/ingest/events', ['events' => $formattedEvents]);
    }

    /**
     * Sanitizes sensitive fields from metadata to enforce zero prompt storage.
     */
    public function sanitizeMetadata(array $metadata): array {
        $sensitiveKeys = ['prompt', 'completion', 'messages', 'input', 'output', 'api_key', 'authorization', 'secret', 'password', 'token'];
        $clean = [];

        foreach ($metadata as $key => $value) {
            $lowerKey = strtolower((string)$key);
            if (in_array($lowerKey, $sensitiveKeys, true)) {
                continue;
            }
            if (is_array($value)) {
                $clean[$key] = $this->sanitizeMetadata($value);
            } else {
                $clean[$key] = $value;
            }
        }

        return $clean;
    }

    /**
     * Helper to send JSON payload via cURL.
     */
    private function sendHttpRequest(string $path, array $payload): array {
        $url = $this->endpoint . $path;
        $jsonPayload = json_encode($payload);

        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => $jsonPayload,
            CURLOPT_HTTPHEADER     => [
                'Content-Type: application/json',
                'Authorization: Bearer ' . $this->apiKey,
                'Content-Length: ' . strlen($jsonPayload)
            ],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => $this->timeout,
            CURLOPT_CONNECTTIMEOUT => 2
        ]);

        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($error) {
            return [
                'success' => false,
                'error'   => $error,
                'status'  => $httpCode
            ];
        }

        $decoded = json_decode((string)$response, true);
        return [
            'success'  => $httpCode >= 200 && $httpCode < 300,
            'status'   => $httpCode,
            'response' => $decoded ?? $response
        ];
    }
}
