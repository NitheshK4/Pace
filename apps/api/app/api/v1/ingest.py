from datetime import datetime, timezone
from typing import List, Optional, Tuple, Union
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.security import hash_project_api_key
from app.models.models import ProjectAPIKey, UsageEvent, PricingRate
from app.schemas.schemas import IngestEventRequest, IngestBatchRequest, IngestEventResponse

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

async def authenticate_project_key(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> ProjectAPIKey:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Expected Bearer pace_...",
        )
    
    raw_key = authorization.replace("Bearer ", "").strip()
    if not raw_key.startswith("pace_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Pace ingestion key format",
        )
    
    key_hash = hash_project_api_key(raw_key)
    stmt = select(ProjectAPIKey).where(
        ProjectAPIKey.key_hash == key_hash,
        ProjectAPIKey.is_active == True
    )
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked Pace ingestion key"
        )
    
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pace ingestion key has expired"
        )
    
    # Touch last_used_at
    api_key.last_used_at = datetime.now(timezone.utc)
    return api_key

async def calculate_event_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    reasoning_tokens: int,
    supplied_cost: Optional[Decimal],
    pricing_cache: dict,
    db: AsyncSession
) -> Tuple[Optional[Decimal], str]:
    if supplied_cost is not None:
        return supplied_cost, "supplied_by_client"

    p_key = provider.lower()
    m_key = model.lower()
    cache_key = (p_key, m_key)

    if cache_key in pricing_cache:
        rate = pricing_cache[cache_key]
    else:
        stmt = select(PricingRate).where(
            PricingRate.provider == p_key,
            PricingRate.model == m_key,
            PricingRate.is_deprecated == False
        ).order_by(PricingRate.effective_from.desc())
        res = await db.execute(stmt)
        rate = res.scalar_one_or_none()

        if not rate:
            base_model = m_key.split('-202')[0]
            base_cache_key = (p_key, base_model)
            if base_cache_key in pricing_cache:
                rate = pricing_cache[base_cache_key]
            else:
                stmt2 = select(PricingRate).where(
                    PricingRate.provider == p_key,
                    PricingRate.model == base_model,
                    PricingRate.is_deprecated == False
                )
                res2 = await db.execute(stmt2)
                rate = res2.scalar_one_or_none()
                pricing_cache[base_cache_key] = rate

        pricing_cache[cache_key] = rate

    if not rate:
        return None, "unknown_model"

    in_cost = (Decimal(input_tokens) / Decimal(1000)) * Decimal(str(rate.input_cost_per_1k))
    out_cost = (Decimal(output_tokens) / Decimal(1000)) * Decimal(str(rate.output_cost_per_1k))
    cache_cost = (Decimal(cached_tokens) / Decimal(1000)) * Decimal(str(rate.cache_read_cost_per_1k))
    reasoning_cost = (Decimal(reasoning_tokens) / Decimal(1000)) * Decimal(str(rate.reasoning_cost_per_1k))
    
    total_cost = in_cost + out_cost + cache_cost + reasoning_cost
    return total_cost, "known"

@router.post("/events", response_model=IngestEventResponse)
async def ingest_events(
    payload: Union[IngestEventRequest, IngestBatchRequest, List[IngestEventRequest]],
    api_key: ProjectAPIKey = Depends(authenticate_project_key),
    db: AsyncSession = Depends(get_db)
):
    if isinstance(payload, IngestEventRequest):
        events_list = [payload]
    elif isinstance(payload, IngestBatchRequest):
        events_list = payload.events
    else:
        events_list = payload

    if len(events_list) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch payload size exceeds maximum limit of 500 events per request."
        )

    accepted_count = 0
    duplicate_count = 0
    rejected_count = 0

    # 1. Bulk pre-fetch active pricing rates in one query
    pricing_cache = {}
    rates_stmt = select(PricingRate).where(PricingRate.is_deprecated == False).order_by(PricingRate.effective_from.desc())
    rates_res = await db.execute(rates_stmt)
    for rate in rates_res.scalars().all():
        p = rate.provider.lower()
        m = rate.model.lower()
        key = (p, m)
        if key not in pricing_cache:
            pricing_cache[key] = rate
        base_m = m.split('-202')[0]
        base_key = (p, base_m)
        if base_key not in pricing_cache:
            pricing_cache[base_key] = rate

    # 2. Bulk pre-fetch duplicate event_ids in one query
    event_ids = [ev.event_id for ev in events_list]
    existing_dup_stmt = select(UsageEvent.event_id).where(
        UsageEvent.project_id == api_key.project_id,
        UsageEvent.event_id.in_(event_ids)
    )
    existing_dup_res = await db.execute(existing_dup_stmt)
    existing_dup_set = set(existing_dup_res.scalars().all())

    for ev in events_list:
        if ev.event_id in existing_dup_set:
            duplicate_count += 1
            continue

        cost_usd, cost_reason = await calculate_event_cost(
            provider=ev.provider,
            model=ev.model,
            input_tokens=ev.input_tokens,
            output_tokens=ev.output_tokens,
            cached_tokens=ev.cached_input_tokens,
            reasoning_tokens=ev.reasoning_tokens,
            supplied_cost=ev.cost_usd,
            pricing_cache=pricing_cache,
            db=db
        )

        event_time = ev.time if ev.time else datetime.now(timezone.utc)

        db_event = UsageEvent(
            project_id=api_key.project_id,
            event_id=ev.event_id,
            time=event_time,
            provider=ev.provider.lower(),
            model=ev.model,
            endpoint=ev.endpoint,
            input_tokens=ev.input_tokens,
            output_tokens=ev.output_tokens,
            cached_input_tokens=ev.cached_input_tokens,
            reasoning_tokens=ev.reasoning_tokens,
            cost_usd=cost_usd,
            cost_reason=cost_reason,
            latency_ms=ev.latency_ms,
            status_code=ev.status_code,
            request_id=ev.request_id,
            metadata_json=ev.metadata
        )
        try:
            async with db.begin_nested():
                db.add(db_event)
                await db.flush()
            existing_dup_set.add(ev.event_id)
            accepted_count += 1
        except IntegrityError:
            duplicate_count += 1
            continue

    await db.commit()
    return IngestEventResponse(
        status="accepted",
        accepted_count=accepted_count,
        duplicate_count=duplicate_count,
        rejected_count=rejected_count
    )
