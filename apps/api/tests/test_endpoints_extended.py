import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base, get_db
from app.models import models
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

from app.api.v1.pricing import seed_default_pricing_rates

@pytest.fixture(autouse=True)
async def prepare_database():
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        await seed_default_pricing_rates(session)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_system_health_and_diagnostics():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        health_res = await ac.get("/healthz")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "healthy"
        assert "uptime_seconds" in health_res.json()

        metrics_res = await ac.get("/metrics")
        assert metrics_res.status_code == 200
        assert "python_info" in metrics_res.text or "process" in metrics_res.text or "pace" in metrics_res.text

        diag_res = await ac.get("/v1/system/diagnostics")
        assert diag_res.status_code == 200
        data = diag_res.json()
        assert "database_status" in data
        assert data["database_status"] == "healthy"

@pytest.mark.asyncio
async def test_pricing_registry_management():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "pricing@pace.dev", "password": "Password123!"})
        l_res = await ac.post("/v1/auth/login", json={"email": "pricing@pace.dev", "password": "Password123!"})
        token = l_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        rates_res = await ac.get("/v1/pricing", headers=headers)
        assert rates_res.status_code == 200
        rates = rates_res.json()
        assert len(rates) > 0

        custom_rate = {
            "provider": "custom_llm",
            "model": "custom-v1",
            "input_cost_per_1k": 0.002,
            "output_cost_per_1k": 0.006,
            "cached_input_cost_per_1k": 0.001,
            "reasoning_cost_per_1k": 0.008
        }
        create_res = await ac.post("/v1/pricing", json=custom_rate, headers=headers)
        assert create_res.status_code == 201
        data = create_res.json()
        assert "id" in data
        assert data["message"] == "Pricing rate created successfully"

@pytest.mark.asyncio
async def test_csv_export_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "exporter@pace.dev", "password": "Password123!"})
        l_res = await ac.post("/v1/auth/login", json={"email": "exporter@pace.dev", "password": "Password123!"})
        token = l_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        proj_res = await ac.post("/v1/projects", json={"name": "Export Test Project"}, headers=auth_headers)
        project_id = proj_res.json()["project"]["id"]
        raw_key = proj_res.json()["initial_api_key"]["raw_key"]

        event = {
            "event_id": "evt_csv_001",
            "provider": "openai",
            "model": "gpt-4o",
            "input_tokens": 500,
            "output_tokens": 150,
            "latency_ms": 220
        }
        await ac.post("/v1/ingest/events", json=event, headers={"Authorization": f"Bearer {raw_key}"})

        csv_res = await ac.get(f"/v1/exports/csv?project_id={project_id}", headers=auth_headers)
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        assert "evt_csv_001" in csv_res.text
        assert "gpt-4o" in csv_res.text

@pytest.mark.asyncio
async def test_events_min_latency_and_errors_filtering():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "filtertest@pace.dev", "password": "Password123!"})
        l_res = await ac.post("/v1/auth/login", json={"email": "filtertest@pace.dev", "password": "Password123!"})
        token = l_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        proj_res = await ac.post("/v1/projects", json={"name": "Filter Test Project"}, headers=auth_headers)
        project_id = proj_res.json()["project"]["id"]
        raw_key = proj_res.json()["initial_api_key"]["raw_key"]

        # Ingest fast ok event
        await ac.post("/v1/ingest/events", json={
            "event_id": "evt_fast_ok",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "input_tokens": 100,
            "output_tokens": 50,
            "latency_ms": 120,
            "status_code": 200
        }, headers={"Authorization": f"Bearer {raw_key}"})

        # Ingest slow error event
        await ac.post("/v1/ingest/events", json={
            "event_id": "evt_slow_err",
            "provider": "openai",
            "model": "gpt-4o",
            "input_tokens": 1000,
            "output_tokens": 200,
            "latency_ms": 1500,
            "status_code": 429
        }, headers={"Authorization": f"Bearer {raw_key}"})

        # Query min latency filter (>= 500ms)
        latency_res = await ac.get(f"/v1/analytics/events?project_id={project_id}&min_latency_ms=500", headers=auth_headers)
        assert latency_res.status_code == 200
        assert latency_res.headers.get("X-Total-Count") == "1"
        data = latency_res.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["event_id"] == "evt_slow_err"

        # Query errors only filter
        err_res = await ac.get(f"/v1/analytics/events?project_id={project_id}&errors_only=true", headers=auth_headers)
        assert err_res.status_code == 200
        data_err = err_res.json()
        assert len(data_err["events"]) == 1
        assert data_err["events"][0]["status_code"] == 429

