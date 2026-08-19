<?php

namespace Pace\Api\Services;

/**
 * Estimates cost in USD for LLM token usage based on provider and model.
 */
class TokenCostEstimator {
    public static function estimate(string $model, int $inputTokens, int $outputTokens): float {
        $model = strtolower(trim($model));
        $inputPricePer1k = 0.0015;
        $outputPricePer1k = 0.002;

        if (str_contains($model, 'gpt-4o')) {
            $inputPricePer1k = 0.0025;
            $outputPricePer1k = 0.0100;
        } elseif (str_contains($model, 'gpt-4')) {
            $inputPricePer1k = 0.03;
            $outputPricePer1k = 0.06;
        } elseif (str_contains($model, 'claude-3-5-sonnet')) {
            $inputPricePer1k = 0.003;
            $outputPricePer1k = 0.015;
        } elseif (str_contains($model, 'claude-3-haiku')) {
            $inputPricePer1k = 0.00025;
            $outputPricePer1k = 0.00125;
        }

        $inputCost = ($inputTokens / 1000.0) * $inputPricePer1k;
        $outputCost = ($outputTokens / 1000.0) * $outputPricePer1k;

        return round($inputCost + $outputCost, 6);
    }
}
