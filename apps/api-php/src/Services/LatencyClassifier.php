<?php

namespace Pace\Api\Services;

/**
 * Classifies telemetry latency into SLA performance categories.
 */
class LatencyClassifier {
    public static function classify(int $latencyMs): string {
        if ($latencyMs <= 0) {
            return 'unknown';
        }
        if ($latencyMs <= 500) {
            return 'excellent';
        }
        if ($latencyMs <= 1500) {
            return 'acceptable';
        }
        return 'degraded';
    }
}
