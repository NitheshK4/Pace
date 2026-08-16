import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

from app.core.database import Base, get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(autouse=True)
async def prepare_database():
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_payload_too_large_rejection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = {"content-length": "2000000"}  # > 1MB
        res = await ac.get("/healthz", headers=headers)
        assert res.status_code == 413
        data = res.json()
        assert "Payload too large" in data["detail"]

@pytest.mark.asyncio
async def test_empty_events_batch_rejection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "batchlimit@pace.dev", "password": "Password123!"})
        l_res = await ac.post("/v1/auth/login", json={"email": "batchlimit@pace.dev", "password": "Password123!"})
        token = l_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        proj_res = await ac.post("/v1/projects", json={"name": "Batch Limit Test"}, headers=auth_headers)
        raw_key = proj_res.json()["initial_api_key"]["raw_key"]

        res = await ac.post("/v1/ingest/events", json={"events": []}, headers={"Authorization": f"Bearer {raw_key}"})
        assert res.status_code == 422
