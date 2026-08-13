import hmac
import hashlib
import json
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.models import AlertDelivery
from app.core.security_url import validate_webhook_url, redact_sensitive_text

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
        destination: Dict[str, Any],
        max_retries: int = 3
    ) -> AlertDelivery:
        idempotency_key = f"{project_id}:{budget_id or 'nobudget'}:{event_type}:{threshold_percent or 0}:{period_start.isoformat()}"

        # Deduplication check: do not resend if already delivered
        existing_stmt = select(AlertDelivery).where(
            AlertDelivery.idempotency_key == idempotency_key,
            AlertDelivery.status == "sent"
        )
        existing_res = await db.execute(existing_stmt)
        existing_delivery = existing_res.scalar_one_or_none()
        if existing_delivery:
            logger.info(f"Alert delivery deduplicated for idempotency_key {idempotency_key}")
            return existing_delivery

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
        retry_count = 0
        next_retry_at = None

        if dest_type in ("webhook", "slack"):
            is_valid, validation_err = validate_webhook_url(target_url)
            if not is_valid:
                status_str = "failed"
                error_msg = redact_sensitive_text(f"SSRF Security Violation: {validation_err}")
            else:
                try:
                    headers = {"Content-Type": "application/json"}
                    if secret:
                        sig = hmac.new(secret.encode("utf-8"), json.dumps(payload).encode("utf-8"), hashlib.sha256).hexdigest()
                        headers["X-Pace-Signature"] = f"sha256={sig}"

                    async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                        resp = await client.post(target_url, json=payload, headers=headers)
                        if resp.status_code >= 500:
                            status_str = "retrying"
                            retry_count = 1
                            next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=60)
                            error_msg = redact_sensitive_text(f"HTTP {resp.status_code}")
                        elif resp.status_code >= 400:
                            status_str = "failed"
                            error_msg = redact_sensitive_text(f"HTTP {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    status_str = "retrying"
                    retry_count = 1
                    next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=60)
                    error_msg = redact_sensitive_text(str(e))
        else:
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
            destination_target=redact_sensitive_text(target_url[:200]),
            status=status_str,
            retry_count=retry_count,
            max_retries=max_retries,
            next_retry_at=next_retry_at,
            idempotency_key=idempotency_key,
            payload_json=payload,
            error_message=error_msg,
            delivered_at=datetime.now(timezone.utc)
        )
        db.add(delivery)
        await db.commit()
        return delivery

    @staticmethod
    async def process_outbox_retries(db: AsyncSession) -> int:
        """Processes pending retries for failed transient alert deliveries."""
        now = datetime.now(timezone.utc)
        stmt = select(AlertDelivery).where(
            AlertDelivery.status == "retrying",
            AlertDelivery.next_retry_at <= now
        )
        res = await db.execute(stmt)
        pending_deliveries = res.scalars().all()

        processed_count = 0
        for delivery in pending_deliveries:
            target_url = delivery.destination_target
            payload = delivery.payload_json

            try:
                async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                    resp = await client.post(target_url, json=payload, headers={"Content-Type": "application/json"})
                    if resp.status_code < 400:
                        delivery.status = "sent"
                        delivery.delivered_at = datetime.now(timezone.utc)
                        delivery.error_message = None
                        delivery.next_retry_at = None
                    else:
                        delivery.retry_count += 1
                        if delivery.retry_count >= delivery.max_retries:
                            delivery.status = "failed"
                            delivery.next_retry_at = None
                        else:
                            backoff = 60 * (2 ** (delivery.retry_count - 1))
                            delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
                        delivery.error_message = redact_sensitive_text(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                delivery.retry_count += 1
                if delivery.retry_count >= delivery.max_retries:
                    delivery.status = "failed"
                    delivery.next_retry_at = None
                else:
                    backoff = 60 * (2 ** (delivery.retry_count - 1))
                    delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
                delivery.error_message = redact_sensitive_text(str(e))

            processed_count += 1

        await db.commit()
        return processed_count
