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
    db: AsyncSession
) -> Tuple[Optional[Decimal], str]:
    if supplied_cost is not None:
        return supplied_cost, "supplied_by_client"

    # Search for matching pricing rate
    stmt = select(PricingRate).where(
        PricingRate.provider == provider.lower(),
        PricingRate.model == model.lower(),
        PricingRate.is_deprecated == False
    ).order_by(PricingRate.effective_from.desc())
    res = await db.execute(stmt)
    rate = res.scalar_one_or_none()

    if not rate:
        # Try fallback prefix match or wildcards e.g. gpt-4o-2024-05-13 -> gpt-4o
        base_model = model.lower().split('-202')[0]
        stmt2 = select(PricingRate).where(
            PricingRate.provider == provider.lower(),
            PricingRate.model == base_model,
            PricingRate.is_deprecated == False
        )
        res2 = await db.execute(stmt2)
        rate = res2.scalar_one_or_none()

    if not rate:
        return None, "unknown_model"

    # Calculate Decimal cost
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

    for ev in events_list:
        # Pre-check idempotency
        dup_stmt = select(UsageEvent).where(
            UsageEvent.project_id == api_key.project_id,
            UsageEvent.event_id == ev.event_id
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.scalar_one_or_none():
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
