import hmac
import hashlib
import json
import logging
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import AlertDelivery

logger = logging.getLogger("pace.alerts")

class AlertDeliveryService:
    @staticmethod
    async def deliver_alert(
        db: AsyncSession,
        project_id: str,
        budget_id: Optional[str],
        event_type: str,
        threshold_percent: Optional[int],
        severity: str,
        observed_value: float,
        limit_value: float,
        period_start: datetime,
        period_end: datetime,
        destination: Dict[str, Any]
    ) -> AlertDelivery:
        dest_type = destination.get("type", "console")
        target_url = destination.get("url", "console")
        secret = destination.get("secret", "")

        payload = {
            "event_id": f"evt_alert_{int(datetime.now(timezone.utc).timestamp())}",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "budget_id": budget_id,
            "severity": severity,
            "threshold_percent": threshold_percent,
            "observed_value": observed_value,
            "limit_value": limit_value,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            }
        }

        status_str = "sent"
        error_msg = None

        if dest_type in ("webhook", "slack") and target_url.startswith("http"):
            try:
                headers = {"Content-Type": "application/json"}
                if secret:
                    sig = hmac.new(secret.encode("utf-8"), json.dumps(payload).encode("utf-8"), hashlib.sha256).hexdigest()
                    headers["X-Pace-Signature"] = f"sha256={sig}"

                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(target_url, json=payload, headers=headers)
                    if resp.status_code >= 400:
                        status_str = "failed"
                        error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                status_str = "failed"
                error_msg = str(e)
        else:
            # Console destination logging
            logger.info(f"[PACE ALERT DISPATCHED] [{severity.upper()}] {event_type} - Project: {project_id} - Observed: {observed_value} / Limit: {limit_value}")

        delivery = AlertDelivery(
            project_id=project_id,
            budget_id=budget_id,
            event_type=event_type,
            threshold_percent=threshold_percent,
            severity=severity,
            observed_value=observed_value,
            limit_value=limit_value,
            period_start=period_start,
            period_end=period_end,
            destination_type=dest_type,
            destination_target=target_url[:200],
            status=status_str,
            payload_json=payload,
            error_message=error_msg,
            delivered_at=datetime.now(timezone.utc)
        )
        db.add(delivery)
        await db.commit()
        return delivery
