import pytest
from datetime import datetime, timezone
from app.core.security_url import validate_webhook_url, redact_sensitive_text
from app.services.alert_service import AlertDeliveryService

def test_validate_webhook_url_ssrf():
    # Loopback targets
    valid, err = validate_webhook_url("http://127.0.0.1:8000/api")
    assert not valid
    assert "loopback" in err.lower() or "blocked" in err.lower()

    # Link-local cloud metadata
    valid, err = validate_webhook_url("http://169.254.169.254/latest/meta-data")
    assert not valid
    assert "link-local" in err.lower() or "blocked" in err.lower()

    # Private IP
    valid, err = validate_webhook_url("http://10.0.0.1/webhook")
    assert not valid
    assert "private" in err.lower() or "blocked" in err.lower()

    # Unsupported scheme
    valid, err = validate_webhook_url("ftp://example.com/webhook")
    assert not valid
    assert "scheme" in err.lower()

def test_redact_sensitive_text():
    text = "Failed with Authorization: Bearer sk-proj-secret-key-12345 and token=pace_sec_9999"
    redacted = redact_sensitive_text(text)
    assert "sk-proj-secret-key-12345" not in redacted
    assert "pace_sec_9999" not in redacted
    assert "[REDACTED]" in redacted

@pytest.mark.asyncio
async def test_alert_delivery_ssrf_blocked(db_session):
    now = datetime.now(timezone.utc)
    delivery = await AlertDeliveryService.deliver_alert(
        db=db_session,
        project_id="proj_ssrf_test",
        budget_id=None,
        event_type="budget_alert",
        threshold_percent=80,
        severity="warning",
        observed_value=85.0,
        limit_value=100.0,
        period_start=now,
        period_end=now,
        destination={"type": "webhook", "url": "http://127.0.0.1/malicious-target"}
    )

    assert delivery.status == "failed"
    assert "SSRF Security Violation" in delivery.error_message
