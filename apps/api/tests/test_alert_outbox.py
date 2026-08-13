import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from httpx import Response
from app.services.alert_service import AlertDeliveryService
from app.models.models import AlertDelivery

@pytest.mark.asyncio
async def test_alert_delivery_deduplication(db_session):
    now = datetime.now(timezone.utc)
    dest = {"type": "console"}

    # First delivery -> sent
    d1 = await AlertDeliveryService.deliver_alert(
        db=db_session,
        project_id="p1",
        budget_id="b1",
        event_type="budget_breached",
        threshold_percent=80,
        severity="warning",
        observed_value=85.0,
        limit_value=100.0,
        period_start=now,
        period_end=now,
        destination=dest
    )
    assert d1.status == "sent"

    # Second delivery with identical idempotency parameters -> deduplicated
    d2 = await AlertDeliveryService.deliver_alert(
        db=db_session,
        project_id="p1",
        budget_id="b1",
        event_type="budget_breached",
        threshold_percent=80,
        severity="warning",
        observed_value=85.0,
        limit_value=100.0,
        period_start=now,
        period_end=now,
        destination=dest
    )

    assert d2.id == d1.id

@pytest.mark.asyncio
async def test_outbox_successful_retry(db_session):
    now = datetime.now(timezone.utc)
    
    # Create an alert delivery in retrying state
    delivery = AlertDelivery(
        project_id="p2",
        budget_id="b2",
        event_type="anomaly_detected",
        threshold_percent=100,
        severity="critical",
        observed_value=500.0,
        limit_value=100.0,
        period_start=now,
        period_end=now,
        destination_type="webhook",
        destination_target="http://example.com/webhook",
        status="retrying",
        retry_count=1,
        max_retries=3,
        next_retry_at=now - timedelta(minutes=1),
        payload_json={"event": "test"},
        error_message="HTTP 503"
    )
    db_session.add(delivery)
    await db_session.commit()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(200, json={"ok": True})
        processed = await AlertDeliveryService.process_outbox_retries(db_session)
        assert processed == 1

    await db_session.refresh(delivery)
    assert delivery.status == "sent"
    assert delivery.error_message is None
    assert delivery.next_retry_at is None

@pytest.mark.asyncio
async def test_outbox_permanent_failure(db_session):
    now = datetime.now(timezone.utc)
    
    # Create an alert delivery at max retries - 1
    delivery = AlertDelivery(
        project_id="p3",
        budget_id="b3",
        event_type="budget_breached",
        threshold_percent=100,
        severity="critical",
        observed_value=150.0,
        limit_value=100.0,
        period_start=now,
        period_end=now,
        destination_type="webhook",
        destination_target="http://example.com/webhook",
        status="retrying",
        retry_count=2,
        max_retries=3,
        next_retry_at=now - timedelta(minutes=1),
        payload_json={"event": "test"},
        error_message="HTTP 500"
    )
    db_session.add(delivery)
    await db_session.commit()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = Response(500, text="Internal Error")
        processed = await AlertDeliveryService.process_outbox_retries(db_session)
        assert processed == 1

    await db_session.refresh(delivery)
    assert delivery.retry_count == 3
    assert delivery.status == "failed"
    assert delivery.next_retry_at is None
