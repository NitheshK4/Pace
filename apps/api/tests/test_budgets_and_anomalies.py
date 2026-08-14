import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base, get_db
from app.models.models import Budget, UsageEvent, AlertDelivery
from app.services.budget_service import calculate_period_bounds, BudgetEvaluationService
from app.services.anomaly_service import AnomalyDetectorService
from app.main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_period_bounds():
    now = datetime(2026, 7, 20, 14, 30, tzinfo=timezone.utc)
    
    d_start, d_end = calculate_period_bounds("daily", now)
    assert d_start.day == 20
    assert d_end.day == 21
    
    m_start, m_end = calculate_period_bounds("monthly", now)
    assert m_start.month == 7
    assert m_start.day == 1

    w_start, w_end = calculate_period_bounds("weekly", now)
    assert w_start <= now < w_end

@pytest.mark.asyncio
async def test_budget_evaluation_and_deduplication():
    async with TestingSessionLocal() as db:
        budget = Budget(
            project_id="proj_test123",
            name="Test Monthly Budget",
            amount_usd=Decimal("10.00"),
            period="monthly",
            metric="spend",
            thresholds_json=[50, 100],
            destinations_json=[{"type": "console"}],
            is_active=True
        )
        db.add(budget)
        await db.commit()
        await db.refresh(budget)

        ev1 = UsageEvent(
            project_id="proj_test123",
            event_id="evt_spend1",
            time=datetime.now(timezone.utc),
            provider="openai",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=Decimal("6.00"),
            status_code=200
        )
        db.add(ev1)
        await db.commit()

        deliv1 = await BudgetEvaluationService.evaluate_budget(db, budget)
        assert len(deliv1) == 1
        assert deliv1[0].threshold_percent == 50
        assert deliv1[0].event_type == "budget.threshold_breached"

        deliv2 = await BudgetEvaluationService.evaluate_budget(db, budget)
        assert len(deliv2) == 0

@pytest.mark.asyncio
async def test_anomaly_detector_safeguard():
    async with TestingSessionLocal() as db:
        anomalies = await AnomalyDetectorService.detect_anomalies(db, "proj_empty")
        assert anomalies == []
