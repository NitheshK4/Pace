<?php

namespace PaceApi\Services;

use PDO;

class RetentionPurger
{
    public static function purgeOldTelemetry(PDO $pdo, string $projectId, int $daysToKeep = 90): int
    {
        $cutoffDate = date('Y-m-d H:i:s', strtotime("-{$daysToKeep} days"));
        $stmt = $pdo->prepare("DELETE FROM usage_events WHERE project_id = ? AND time < ?");
        $stmt->execute([$projectId, $cutoffDate]);
        return $stmt->rowCount();
    }
}
