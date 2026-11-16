# ==============================================================================
# LOGIC OVERVIEW:
# This module manages the LLM Pricing Registry.
#
# KEY RESPONSIBILITIES:
# 1. Default Price Seeding: Automatically seeds standard benchmark token rates
#    for major providers (OpenAI, Anthropic) per 1,000 tokens.
# 2. Multi-dimensional Pricing: Stores 4 separate rates per model:
#    - Input (prompt tokens)
#    - Output (completion tokens)
#    - Cache Read (prompt cache hits)
#    - Reasoning (thinking tokens)
# 3. Custom Rate Overrides: Allows enterprise users to insert custom discounted rates.
# ==============================================================================

from typing import List
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.models import User, PricingRate, AuditLog
from app.schemas.schemas import PricingRateCreate, PricingRateResponse

router = APIRouter(prefix="/pricing", tags=["Pricing"])

# ------------------------------------------------------------------------------
# CORE CODE: Default Pricing Seed Registry
# LOGIC:
# Benchmark rate cards from official provider pricing pages (OpenAI & Anthropic).
# Rates are specified in USD per 1,000 tokens as precise Decimals.
# ------------------------------------------------------------------------------
DEFAULT_PRICING_SEED = [
    {"provider": "openai", "model": "gpt-4o", "input": Decimal("0.00250"), "output": Decimal("0.01000"), "cache": Decimal("0.00125"), "reasoning": Decimal("0.01000"), "url": "https://openai.com/api/pricing/"},
    {"provider": "openai", "model": "gpt-4o-mini", "input": Decimal("0.00015"), "output": Decimal("0.00060"), "cache": Decimal("0.000075"), "reasoning": Decimal("0.00060"), "url": "https://openai.com/api/pricing/"},
    {"provider": "openai", "model": "o1", "input": Decimal("0.01500"), "output": Decimal("0.06000"), "cache": Decimal("0.00750"), "reasoning": Decimal("0.06000"), "url": "https://openai.com/api/pricing/"},
    {"provider": "openai", "model": "o3-mini", "input": Decimal("0.00110"), "output": Decimal("0.00440"), "cache": Decimal("0.00055"), "reasoning": Decimal("0.00440"), "url": "https://openai.com/api/pricing/"},
    {"provider": "anthropic", "model": "claude-3-5-sonnet-20241022", "input": Decimal("0.00300"), "output": Decimal("0.01500"), "cache": Decimal("0.00030"), "reasoning": Decimal("0.01500"), "url": "https://www.anthropic.com/pricing"},
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022", "input": Decimal("0.00080"), "output": Decimal("0.00400"), "cache": Decimal("0.00008"), "reasoning": Decimal("0.00400"), "url": "https://www.anthropic.com/pricing"},
    {"provider": "anthropic", "model": "claude-3-opus-20240229", "input": Decimal("0.01500"), "output": Decimal("0.07500"), "cache": Decimal("0.00150"), "reasoning": Decimal("0.07500"), "url": "https://www.anthropic.com/pricing"},
]

# ------------------------------------------------------------------------------
# CORE CODE: Seed Default Pricing Rates
# LOGIC:
# Ensures the database has baseline rates on startup without overwriting customized user rates.
# ------------------------------------------------------------------------------
async def seed_default_pricing_rates(db: AsyncSession):
    for item in DEFAULT_PRICING_SEED:
        stmt = select(PricingRate).where(
            PricingRate.provider == item["provider"],
            PricingRate.model == item["model"]
        )
        res = await db.execute(stmt)
        if not res.scalar_one_or_none():
            rate = PricingRate(
                provider=item["provider"],
                model=item["model"],
                input_cost_per_1k=item["input"],
                output_cost_per_1k=item["output"],
                cache_read_cost_per_1k=item["cache"],
                reasoning_cost_per_1k=item["reasoning"],
                source_url=item["url"],
                effective_from=datetime(2024, 1, 1, tzinfo=timezone.utc)
            )
            db.add(rate)
    await db.commit()

@router.get("", response_model=List[dict])
async def list_pricing_rates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await seed_default_pricing_rates(db)
    stmt = select(PricingRate).order_by(PricingRate.provider, PricingRate.model)
    res = await db.execute(stmt)
    rates = res.scalars().all()
    
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "model": r.model,
            "input_cost_per_1k": float(r.input_cost_per_1k),
            "output_cost_per_1k": float(r.output_cost_per_1k),
            "cache_read_cost_per_1k": float(r.cache_read_cost_per_1k),
            "reasoning_cost_per_1k": float(r.reasoning_cost_per_1k),
            "currency": r.currency,
            "source_url": r.source_url,
            "effective_from": r.effective_from.isoformat(),
            "is_deprecated": r.is_deprecated
        } for r in rates
    ]

@router.post("", status_code=201)
async def create_pricing_rate(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    rate = PricingRate(
        provider=payload["provider"].lower(),
        model=payload["model"],
        input_cost_per_1k=Decimal(str(payload.get("input_cost_per_1k", 0))),
        output_cost_per_1k=Decimal(str(payload.get("output_cost_per_1k", 0))),
        cache_read_cost_per_1k=Decimal(str(payload.get("cache_read_cost_per_1k", 0))),
        reasoning_cost_per_1k=Decimal(str(payload.get("reasoning_cost_per_1k", 0))),
        source_url=payload.get("source_url"),
        effective_from=datetime.now(timezone.utc)
    )
    db.add(rate)

    audit = AuditLog(
        user_id=current_user.id,
        action="pricing_rate.create",
        resource_type="pricing_rate",
        details_json={"provider": rate.provider, "model": rate.model}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(rate)
    return {"message": "Pricing rate created successfully", "id": rate.id}
