import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_stable_cursor_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "cursor@pace.dev", "password": "Password123!"})
        login_res = await ac.post("/v1/auth/login", json={"email": "cursor@pace.dev", "password": "Password123!"})
        token = login_res.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {token}"}

        proj_res = await ac.post("/v1/projects", json={"name": "Cursor Pagination Project"}, headers=user_headers)
        proj_id = proj_res.json()["project"]["id"]
        raw_key = proj_res.json()["initial_api_key"]["raw_key"]
        ingest_headers = {"Authorization": f"Bearer {raw_key}"}

        # Ingest 5 events
        for i in range(1, 6):
            await ac.post("/v1/ingest/events", json={
                "event_id": f"evt_page_{i}",
                "provider": "openai",
                "model": "gpt-4o",
                "input_tokens": 100 * i,
                "output_tokens": 50 * i
            }, headers=ingest_headers)

        # Page 1: limit 2
        p1_res = await ac.get(f"/v1/analytics/events?project_id={proj_id}&limit=2", headers=user_headers)
        assert p1_res.status_code == 200
        p1_data = p1_res.json()
        assert len(p1_data["events"]) == 2
        assert p1_data["has_more"] is True
        assert p1_data["next_cursor"] is not None
        p1_ids = [e["event_id"] for e in p1_data["events"]]

        # Page 2: limit 2 using next_cursor
        p2_res = await ac.get(f"/v1/analytics/events?project_id={proj_id}&limit=2&cursor={p1_data['next_cursor']}", headers=user_headers)
        assert p2_res.status_code == 200
        p2_data = p2_res.json()
        assert len(p2_data["events"]) == 2
        assert p2_data["has_more"] is True
        assert p2_data["next_cursor"] is not None
        p2_ids = [e["event_id"] for e in p2_data["events"]]

        # Verify no overlap between page 1 and page 2
        assert set(p1_ids).isdisjoint(set(p2_ids))

        # Page 3: limit 2 using next_cursor from Page 2
        p3_res = await ac.get(f"/v1/analytics/events?project_id={proj_id}&limit=2&cursor={p2_data['next_cursor']}", headers=user_headers)
        assert p3_res.status_code == 200
        p3_data = p3_res.json()
        assert len(p3_data["events"]) == 1
        assert p3_data["has_more"] is False
        p3_ids = [e["event_id"] for e in p3_data["events"]]

        # Total events across all pages == 5
        assert len(set(p1_ids + p2_ids + p3_ids)) == 5
