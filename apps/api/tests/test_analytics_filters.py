import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_analytics_endpoints_consistent_filtering():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "filters@pace.dev", "password": "Password123!"})
        login_res = await ac.post("/v1/auth/login", json={"email": "filters@pace.dev", "password": "Password123!"})
        token = login_res.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}

        proj_res = await ac.post("/v1/projects", json={"name": "Filters Project"}, headers=user_headers)
        proj_id = proj_res.json()["project"]["id"]
        raw_key = proj_res.json()["initial_api_key"]["raw_key"]
        ingest_headers = {"Authorization": f"Bearer {raw_key}"}

        # 3 OpenAI gpt-4o events
        for i in range(3):
            await ac.post("/v1/ingest/events", json={
                "event_id": f"evt_o_4o_{i}",
                "provider": "openai",
                "model": "gpt-4o",
                "input_tokens": 100,
                "output_tokens": 50
            }, headers=ingest_headers)

        # 2 OpenAI gpt-4o-mini events
        for i in range(2):
            await ac.post("/v1/ingest/events", json={
                "event_id": f"evt_o_mini_{i}",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "input_tokens": 80,
                "output_tokens": 40
            }, headers=ingest_headers)

        # 4 Anthropic claude-3-5-sonnet events
        for i in range(4):
            await ac.post("/v1/ingest/events", json={
                "event_id": f"evt_a_sonnet_{i}",
                "provider": "anthropic",
                "model": "claude-3-5-sonnet",
                "input_tokens": 200,
                "output_tokens": 100
            }, headers=ingest_headers)

        # 1. Filter by provider=openai
        ov = (await ac.get(f"/v1/analytics/overview?project_id={proj_id}&provider=openai", headers=user_headers)).json()
        ts = (await ac.get(f"/v1/analytics/timeseries?project_id={proj_id}&provider=openai", headers=user_headers)).json()
        bd = (await ac.get(f"/v1/analytics/breakdown?project_id={proj_id}&provider=openai", headers=user_headers)).json()
        ev = (await ac.get(f"/v1/analytics/events?project_id={proj_id}&provider=openai", headers=user_headers)).json()

        assert ov["total_requests"] == 5
        assert sum(pt["requests"] for pt in ts["points"]) == 5
        assert sum(item["requests"] for item in bd["by_provider"]) == 5
        assert ev["total"] == 5

        # 2. Filter by model=gpt-4o
        ov_m = (await ac.get(f"/v1/analytics/overview?project_id={proj_id}&model=gpt-4o", headers=user_headers)).json()
        ts_m = (await ac.get(f"/v1/analytics/timeseries?project_id={proj_id}&model=gpt-4o", headers=user_headers)).json()
        bd_m = (await ac.get(f"/v1/analytics/breakdown?project_id={proj_id}&model=gpt-4o", headers=user_headers)).json()
        ev_m = (await ac.get(f"/v1/analytics/events?project_id={proj_id}&model=gpt-4o", headers=user_headers)).json()

        assert ov_m["total_requests"] == 3
        assert sum(pt["requests"] for pt in ts_m["points"]) == 3
        assert sum(item["requests"] for item in bd_m["by_model"]) == 3
        assert ev_m["total"] == 3
