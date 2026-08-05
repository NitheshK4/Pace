import pytest
from httpx import AsyncClient, ASGITransport
from pace_proxy.server import app, clean_headers

@pytest.mark.asyncio
async def test_proxy_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "pace-proxy"
        assert data["loopback_only"] is True
        assert "allowlisted_providers" in data

def test_clean_headers():
    headers = {
        "Host": "api.openai.com",
        "Authorization": "Bearer sk-testkey123",
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }
    cleaned = clean_headers(headers)
    assert "Host" not in cleaned
    assert "Connection" not in cleaned
    assert "Authorization" in cleaned
    assert cleaned["Content-Type"] == "application/json"
