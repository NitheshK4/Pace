import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_p95_latency_no_events():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "p95_empty@pace.dev", "password": "Password123!"})
        login_res = await ac.post("/v1/auth/login", json={"email": "p95_empty@pace.dev", "password": "Password123!"})
        token = login_res.json()["access_token"]

        proj_res = await ac.post("/v1/projects", json={"name": "Empty Project"}, headers={"Authorization": f"Bearer {token}"})
        proj_id = proj_res.json()["project"]["id"]

        ov_res = await ac.get(f"/v1/analytics/overview?project_id={proj_id}", headers={"Authorization": f"Bearer {token}"})
        assert ov_res.status_code == 200
        data = ov_res.json()
        assert data["total_requests"] == 0
        assert data["p95_latency_ms"] == 0.0
        assert data["avg_latency_ms"] == 0.0

@pytest.mark.asyncio
async def test_p95_latency_calculation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "p95_calc@pace.dev", "password": "Password123!"})
        login_res = await ac.post("/v1/auth/login", json={"email": "p95_calc@pace.dev", "password": "Password123!"})
        token = login_res.json()["access_token"]

        proj_res = await ac.post("/v1/projects", json={"name": "p95 Test Project"}, headers={"Authorization": f"Bearer {token}"})
        proj_id = proj_res.json()["project"]["id"]
        raw_key = proj_res.json()["initial_api_key"]["raw_key"]
        ingest_headers = {"Authorization": f"Bearer {raw_key}"}

        # Ingest 20 events with latencies 100, 200, ..., 2000
        for i in range(1, 21):
            await ac.post("/v1/ingest/events", json={
                "event_id": f"evt_p95_{i}",
                "provider": "openai",
                "model": "gpt-4o",
                "input_tokens": 100,
                "output_tokens": 50,
                "latency_ms": i * 100
            }, headers=ingest_headers)

        ov_res = await ac.get(f"/v1/analytics/overview?project_id={proj_id}", headers={"Authorization": f"Bearer {token}"})
        assert ov_res.status_code == 200
        data = ov_res.json()
        assert data["total_requests"] == 20
        # Average is (100 + ... + 2000)/20 = 1050
        assert data["avg_latency_ms"] == 1050.0
        # True 95th percentile for 100..2000 (20 values): index k = 19 * 0.95 = 18.05 => 1900 + 0.05*100 = 1905
        assert data["p95_latency_ms"] == 1905.0
