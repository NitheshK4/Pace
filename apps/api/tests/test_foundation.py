import pytest
import asyncio
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base, get_db
from app.core.security import get_password_hash, verify_password, generate_project_api_key, hash_project_api_key, validate_api_key_format
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
async def test_security_utils():
    password = "SecurePassword123!"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)

    raw_key, key_hash, prefix = generate_project_api_key()
    assert raw_key.startswith("pace_")
    assert prefix == raw_key[:12]
    assert hash_project_api_key(raw_key) == key_hash
    assert validate_api_key_format(raw_key) is True
    assert validate_api_key_format("invalid_key") is False
    assert validate_api_key_format("pace_short") is False
    assert validate_api_key_format("") is False
    assert validate_api_key_format(None) is False

@pytest.mark.asyncio
async def test_auth_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        reg_resp = await ac.post("/v1/auth/register", json={
            "email": "user1@pace.dev",
            "password": "Password123!",
            "full_name": "User One"
        })
        assert reg_resp.status_code == 201
        assert reg_resp.json()["email"] == "user1@pace.dev"

        login_resp = await ac.post("/v1/auth/login", json={
            "email": "user1@pace.dev",
            "password": "Password123!"
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        assert token is not None

        me_resp = await ac.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "user1@pace.dev"

@pytest.mark.asyncio
async def test_project_and_key_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "owner@pace.dev", "password": "Password123!"})
        login_res = await ac.post("/v1/auth/login", json={"email": "owner@pace.dev", "password": "Password123!"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        proj_res = await ac.post("/v1/projects", json={"name": "Production AI Service"}, headers=headers)
        assert proj_res.status_code == 201
        data = proj_res.json()
        project_id = data["project"]["id"]
        raw_key = data["initial_api_key"]["raw_key"]
        assert raw_key.startswith("pace_")

        list_res = await ac.get("/v1/projects", headers=headers)
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1

        key2_res = await ac.post(f"/v1/projects/{project_id}/keys", json={"name": "Staging Key"}, headers=headers)
        assert key2_res.status_code == 201
        raw_key2 = key2_res.json()["raw_key"]
        assert raw_key2.startswith("pace_")

        keys_res = await ac.get(f"/v1/projects/{project_id}/keys", headers=headers)
        assert keys_res.status_code == 200
        for k in keys_res.json():
            assert "raw_key" not in k

@pytest.mark.asyncio
async def test_cross_user_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "usera@pace.dev", "password": "Password123!"})
        l1 = await ac.post("/v1/auth/login", json={"email": "usera@pace.dev", "password": "Password123!"})
        t1 = l1.json()["access_token"]
        p1_res = await ac.post("/v1/projects", json={"name": "User A Project"}, headers={"Authorization": f"Bearer {t1}"})
        p1_id = p1_res.json()["project"]["id"]

        await ac.post("/v1/auth/register", json={"email": "userb@pace.dev", "password": "Password123!"})
        l2 = await ac.post("/v1/auth/login", json={"email": "userb@pace.dev", "password": "Password123!"})
        t2 = l2.json()["access_token"]

        get_res = await ac.get(f"/v1/projects/{p1_id}", headers={"Authorization": f"Bearer {t2}"})
        assert get_res.status_code == 404

@pytest.mark.asyncio
async def test_event_ingestion_and_privacy():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/v1/auth/register", json={"email": "ingest@pace.dev", "password": "Password123!"})
        l1 = await ac.post("/v1/auth/login", json={"email": "ingest@pace.dev", "password": "Password123!"})
        t1 = l1.json()["access_token"]
        p1_res = await ac.post("/v1/projects", json={"name": "Ingestion Test Project"}, headers={"Authorization": f"Bearer {t1}"})
        project_id = p1_res.json()["project"]["id"]
        raw_key = p1_res.json()["initial_api_key"]["raw_key"]
        ingest_headers = {"Authorization": f"Bearer {raw_key}"}

        ev1 = {
            "event_id": "evt_001",
            "provider": "openai",
            "model": "gpt-4o",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cached_input_tokens": 200,
            "latency_ms": 450,
            "status_code": 200,
            "metadata": {"environment": "production", "service": "chat-service"}
        }
        res1 = await ac.post("/v1/ingest/events", json=ev1, headers=ingest_headers)
        assert res1.status_code == 200
        assert res1.json()["accepted_count"] == 1

        res_dup = await ac.post("/v1/ingest/events", json=ev1, headers=ingest_headers)
        assert res_dup.status_code == 200
        assert res_dup.json()["duplicate_count"] == 1

        ev_forbidden = {
            "event_id": "evt_forbidden",
            "provider": "openai",
            "model": "gpt-4o",
            "input_tokens": 100,
            "output_tokens": 50,
            "metadata": {"prompt": "What is the secret key?"}
        }
        res_forbid = await ac.post("/v1/ingest/events", json=ev_forbidden, headers=ingest_headers)
        assert res_forbid.status_code == 422

        ev_unknown = {
            "event_id": "evt_unknown",
            "provider": "custom_provider",
            "model": "my-custom-fine-tuned-model",
            "input_tokens": 1000,
            "output_tokens": 500,
            "latency_ms": 300
        }
        res_unk = await ac.post("/v1/ingest/events", json=ev_unknown, headers=ingest_headers)
        assert res_unk.status_code == 200

        user_headers = {"Authorization": f"Bearer {t1}"}
        overview_res = await ac.get(f"/v1/analytics/overview?project_id={project_id}", headers=user_headers)
        assert overview_res.status_code == 200
        ov_data = overview_res.json()
        assert ov_data["total_requests"] == 2
        assert ov_data["unknown_cost_events_count"] == 1
        assert ov_data["total_spend_usd"] > 0.0

@pytest.mark.asyncio
async def test_request_id_header_middleware():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/healthz")
        assert res.status_code == 200
        assert "X-Request-ID" in res.headers
        assert "X-Response-Time-Ms" in res.headers

from app.core.security import validate_environment_tag, format_token_count

def test_validate_environment_tag():
    assert validate_environment_tag(None) is False
    assert validate_environment_tag("") is False
    assert validate_environment_tag("invalid_env") is False
    assert validate_environment_tag("production") is True
    assert validate_environment_tag("STAGING") is True
    assert validate_environment_tag("development") is True

def test_format_token_count():
    assert format_token_count(-5) == "0"
    assert format_token_count(500) == "500"
    assert format_token_count(1500) == "1.5k"
    assert format_token_count(2_500_000) == "2.5M"


