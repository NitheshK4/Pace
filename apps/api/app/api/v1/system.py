from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete
from app.core.database import get_db
from app.core.config import settings
from app.models.models import UsageEvent, AuditLog, User
from app.api.v1.auth import get_current_user
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

router = APIRouter(tags=["System"])

# Metrics
INGESTION_COUNTER = Counter("pace_ingested_events_total", "Total ingested LLM usage events", ["provider", "status"])
REQUEST_LATENCY = Histogram("pace_request_latency_seconds", "API request latency seconds")

import os
import time

START_TIME = time.time()

@router.get("/healthz")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    uptime_seconds = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "database": "connected" if db_ok else "error",
        "version": settings.VERSION,
        "uptime_seconds": uptime_seconds,
        "timescale_enabled": settings.TIMESCALE_ENABLED
    }

@router.get("/metrics")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/v1/system/diagnostics")
async def system_diagnostics(db: AsyncSession = Depends(get_db)):
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    uptime_seconds = round(time.time() - START_TIME, 2)
    pid = os.getpid()

    return {
        "component": "pace-api",
        "version": settings.VERSION,
        "pid": pid,
        "uptime_seconds": uptime_seconds,
        "database_status": "healthy" if db_ok else "unhealthy",
        "timescale_enabled": settings.TIMESCALE_ENABLED,
        "demo_mode": settings.DEMO_MODE,
        "worker_enabled": settings.WORKER_ENABLED,
        "data_retention_days": settings.DATA_RETENTION_DAYS,
        "pricing_registry_version": "2024.11"
    }

@router.post("/v1/system/retention-purge")
async def purge_old_telemetry(
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = delete(UsageEvent).where(UsageEvent.time < cutoff)
    res = await db.execute(stmt)
    purged_count = res.rowcount

    audit = AuditLog(
        user_id=current_user.id,
        action="system.retention_purge",
        resource_type="usage_events",
        details_json={"cutoff": cutoff.isoformat(), "purged_count": purged_count}
    )
    db.add(audit)
    await db.commit()

    return {"message": f"Successfully purged telemetry events older than {days} days", "purged_count": purged_count}
