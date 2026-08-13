import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_concurrent_ingestion_idempotency():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register user and create project
        await ac.post("/v1/auth/register", json={"email": "concurrent@pace.dev", "password": "Password123!"})
        login_res = await ac.post("/v1/auth/login", json={"email": "concurrent@pace.dev", "password": "Password123!"})
        token = login_res.json()["access_token"]
        
        proj_res = await ac.post("/v1/projects", json={"name": "Concurrent Ingestion Test"}, headers={"Authorization": f"Bearer {token}"})
        raw_key = proj_res.json()["initial_api_key"]["raw_key"]
        headers = {"Authorization": f"Bearer {raw_key}"}

        event_payload = {
            "event_id": "evt_concurrent_999",
            "provider": "openai",
            "model": "gpt-4o",
            "input_tokens": 100,
            "output_tokens": 50,
            "latency_ms": 200
        }

        # Fire 5 concurrent requests with identical event_id
        tasks = [
            ac.post("/v1/ingest/events", json=event_payload, headers=headers)
            for _ in range(5)
        ]
        responses = await asyncio.gather(*tasks)

        accepted_total = 0
        duplicate_total = 0

        for r in responses:
            assert r.status_code == 200
            data = r.json()
            accepted_total += data["accepted_count"]
            duplicate_total += data["duplicate_count"]

        # Exactly 1 request accepted, remaining 4 reported as duplicate
        assert accepted_total == 1
        assert duplicate_total == 4
