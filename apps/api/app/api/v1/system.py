import os
import time
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Response, status as http_status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, delete
from app.core.database import get_db
from app.core.config import settings
from app.core.migrations import check_migration_status
from app.models.models import UsageEvent, AuditLog, User
from app.api.v1.auth import get_current_user
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram

router = APIRouter(tags=["System"])

# Operational Metrics
INGESTION_COUNTER = Counter("pace_ingested_events_total", "Total ingested LLM usage events", ["provider", "status"])
INGESTION_BATCH_HISTOGRAM = Histogram("pace_ingestion_batch_size", "Ingestion batch payload sizes")
HTTP_REQUESTS_TOTAL = Counter("pace_http_requests_total", "Total HTTP requests received", ["method", "endpoint", "status"])
ALERT_DELIVERIES_COUNTER = Counter("pace_alert_deliveries_total", "Total alert delivery attempts", ["destination_type", "status"])
WORKER_EVALUATION_COUNTER = Counter("pace_worker_evaluation_cycles_total", "Total worker evaluation cycles", ["status"])
REQUEST_LATENCY = Histogram("pace_request_latency_seconds", "API request latency seconds")

START_TIME = time.time()

@router.get("/healthz")
async def health_check():
    """Liveness probe: returns HTTP 200 as long as API process is running."""
    uptime_seconds = round(time.time() - START_TIME, 2)
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "uptime_seconds": uptime_seconds,
        "environment": settings.ENVIRONMENT
    }

@router.get("/readyz")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness probe: checks DB connection and Alembic migration status."""
    db_ok = False
    migration_info = None

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False

    if db_ok:
        try:
            conn = await db.connection()
            migration_info = await conn.run_sync(check_migration_status)
        except Exception:
            migration_info = {"is_up_to_date": False, "error": "Failed checking alembic_version table"}

    is_ready = db_ok and (migration_info.get("is_up_to_date") if migration_info else False)
    status_code = http_status.HTTP_200_OK if is_ready else http_status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "database": "connected" if db_ok else "error",
            "migration_status": migration_info if migration_info else {"is_up_to_date": False},
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT
        }
    )

@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
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
        "status": "ok",
        "component": "pace-api",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
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
