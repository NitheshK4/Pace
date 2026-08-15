import csv
import io
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.api.v1.projects import check_project_access
from app.models.models import User, UsageEvent, AuditLog

router = APIRouter(prefix="/exports", tags=["Exports"])

@router.get("/csv")
async def export_events_csv(
    project_id: str = Query(...),
    provider: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    
    stmt = select(UsageEvent).where(UsageEvent.project_id == project_id)
    if provider:
        stmt = stmt.where(UsageEvent.provider == provider.lower())
    if start_time:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        stmt = stmt.where(UsageEvent.time >= start_time)
    if end_time:
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        stmt = stmt.where(UsageEvent.time <= end_time)
    
    stmt = stmt.order_by(desc(UsageEvent.time)).limit(10000)
    res = await db.execute(stmt)
    events = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event ID", "Timestamp (UTC)", "Provider", "Model", "Endpoint",
        "Input Tokens", "Output Tokens", "Cached Tokens", "Reasoning Tokens",
        "Estimated Cost (USD)", "Cost Reason", "Latency (ms)", "Status Code", "Request ID"
    ])

    for ev in events:
        writer.writerow([
            ev.event_id,
            ev.time.isoformat() if ev.time else "",
            ev.provider,
            ev.model,
            ev.endpoint or "",
            ev.input_tokens,
            ev.output_tokens,
            ev.cached_input_tokens,
            ev.reasoning_tokens,
            float(ev.cost_usd) if ev.cost_usd is not None else "",
            ev.cost_reason or "",
            ev.latency_ms,
            ev.status_code,
            ev.request_id or ""
        ])

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="export.csv",
        resource_type="usage_events",
        details_json={"count": len(events)}
    )
    db.add(audit)
    await db.commit()

    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=pace-export-{project_id}.csv"
    return response


@router.get("/json")
async def export_events_json(
    project_id: str = Query(...),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    
    stmt = select(UsageEvent).where(UsageEvent.project_id == project_id)
    if start_time:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        stmt = stmt.where(UsageEvent.time >= start_time)
    if end_time:
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        stmt = stmt.where(UsageEvent.time <= end_time)
    
    stmt = stmt.order_by(desc(UsageEvent.time)).limit(10000)
    res = await db.execute(stmt)
    events = res.scalars().all()

    data = [
        {
            "event_id": ev.event_id,
            "timestamp": ev.time.isoformat() if ev.time else None,
            "provider": ev.provider,
            "model": ev.model,
            "endpoint": ev.endpoint,
            "input_tokens": ev.input_tokens,
            "output_tokens": ev.output_tokens,
            "cached_input_tokens": ev.cached_input_tokens,
            "reasoning_tokens": ev.reasoning_tokens,
            "cost_usd": float(ev.cost_usd) if ev.cost_usd is not None else None,
            "cost_reason": ev.cost_reason,
            "latency_ms": ev.latency_ms,
            "status_code": ev.status_code,
            "request_id": ev.request_id
        }
        for ev in events
    ]

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="export.json",
        resource_type="usage_events",
        details_json={"count": len(events)}
    )
    db.add(audit)
    await db.commit()

    return {"project_id": project_id, "count": len(data), "events": data}

