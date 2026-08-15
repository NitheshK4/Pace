import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_payload_too_large_rejection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"content-length": "2000000"}  # > 1MB
        res = await ac.get("/healthz", headers=headers)
        assert res.status_code == 413
        data = res.json()
        assert "Payload too large" in data["detail"]
