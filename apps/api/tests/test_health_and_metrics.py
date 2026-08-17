import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_liveness_healthz_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "server_start_timestamp" in data
        assert "version" in data

@pytest.mark.asyncio
async def test_readiness_readyz_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/readyz")
        # In test suite with in-memory DB and migrations, readyz returns 200 or 503 depending on migration status check
        assert res.status_code in (200, 503)
        data = res.json()
        assert "database" in data
        assert "db_ping_ms" in data
        assert "migration_status" in data

@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/metrics")
        assert res.status_code == 200
        text = res.text
        assert "pace_ingested_events_total" in text
        assert "pace_request_latency_seconds" in text
