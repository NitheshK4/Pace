import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.engine import Engine
from app.main import app

@pytest.mark.asyncio
async def test_batch_ingestion_pricing_query_count():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "perf@pace.dev", "password": "Password123!"})
        login_res = await ac.post("/v1/auth/login", json={"email": "perf@pace.dev", "password": "Password123!"})
        token = login_res.json()["access_token"]

        proj_res = await ac.post("/v1/projects", json={"name": "Batch Perf Project"}, headers={"Authorization": f"Bearer {token}"})
        raw_key = proj_res.json()["initial_api_key"]["raw_key"]
        headers = {"Authorization": f"Bearer {raw_key}"}

        # Build a multi-event batch (20 events)
        batch_events = [
            {
                "event_id": f"evt_perf_{i}",
                "provider": "openai" if i % 2 == 0 else "anthropic",
                "model": "gpt-4o" if i % 2 == 0 else "claude-3-5-sonnet",
                "input_tokens": 500,
                "output_tokens": 200,
                "latency_ms": 150 + i
            }
            for i in range(20)
        ]

        pricing_query_count = 0

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            nonlocal pricing_query_count
            if "pricing_rates" in statement.lower():
                pricing_query_count += 1

        # Track pricing query count for batch request
        event.listen(Engine, "before_cursor_execute", before_cursor_execute)
        try:
            res = await ac.post("/v1/ingest/events", json=batch_events, headers=headers)
        finally:
            event.remove(Engine, "before_cursor_execute", before_cursor_execute)

        assert res.status_code == 200
        assert res.json()["accepted_count"] == 20

        # For 20 events, without bulk optimization it executed 20+ queries on pricing_rates.
        # With bulk optimization, total pricing queries is at most 1 regardless of batch size.
        assert pricing_query_count <= 1, f"Expected <= 1 pricing query for 20 events batch, got {pricing_query_count}"
