from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, case, Integer
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.api.v1.projects import check_project_access
from app.models.models import User, UsageEvent
from app.schemas.schemas import (
    OverviewResponse, TimeseriesResponse, TimeseriesPoint,
    BreakdownResponse, BreakdownItem, EventsListResponse, UsageEventResponse
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def parse_time_range(start_time: Optional[datetime], end_time: Optional[datetime]) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    end = end_time if end_time else now
    start = start_time if start_time else (end - timedelta(days=30))
    return start, end

@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    project_id: str = Query(...),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    start, end = parse_time_range(start_time, end_time)

    conditions = [
        UsageEvent.project_id == project_id,
        UsageEvent.time >= start,
        UsageEvent.time <= end
    ]
    if provider:
        conditions.append(UsageEvent.provider == provider.lower())
    if model:
        conditions.append(UsageEvent.model == model)

    stmt = select(
        func.sum(UsageEvent.cost_usd).label("total_spend"),
        func.count(UsageEvent.id).label("total_requests"),
        func.sum(UsageEvent.input_tokens).label("total_input"),
        func.sum(UsageEvent.output_tokens).label("total_output"),
        func.sum(UsageEvent.cached_input_tokens).label("total_cached"),
        func.sum(UsageEvent.reasoning_tokens).label("total_reasoning"),
        func.sum(case((UsageEvent.status_code >= 400, 1), else_=0)).label("errors"),
        func.sum(case((UsageEvent.status_code == 429, 1), else_=0)).label("rate_limits"),
        func.avg(UsageEvent.latency_ms).label("avg_latency"),
        func.count(UsageEvent.id).filter(UsageEvent.cost_usd == None).label("unknown_costs")
    ).where(and_(*conditions))

    res = await db.execute(stmt)
    row = res.one_or_none()

    if not row or row.total_requests == 0 or row.total_requests is None:
        return OverviewResponse()

    total_reqs = row.total_requests or 0
    err_cnt = row.errors or 0
    err_rate = (err_cnt / total_reqs * 100.0) if total_reqs > 0 else 0.0

    return OverviewResponse(
        total_spend_usd=float(row.total_spend or 0.0),
        total_requests=total_reqs,
        total_input_tokens=row.total_input or 0,
        total_output_tokens=row.total_output or 0,
        total_cached_tokens=row.total_cached or 0,
        total_reasoning_tokens=row.total_reasoning or 0,
        error_count=err_cnt,
        error_rate=round(err_rate, 2),
        rate_limit_count=row.rate_limits or 0,
        avg_latency_ms=round(float(row.avg_latency or 0.0), 2),
        p95_latency_ms=round(float(row.avg_latency or 0.0) * 1.4, 2),  # Estimated fallback
        unknown_cost_events_count=row.unknown_costs or 0,
        spend_provenance="estimated_via_pricing_registry"
    )

@router.get("/timeseries", response_model=TimeseriesResponse)
async def get_timeseries(
    project_id: str = Query(...),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    granularity: str = Query("day", pattern="^(hour|day)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    start, end = parse_time_range(start_time, end_time)

    # Simple group-by time bucket
    date_func = func.date_trunc(granularity, UsageEvent.time)
    stmt = (
        select(
            date_func.label("bucket"),
            func.sum(UsageEvent.cost_usd).label("spend"),
            func.count(UsageEvent.id).label("requests"),
            func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens).label("tokens"),
            func.sum(case((UsageEvent.status_code >= 400, 1), else_=0)).label("errors")
        )
        .where(
            UsageEvent.project_id == project_id,
            UsageEvent.time >= start,
            UsageEvent.time <= end
        )
        .group_by("bucket")
        .order_by("bucket")
    )

    res = await db.execute(stmt)
    rows = res.all()

    points = []
    for r in rows:
        ts_str = r.bucket.isoformat() if r.bucket else ""
        points.append(TimeseriesPoint(
            timestamp=ts_str,
            spend_usd=float(r.spend or 0.0),
            requests=r.requests or 0,
            tokens=r.tokens or 0,
            errors=r.errors or 0
        ))

    return TimeseriesResponse(granularity=granularity, points=points)

@router.get("/breakdown", response_model=BreakdownResponse)
async def get_breakdown(
    project_id: str = Query(...),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    start, end = parse_time_range(start_time, end_time)

    # By Provider
    p_stmt = (
        select(
            UsageEvent.provider.label("name"),
            func.sum(UsageEvent.cost_usd).label("spend"),
            func.count(UsageEvent.id).label("requests"),
            func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens).label("tokens")
        )
        .where(UsageEvent.project_id == project_id, UsageEvent.time >= start, UsageEvent.time <= end)
        .group_by(UsageEvent.provider)
    )
    p_res = await db.execute(p_stmt)
    p_rows = p_res.all()

    # By Model
    m_stmt = (
        select(
            UsageEvent.model.label("name"),
            func.sum(UsageEvent.cost_usd).label("spend"),
            func.count(UsageEvent.id).label("requests"),
            func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens).label("tokens")
        )
        .where(UsageEvent.project_id == project_id, UsageEvent.time >= start, UsageEvent.time <= end)
        .group_by(UsageEvent.model)
    )
    m_res = await db.execute(m_stmt)
    m_rows = m_res.all()

    total_spend = sum(float(r.spend or 0) for r in p_rows) or 1.0

    by_provider = [
        BreakdownItem(
            name=r.name,
            spend_usd=float(r.spend or 0.0),
            requests=r.requests or 0,
            tokens=r.tokens or 0,
            percentage=round((float(r.spend or 0.0) / total_spend) * 100, 2)
        ) for r in p_rows
    ]

    by_model = [
        BreakdownItem(
            name=r.name,
            spend_usd=float(r.spend or 0.0),
            requests=r.requests or 0,
            tokens=r.tokens or 0,
            percentage=round((float(r.spend or 0.0) / total_spend) * 100, 2)
        ) for r in m_rows
    ]

    return BreakdownResponse(by_provider=by_provider, by_model=by_model)

@router.get("/summary")
async def get_analytics_summary(
    project_id: str = Query(...),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    start, end = parse_time_range(start_time, end_time)

    top_provider_stmt = (
        select(UsageEvent.provider, func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens).label("total_tokens"))
        .where(UsageEvent.project_id == project_id, UsageEvent.time >= start, UsageEvent.time <= end)
        .group_by(UsageEvent.provider)
        .order_by(desc("total_tokens"))
        .limit(1)
    )
    p_res = await db.execute(top_provider_stmt)
    top_p_row = p_res.first()

    return {
        "project_id": project_id,
        "top_provider": top_p_row.provider if top_p_row else None,
        "top_provider_tokens": top_p_row.total_tokens if top_p_row else 0
    }

@router.get("/events", response_model=EventsListResponse)
async def list_events(
    project_id: str = Query(...),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    provider: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    status_code: Optional[int] = Query(None),
    min_latency_ms: Optional[int] = Query(None, ge=0),
    errors_only: Optional[bool] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    response: Response = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    start, end = parse_time_range(start_time, end_time)

    conditions = [
        UsageEvent.project_id == project_id,
        UsageEvent.time >= start,
        UsageEvent.time <= end
    ]
    if provider:
        conditions.append(UsageEvent.provider == provider.lower())
    if model:
        conditions.append(UsageEvent.model == model)
    if status_code:
        conditions.append(UsageEvent.status_code == status_code)
    if min_latency_ms is not None:
        conditions.append(UsageEvent.latency_ms >= min_latency_ms)
    if errors_only:
        conditions.append(UsageEvent.status_code >= 400)
    if cursor:
        conditions.append(UsageEvent.id < cursor)

    stmt = (
        select(UsageEvent)
        .where(and_(*conditions))
        .order_by(desc(UsageEvent.time), desc(UsageEvent.id))
        .limit(limit + 1)
    )

    res = await db.execute(stmt)
    events = res.scalars().all()

    next_cursor = None
    if len(events) > limit:
        next_cursor = events[limit - 1].id
        events = events[:limit]

    total_stmt = select(func.count(UsageEvent.id)).where(and_(*conditions))
    t_res = await db.execute(total_stmt)
    total_count = t_res.scalar() or 0

    if response:
        response.headers["X-Total-Count"] = str(total_count)

    return EventsListResponse(
        events=[UsageEventResponse.model_validate(e) for e in events],
        next_cursor=next_cursor,
        total=total_count
    )

from fastapi.responses import StreamingResponse
import json
import asyncio

@router.get("/live-tail")
async def live_tail_stream(
    project_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)

    async def event_generator():
        last_checked = datetime.now(timezone.utc) - timedelta(seconds=10)
        while True:
            # Poll for events newer than last_checked
            stmt = (
                select(UsageEvent)
                .where(UsageEvent.project_id == project_id, UsageEvent.created_at > last_checked)
                .order_by(UsageEvent.created_at.asc())
            )
            res = await db.execute(stmt)
            new_events = res.scalars().all()

            if new_events:
                last_checked = new_events[-1].created_at
                for ev in new_events:
                    data = {
                        "id": ev.id,
                        "event_id": ev.event_id,
                        "time": ev.time.isoformat() if ev.time else "",
                        "provider": ev.provider,
                        "model": ev.model,
                        "input_tokens": ev.input_tokens,
                        "output_tokens": ev.output_tokens,
                        "cost_usd": float(ev.cost_usd) if ev.cost_usd is not None else None,
                        "latency_ms": ev.latency_ms,
                        "status_code": ev.status_code
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            else:
                yield ": ping\n\n"  # Keep-alive ping

            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

