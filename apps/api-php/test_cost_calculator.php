<?php

require_once __DIR__ . '/src/CostCalculator.php';

use PaceApi\CostCalculator;

$formattedUsd = CostCalculator::formatCurrency(0.0125, 'USD');
assert($formattedUsd === '$0.0125', 'Expected $0.0125 format for 0.0125 USD');

$formattedEur = CostCalculator::formatCurrency(0.0125, 'EUR');
assert($formattedEur === '0.0125', 'Expected 0.0125 format for EUR currency');

echo "CostCalculator formatCurrency unit test passed successfully.\n";
