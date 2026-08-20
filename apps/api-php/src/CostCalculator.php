<?php

namespace PaceApi;

use PDO;

class CostCalculator {
    public static function calculate(
        PDO $pdo,
        string $provider,
        string $model,
        int $inputTokens,
        int $outputTokens,
        int $cachedTokens = 0,
        int $reasoningTokens = 0,
        ?float $suppliedCost = null
    ): ?float {
        if ($suppliedCost !== null) {
            return $suppliedCost;
        }

        $providerLower = strtolower($provider);
        $modelLower = strtolower($model);

        $stmt = $pdo->prepare("
            SELECT input_cost_per_1k, output_cost_per_1k, cache_read_cost_per_1k, reasoning_cost_per_1k
            FROM pricing_rates
            WHERE provider = ? AND model = ? AND is_deprecated = 0
            ORDER BY effective_from DESC LIMIT 1
        ");
        $stmt->execute([$providerLower, $modelLower]);
        $rate = $stmt->fetch();

        if (!$rate) {
            // Fallback prefix match e.g. gpt-4o-2024-05-13 -> gpt-4o
            $baseModel = explode('-202', $modelLower)[0];
            $stmt->execute([$providerLower, $baseModel]);
            $rate = $stmt->fetch();
        }

        if (!$rate) {
            return null;
        }

        $inCost = ($inputTokens / 1000.0) * (float)$rate['input_cost_per_1k'];
        $outCost = ($outputTokens / 1000.0) * (float)$rate['output_cost_per_1k'];
        $cacheCost = ($cachedTokens / 1000.0) * (float)$rate['cache_read_cost_per_1k'];
        $reasoningCost = ($reasoningTokens / 1000.0) * (float)$rate['reasoning_cost_per_1k'];

        return round($inCost + $outCost + $cacheCost + $reasoningCost, 6);
    }

    public static function formatCurrency(float $amount, string $currency = 'USD'): string {
        $symbol = ($currency === 'USD') ? '$' : '';
        return $symbol . number_format($amount, 4);
    }
}
