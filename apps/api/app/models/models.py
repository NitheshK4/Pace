import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey, JSON, Index, UniqueConstraint, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    memberships: Mapped[List["ProjectMember"]] = relationship("ProjectMember", back_populates="user", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    members: Mapped[List["ProjectMember"]] = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    api_keys: Mapped[List["ProjectAPIKey"]] = relationship("ProjectAPIKey", back_populates="project", cascade="all, delete-orphan")
    events: Mapped[List["UsageEvent"]] = relationship("UsageEvent", back_populates="project", cascade="all, delete-orphan")
    budgets: Mapped[List["Budget"]] = relationship("Budget", back_populates="project", cascade="all, delete-orphan")

class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="owner", nullable=False)  # owner, admin, viewer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )

class ProjectAPIKey(Base):
    __tablename__ = "project_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), index=True, nullable=False)  # pace_12345678
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="api_keys")

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Idempotency token
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # openai, anthropic
    model: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    endpoint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reasoning_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(14, 8), nullable=True)  # NUMERIC, NULL if unknown
    cost_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 'known', 'partial', 'unknown_model'
    
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=200, index=True, nullable=False)
    request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="events")

    __table_args__ = (
        UniqueConstraint("project_id", "event_id", name="uq_project_event"),
        Index("idx_events_project_time", "project_id", "time"),
        Index("idx_events_project_provider_model", "project_id", "provider", "model"),
        Index("idx_events_project_status", "project_id", "status_code"),
    )

class PricingRate(Base):
    __tablename__ = "pricing_rates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    provider: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    model_pattern: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    input_cost_per_1k: Mapped[float] = mapped_column(Numeric(14, 8), default=0, nullable=False)
    output_cost_per_1k: Mapped[float] = mapped_column(Numeric(14, 8), default=0, nullable=False)
    cache_read_cost_per_1k: Mapped[float] = mapped_column(Numeric(14, 8), default=0, nullable=False)
    reasoning_cost_per_1k: Mapped[float] = mapped_column(Numeric(14, 8), default=0, nullable=False)
    
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("provider", "model", "effective_from", name="uq_provider_model_effective"),
    )

class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_usd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    period: Mapped[str] = mapped_column(String(50), default="monthly", nullable=False)  # daily, weekly, monthly, rolling_24h
    metric: Mapped[str] = mapped_column(String(50), default="spend", nullable=False)  # spend, tokens, requests, error_rate, latency
    thresholds_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # [50, 80, 100, 120]
    destinations_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # list of webhook/email configs
    quiet_hours_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    cool_down_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    project: Mapped["Project"] = relationship("Project", back_populates="budgets")

class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    budget_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("budgets.id", ondelete="SET NULL"), nullable=True)
    
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)  # budget_breached, rate_limit_spike, anomaly_detected
    threshold_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning", nullable=False)  # info, warning, critical
    
    observed_value: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    limit_value: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    destination_type: Mapped[str] = mapped_column(String(50), nullable=False)  # console, webhook, slack, email
    destination_target: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="sent", nullable=False)  # sent, failed, retrying
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
