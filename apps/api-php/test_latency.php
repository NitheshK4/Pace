<?php

require_once __DIR__ . '/src/Services/LatencyClassifier.php';

use Pace\Api\Services\LatencyClassifier;

assert(LatencyClassifier::classify(0) === 'unknown');
assert(LatencyClassifier::classify(250) === 'excellent');
assert(LatencyClassifier::classify(1000) === 'acceptable');
assert(LatencyClassifier::classify(3000) === 'degraded');

echo "LatencyClassifier tests passed successfully.\n";
