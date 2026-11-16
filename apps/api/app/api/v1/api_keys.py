# ==============================================================================
# LOGIC OVERVIEW:
# This module handles API key lifecycle management (creation, listing, revocation).
#
# KEY SECURITY PROPERTIES:
# 1. Zero Secret Storage: The raw secret 'pace_...' is generated and returned to the caller ONCE.
#    Only the HMAC-SHA256 hash is saved in the database.
# 2. Key Identification: Stores a non-sensitive 'key_prefix' (e.g. 'pace_live_ab12...')
#    allowing users to recognize keys without compromising the secret.
# 3. Soft Revocation: Revocation marks is_active=False instead of hard deletion
#    to maintain referential integrity in audit records.
# ==============================================================================

from typing import List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.api.v1.projects import check_project_access
from app.models.models import User, ProjectAPIKey, AuditLog
from app.schemas.schemas import APIKeyCreate, APIKeyResponse, APIKeyCreatedResponse
from app.core.security import generate_project_api_key

router = APIRouter(prefix="/projects/{project_id}/keys", tags=["API Keys"])

@router.get("", response_model=List[APIKeyResponse])
async def list_keys(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db)
    stmt = select(ProjectAPIKey).where(
        ProjectAPIKey.project_id == project_id,
        ProjectAPIKey.is_active == True
    ).order_by(ProjectAPIKey.created_at.desc())
    result = await db.execute(stmt)
    keys = result.scalars().all()
    return keys

# ------------------------------------------------------------------------------
# CORE CODE: Create Ingestion Key Endpoint (POST /projects/{id}/keys)
# LOGIC:
# 1. Calls generate_project_api_key() returning (raw_key, key_hash, key_prefix).
# 2. Computes optional expiration date.
# 3. Saves hashed token to DB; returns raw_key to caller in response.
# ------------------------------------------------------------------------------
@router.post("", response_model=APIKeyCreatedResponse, status_code=201)
async def create_key(
    project_id: str,
    req: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db, min_role="admin")
    
    raw_key, key_hash, key_prefix = generate_project_api_key()
    expires_at = None
    if req.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.expires_in_days)
    
    api_key = ProjectAPIKey(
        project_id=project_id,
        name=req.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        expires_at=expires_at
    )
    db.add(api_key)

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="api_key.create",
        resource_type="api_key",
        resource_id=api_key.id,
        details_json={"name": req.name, "prefix": key_prefix}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(api_key)

    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        raw_key=raw_key,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at
    )

@router.delete("/{key_id}")
async def revoke_key(
    project_id: str,
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await check_project_access(project_id, current_user.id, db, min_role="admin")
    stmt = select(ProjectAPIKey).where(
        ProjectAPIKey.id == key_id,
        ProjectAPIKey.project_id == project_id
    )
    result = await db.execute(stmt)
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    key.is_active = False

    audit = AuditLog(
        project_id=project_id,
        user_id=current_user.id,
        action="api_key.revoke",
        resource_type="api_key",
        resource_id=key_id,
        details_json={"name": key.name, "prefix": key.key_prefix}
    )
    db.add(audit)

    await db.commit()
    return {"message": "Key revoked successfully"}
