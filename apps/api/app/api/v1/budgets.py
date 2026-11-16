# ==============================================================================
# LOGIC OVERVIEW:
# This module manages cost budgets, spending thresholds, and alert delivery history.
#
# KEY RESPONSIBILITIES:
# 1. Budget Definition: Sets dollar caps per period (daily, weekly, monthly, rolling_24h)
#    and percentage trigger thresholds (e.g. 50%, 80%, 100%, 120%).
# 2. Multi-destination Routing: Dispatches alerts to webhooks, Slack, or console.
# 3. Alert History: Exposes the audit log of all delivered alerts to the dashboard.
# 4. Audit Trail: Automatically logs administrative changes to the AuditLog table.
# ==============================================================================

from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.api.v1.projects import check_project_access
from app.models.models import User, Budget, AlertDelivery, AuditLog

router = APIRouter(prefix="/budgets", tags=["Budgets"])

@router.get("", response_model=List[dict])
async def list_budgets(
    project_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    stmt = select(Budget).where(Budget.project_id == project_id).order_by(Budget.created_at.desc())
    res = await db.execute(stmt)
    budgets = res.scalars().all()

    return [
        {
            "id": b.id,
            "project_id": b.project_id,
            "name": b.name,
            "amount_usd": float(b.amount_usd),
            "period": b.period,
            "metric": b.metric,
            "thresholds": b.thresholds_json,
            "destinations": b.destinations_json,
            "cool_down_minutes": b.cool_down_minutes,
            "is_active": b.is_active,
            "created_at": b.created_at.isoformat()
        } for b in budgets
    ]

# ------------------------------------------------------------------------------
# CORE CODE: Create Budget Endpoint (POST /v1/budgets)
# LOGIC:
# 1. Verifies admin authorization on the target project.
# 2. Stores the spending limit using Decimal precision.
# 3. Configures alert thresholds (e.g. [50, 80, 100, 120]%) and cooldown windows.
# 4. Writes an immutable audit log entry for organizational compliance.
# ------------------------------------------------------------------------------
@router.post("", status_code=201)
async def create_budget(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project_id = payload["project_id"]
    await check_project_access(project_id, current_user.id, db, min_role="admin")

    budget = Budget(
        project_id=project_id,
        name=payload["name"],
        amount_usd=Decimal(str(payload["amount_usd"])),
        period=payload.get("period", "monthly"),
        metric=payload.get("metric", "spend"),
        thresholds_json=payload.get("thresholds", [50, 80, 100, 120]),
        destinations_json=payload.get("destinations", [{"type": "console"}]),
        cool_down_minutes=payload.get("cool_down_minutes", 60),
        is_active=payload.get("is_active", True)
    )
    db.add(budget)

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="budget.create",
        resource_type="budget",
        details_json={"name": budget.name, "amount_usd": float(budget.amount_usd)}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(budget)
    return {"message": "Budget created successfully", "id": budget.id}

@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: str,
    project_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db, min_role="admin")
    stmt = select(Budget).where(Budget.id == budget_id, Budget.project_id == project_id)
    res = await db.execute(stmt)
    budget = res.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    await db.delete(budget)

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="budget.delete",
        resource_type="budget",
        resource_id=budget_id
    )
    db.add(audit)

    await db.commit()
    return {"message": "Budget deleted successfully"}

@router.get("/alerts", response_model=List[dict])
async def list_alerts(
    project_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    stmt = select(AlertDelivery).where(AlertDelivery.project_id == project_id).order_by(AlertDelivery.delivered_at.desc()).limit(100)
    res = await db.execute(stmt)
    alerts = res.scalars().all()

    return [
        {
            "id": a.id,
            "event_type": a.event_type,
            "threshold_percent": a.threshold_percent,
            "severity": a.severity,
            "observed_value": float(a.observed_value),
            "limit_value": float(a.limit_value),
            "destination_type": a.destination_type,
            "destination_target": a.destination_target,
            "status": a.status,
            "payload": a.payload_json,
            "delivered_at": a.delivered_at.isoformat()
        } for a in alerts
    ]
