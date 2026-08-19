<?php

require_once __DIR__ . '/src/Services/TokenCostEstimator.php';

use Pace\Api\Services\TokenCostEstimator;

$costGpt4o = TokenCostEstimator::estimate('gpt-4o', 1000, 1000);
assert($costGpt4o === 0.0125, 'Expected 0.0125 cost for gpt-4o 1k/1k tokens');

$costClaudeSonnet = TokenCostEstimator::estimate('claude-3-5-sonnet', 1000, 1000);
assert($costClaudeSonnet === 0.018, 'Expected 0.018 cost for claude-3-5-sonnet 1k/1k tokens');

echo "TokenCostEstimator tests passed successfully.\n";
