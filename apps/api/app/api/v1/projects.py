import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.models import User, Project, ProjectMember, ProjectAPIKey, AuditLog
from app.schemas.schemas import ProjectCreate, ProjectResponse, APIKeyCreatedResponse
from app.core.security import generate_project_api_key

router = APIRouter(prefix="/projects", tags=["Projects"])

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text or "project"

async def check_project_access(project_id: str, user_id: str, db: AsyncSession, min_role: str = "viewer") -> Project:
    stmt = select(Project).join(ProjectMember).where(
        Project.id == project_id,
        ProjectMember.user_id == user_id
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    return project

@router.post("", response_model=dict, status_code=201)
async def create_project(
    req: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    base_slug = slugify(req.name)
    slug = base_slug
    counter = 1
    while True:
        res = await db.execute(select(Project).where(Project.slug == slug))
        if not res.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    project = Project(
        name=req.name,
        slug=slug,
        owner_id=current_user.id
    )
    db.add(project)
    await db.flush()

    # Add member
    member = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role="owner"
    )
    db.add(member)

    # Generate initial ingestion key
    raw_key, key_hash, key_prefix = generate_project_api_key()
    api_key = ProjectAPIKey(
        project_id=project.id,
        name="Default Key",
        key_prefix=key_prefix,
        key_hash=key_hash
    )
    db.add(api_key)

    # Audit log
    audit = AuditLog(
        project_id=project.id,
        user_id=current_user.id,
        action="project.create",
        resource_type="project",
        resource_id=project.id,
        details_json={"name": project.name, "slug": project.slug}
    )
    db.add(audit)

    await db.commit()
    await db.refresh(project)
    await db.refresh(api_key)

    return {
        "project": ProjectResponse.model_validate(project),
        "initial_api_key": {
            "id": api_key.id,
            "name": api_key.name,
            "key_prefix": api_key.key_prefix,
            "raw_key": raw_key,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at
        }
    }

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Project, ProjectMember.role)
        .join(ProjectMember, Project.id == ProjectMember.project_id)
        .where(ProjectMember.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    output = []
    for proj, role in rows:
        p_resp = ProjectResponse.model_validate(proj)
        p_resp.role = role
        output.append(p_resp)
    return output

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await check_project_access(project_id, current_user.id, db)
    return project
