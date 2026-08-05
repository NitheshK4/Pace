<?php

require_once __DIR__ . '/../src/Database.php';
require_once __DIR__ . '/../src/CostCalculator.php';
require_once __DIR__ . '/../src/Services/BudgetService.php';
require_once __DIR__ . '/../src/Services/AnomalyDetector.php';
require_once __DIR__ . '/../src/Services/CsvExporter.php';

use PaceApi\Database;
use PaceApi\CostCalculator;
use PaceApi\Services\BudgetService;
use PaceApi\Services\AnomalyDetector;
use PaceApi\Services\CsvExporter;

$startTime = microtime(true);

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Total-Count');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

register_shutdown_function(function() use ($startTime) {
    $durationMs = round((microtime(true) - $startTime) * 1000, 2);
    if (!headers_sent()) {
        header("X-Response-Time-Ms: {$durationMs}");
    }
});

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$method = $_SERVER['REQUEST_METHOD'];
$pdo = Database::getConnection();

// Router
if ($uri === '/healthz' && $method === 'GET') {
    echo json_encode([
        'status' => 'healthy',
        'service' => 'pace-api-php',
        'timestamp' => gmdate('Y-m-d\TH:i:s\Z')
    ]);
    exit;
}

if ($uri === '/v1/auth/login' && $method === 'POST') {
    $rawInput = file_get_contents('php://input');
    $payload = json_decode($rawInput, true);

    $email = $payload['email'] ?? '';
    $password = $payload['password'] ?? '';

    if (!empty($email) && !empty($password)) {
        echo json_encode([
            'access_token' => 'pace_token_demo_php_' . bin2hex(random_bytes(16)),
            'token_type' => 'bearer'
        ]);
        exit;
    }

    http_response_code(401);
    echo json_encode(['detail' => 'Invalid email or password']);
    exit;
}

if ($uri === '/v1/auth/register' && $method === 'POST') {
    $rawInput = file_get_contents('php://input');
    $payload = json_decode($rawInput, true);

    echo json_encode([
        'message' => 'User registered successfully',
        'email' => $payload['email'] ?? 'demo@pace.dev'
    ]);
    exit;
}

if ($uri === '/v1/projects' && $method === 'GET') {
    echo json_encode([
        [
            'id' => 'proj_default',
            'name' => 'Default Project',
            'created_at' => gmdate('Y-m-d\TH:i:s\Z')
        ]
    ]);
    exit;
}

if (str_starts_with($uri, '/v1/projects/') && str_ends_with($uri, '/keys') && $method === 'GET') {
    echo json_encode([
        [
            'id' => 'key_1',
            'key_prefix' => 'pace_demokey',
            'created_at' => gmdate('Y-m-d\TH:i:s\Z')
        ]
    ]);
    exit;
}

if ($uri === '/v1/ingest/events' && $method === 'POST') {
    $rawInput = file_get_contents('php_input');
    if (empty($rawInput)) {
        $rawInput = file_get_contents('php://input');
    }
    $payload = json_decode($rawInput, true);

    if (!$payload) {
        http_response_code(400);
        echo json_encode(['error' => 'Invalid JSON body']);
        exit;
    }

    $eventsList = [];
    if (isset($payload['events']) && is_array($payload['events'])) {
        $eventsList = $payload['events'];
    } elseif (isset($payload['event_id'])) {
        $eventsList = [$payload];
    } elseif (is_array($payload) && isset($payload[0]['event_id'])) {
        $eventsList = $payload;
    }

    $projectId = 'proj_default';
    // Parse Bearer Token if available
    $authHeader = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    if (preg_match('/Bearer\s+(pace_[a-zA-Z0-9_]+)/', $authHeader, $matches)) {
        $keyPrefix = substr($matches[1], 0, 12);
        $stmtKey = $pdo->prepare("SELECT project_id FROM project_api_keys WHERE key_prefix = ? AND is_active = 1");
        $stmtKey->execute([$keyPrefix]);
        $fetchedProj = $stmtKey->fetchColumn();
        if ($fetchedProj) {
            $projectId = $fetchedProj;
        }
    }

    $accepted = 0;
    $duplicates = 0;

    $checkStmt = $pdo->prepare("SELECT COUNT(*) FROM usage_events WHERE project_id = ? AND event_id = ?");
    $insertStmt = $pdo->prepare("
        INSERT INTO usage_events (
            project_id, event_id, time, provider, model, endpoint,
            input_tokens, output_tokens, cached_input_tokens, reasoning_tokens,
            cost_usd, latency_ms, status_code, metadata_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ");

    $now = gmdate('Y-m-d\TH:i:s\Z');

    foreach ($eventsList as $ev) {
        $eventId = $ev['event_id'] ?? ('evt_' . bin2hex(random_bytes(8)));
        $checkStmt->execute([$projectId, $eventId]);
        if ($checkStmt->fetchColumn() > 0) {
            $duplicates++;
            continue;
        }

        $provider = strtolower($ev['provider'] ?? 'openai');
        $model = $ev['model'] ?? 'unknown';
        $inTokens = (int)($ev['input_tokens'] ?? 0);
        $outTokens = (int)($ev['output_tokens'] ?? 0);
        $cachedTokens = (int)($ev['cached_input_tokens'] ?? 0);
        $reasoningTokens = (int)($ev['reasoning_tokens'] ?? 0);
        $suppliedCost = isset($ev['cost_usd']) ? (float)$ev['cost_usd'] : null;

        $costUsd = CostCalculator::calculate($pdo, $provider, $model, $inTokens, $outTokens, $cachedTokens, $reasoningTokens, $suppliedCost);

        $eventTime = $ev['time'] ?? $now;
        $metaJson = isset($ev['metadata']) ? json_encode($ev['metadata']) : null;

        $insertStmt->execute([
            $projectId,
            $eventId,
            $eventTime,
            $provider,
            $model,
            $ev['endpoint'] ?? '/v1/chat/completions',
            $inTokens,
            $outTokens,
            $cachedTokens,
            $reasoningTokens,
            $costUsd,
            (int)($ev['latency_ms'] ?? 0),
            (int)($ev['status_code'] ?? 200),
            $metaJson,
            $now
        ]);
        $accepted++;
    }

    echo json_encode([
        'accepted_count' => $accepted,
        'duplicate_count' => $duplicates,
        'rejected_count' => 0
    ]);
    exit;
}

if ($uri === '/v1/analytics/overview' && $method === 'GET') {
    $projectId = $_GET['project_id'] ?? 'proj_default';
    $stmt = $pdo->prepare("
        SELECT
            SUM(cost_usd) as total_spend,
            COUNT(*) as total_requests,
            SUM(input_tokens) as total_input,
            SUM(output_tokens) as total_output,
            SUM(cached_input_tokens) as total_cached,
            SUM(reasoning_tokens) as total_reasoning,
            SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors,
            AVG(latency_ms) as avg_latency
        FROM usage_events
        WHERE project_id = ?
    ");
    $stmt->execute([$projectId]);
    $row = $stmt->fetch();

    $totalReqs = (int)($row['total_requests'] ?? 0);
    $errors = (int)($row['errors'] ?? 0);
    $errRate = $totalReqs > 0 ? round(($errors / $totalReqs) * 100.0, 2) : 0.0;

    echo json_encode([
        'total_spend_usd' => (float)($row['total_spend'] ?? 0.0),
        'total_requests' => $totalReqs,
        'total_input_tokens' => (int)($row['total_input'] ?? 0),
        'total_output_tokens' => (int)($row['total_output'] ?? 0),
        'total_cached_tokens' => (int)($row['total_cached'] ?? 0),
        'total_reasoning_tokens' => (int)($row['total_reasoning'] ?? 0),
        'error_count' => $errors,
        'error_rate' => $errRate,
        'avg_latency_ms' => round((float)($row['avg_latency'] ?? 0.0), 2)
    ]);
    exit;
}

if ($uri === '/v1/analytics/events' && $method === 'GET') {
    $projectId = $_GET['project_id'] ?? 'proj_default';
    $provider = $_GET['provider'] ?? null;
    $model = $_GET['model'] ?? null;
    $minLatency = isset($_GET['min_latency_ms']) ? (int)$_GET['min_latency_ms'] : null;
    $errorsOnly = !empty($_GET['errors_only']);
    $limit = isset($_GET['limit']) ? min((int)$_GET['limit'], 200) : 50;

    $where = ["project_id = ?"];
    $params = [$projectId];

    if ($provider) {
        $where[] = "provider = ?";
        $params[] = strtolower($provider);
    }
    if ($model) {
        $where[] = "model = ?";
        $params[] = $model;
    }
    if ($minLatency !== null) {
        $where[] = "latency_ms >= ?";
        $params[] = $minLatency;
    }
    if ($errorsOnly) {
        $where[] = "status_code >= 400";
    }

    $whereStr = implode(' AND ', $where);

    // Count
    $countStmt = $pdo->prepare("SELECT COUNT(*) FROM usage_events WHERE {$whereStr}");
    $countStmt->execute($params);
    $totalCount = (int)$countStmt->fetchColumn();

    header("X-Total-Count: {$totalCount}");

    // Fetch Events
    $queryStmt = $pdo->prepare("
        SELECT id, event_id, time, provider, model, endpoint, input_tokens, output_tokens, cached_input_tokens, reasoning_tokens, cost_usd, latency_ms, status_code, metadata_json
        FROM usage_events
        WHERE {$whereStr}
        ORDER BY id DESC
        LIMIT ?
    ");
    $queryParams = array_merge($params, [$limit]);
    $queryStmt->execute($queryParams);
    $rows = $queryStmt->fetchAll();

    $events = [];
    foreach ($rows as $r) {
        $meta = !empty($r['metadata_json']) ? json_decode($r['metadata_json'], true) : null;
        $events[] = [
            'id' => (string)$r['id'],
            'event_id' => $r['event_id'],
            'time' => $r['time'],
            'provider' => $r['provider'],
            'model' => $r['model'],
            'input_tokens' => (int)$r['input_tokens'],
            'output_tokens' => (int)$r['output_tokens'],
            'cached_input_tokens' => (int)$r['cached_input_tokens'],
            'reasoning_tokens' => (int)$r['reasoning_tokens'],
            'cost_usd' => $r['cost_usd'] !== null ? (float)$r['cost_usd'] : null,
            'latency_ms' => (int)$r['latency_ms'],
            'status_code' => (int)$r['status_code'],
            'metadata_json' => $meta
        ];
    }

    echo json_encode([
        'events' => $events,
        'total' => $totalCount
    ]);
    exit;
}

if ($uri === '/v1/exports/csv' && $method === 'GET') {
    $projectId = $_GET['project_id'] ?? 'proj_default';
    $csvData = CsvExporter::exportCsv($pdo, $projectId);

    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="pace_telemetry_' . $projectId . '.csv"');
    echo $csvData;
    exit;
}

if ($uri === '/v1/budgets/status' && $method === 'GET') {
    $projectId = $_GET['project_id'] ?? 'proj_default';
    $limitUsd = isset($_GET['limit_usd']) ? (float)$_GET['limit_usd'] : 500.0;
    echo json_encode(BudgetService::getBudgetStatus($pdo, $projectId, $limitUsd));
    exit;
}

if ($uri === '/v1/system/anomalies' && $method === 'GET') {
    $projectId = $_GET['project_id'] ?? 'proj_default';
    echo json_encode(AnomalyDetector::detectAnomalies($pdo, $projectId));
    exit;
}

http_response_code(404);
echo json_encode(['error' => 'Endpoint not found', 'path' => $uri]);
