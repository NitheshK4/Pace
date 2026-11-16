# ==============================================================================
# LOGIC OVERVIEW:
# Statistical anomaly detection service for proactive incident alerting.
#
# CORE CODE HIGHLIGHTS:
# - detect_anomalies():
#   1. Compares recent 1-hour activity against a 7-day historical hourly baseline.
#   2. Safeguards against false positives by requiring minimum sample volumes.
#   3. Triggers 'cost_spike' alerts if spend surges > 3x the baseline.
#   4. Triggers 'rate_limit_spike' alerts if HTTP 429 errors exceed 10 in 1 hour.
# - calculate_forecast(): Linear month-end spend projection based on elapsed period time.
# ==============================================================================

import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from app.models.models import UsageEvent, AlertDelivery
from app.services.alert_service import AlertDeliveryService

# ------------------------------------------------------------------------------
# CORE CODE: Anomaly Detector Engine
# LOGIC:
# Calculates ratio = recent_1h_spend / historical_hourly_baseline.
# If ratio > 3.0x -> Dispatches CRITICAL cost spike anomaly.
# If recent 429s > 10 -> Dispatches WARNING rate-limit storm alert.
# ------------------------------------------------------------------------------
class AnomalyDetectorService:
    @staticmethod
    async def detect_anomalies(db: AsyncSession, project_id: str) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        recent_window_start = now - timedelta(hours=1)
        baseline_window_start = now - timedelta(days=7)

        # Recent 1h metrics
        recent_stmt = select(
            func.sum(UsageEvent.cost_usd).label("spend"),
            func.count(UsageEvent.id).label("requests"),
            func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens).label("tokens"),
            func.sum(case((UsageEvent.status_code == 429, 1), else_=0)).label("rate_limits")
        ).where(
            UsageEvent.project_id == project_id,
            UsageEvent.time >= recent_window_start
        )
        recent_res = await db.execute(recent_stmt)
        recent_row = recent_res.one_or_none()

        if not recent_row or (recent_row.requests or 0) < 5:
            return []  # Minimum sample safeguard to avoid false positives

        recent_spend = float(recent_row.spend or 0.0)
        recent_requests = recent_row.requests or 0

        # Baseline metrics (average hourly spend over last 7 days)
        baseline_stmt = select(
            func.sum(UsageEvent.cost_usd).label("spend"),
            func.count(UsageEvent.id).label("requests")
        ).where(
            UsageEvent.project_id == project_id,
            UsageEvent.time >= baseline_window_start,
            UsageEvent.time < recent_window_start
        )
        base_res = await db.execute(baseline_stmt)
        base_row = base_res.one_or_none()

        if not base_row or (base_row.requests or 0) < 20:
            return []  # Insufficient baseline data

        avg_hourly_spend = float(base_row.spend or 0.0) / (7 * 24)
        avg_hourly_requests = (base_row.requests or 0) / (7 * 24)

        anomalies = []

        # 1. Cost Spike Anomaly (recent 1h spend > 3x historical hourly average)
        if avg_hourly_spend > 0.01 and recent_spend > (avg_hourly_spend * 3.0):
            anomalies.append({
                "type": "cost_spike",
                "severity": "critical",
                "explanation": f"Recent 1h spend (${recent_spend:.4f}) is {recent_spend / avg_hourly_spend:.1f}x higher than historical hourly baseline (${avg_hourly_spend:.4f}).",
                "observed_value": recent_spend,
                "baseline_value": avg_hourly_spend,
            })

        # 2. Rate Limit Spike Anomaly (recent 429 count > 10)
        rate_limits = recent_row.rate_limits or 0
        if rate_limits > 10:
            anomalies.append({
                "type": "rate_limit_spike",
                "severity": "warning",
                "explanation": f"Observed {rate_limits} rate limit (429) errors in the last hour.",
                "observed_value": rate_limits,
                "baseline_value": 0,
            })

        return anomalies

    @staticmethod
    def calculate_forecast(current_spend: float, period: str, elapsed_percent: float) -> float:
        if elapsed_percent <= 0:
            return current_spend
        if elapsed_percent >= 100:
            return current_spend
        projected = (current_spend / (elapsed_percent / 100.0))
        return round(projected, 2)
