from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict

# --- Auth Schemas ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Project Schemas ---
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    def validate_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Project name cannot be empty or whitespace only.")
        return v.strip()

class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    owner_id: str
    role: str = "owner"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- API Key Schemas ---
class APIKeyCreate(BaseModel):
    name: str = Field(default="Default Key", min_length=1, max_length=255)
    expires_in_days: Optional[int] = None

class APIKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class APIKeyCreatedResponse(APIKeyResponse):
    raw_key: str = Field(description="Raw API key shown ONCE only on creation. Store it securely!")

# --- Usage Ingestion Schemas ---
class IngestEventRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=255, description="Unique idempotency token per project")
    time: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of event")
    provider: str = Field(min_length=1, max_length=50, description="LLM provider: openai, anthropic, azure, etc.")
    model: str = Field(min_length=1, max_length=100, description="Model identifier e.g. gpt-4o, claude-3-5-sonnet-20241022")
    endpoint: Optional[str] = Field(default=None, max_length=100)
    
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    
    cost_usd: Optional[Decimal] = Field(default=None, ge=0, description="Estimated cost in USD. Set to None if unknown")
    latency_ms: int = Field(default=0, ge=0)
    status_code: int = Field(default=200, ge=100, le=599)
    request_id: Optional[str] = Field(default=None, max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Safe key-value tags without prompts/completions/keys")

    @field_validator("metadata")
    def validate_metadata_privacy(cls, v):
        if not v:
            return v
        forbidden_keys = {"prompt", "completion", "messages", "content", "authorization", "api_key", "secret"}
        for k in v.keys():
            if k.lower() in forbidden_keys:
                raise ValueError(f"Forbidden sensitive key in metadata: {k}. Pace never persists prompt or secret content.")
        return v

class IngestBatchRequest(BaseModel):
    events: List[IngestEventRequest] = Field(min_length=1, max_length=500)

class IngestEventResponse(BaseModel):
    status: str = "accepted"
    accepted_count: int
    duplicate_count: int = 0
    rejected_count: int = 0

# --- Analytics Schemas ---
class OverviewResponse(BaseModel):
    total_spend_usd: Optional[float] = 0.0
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_tokens: int = 0
    total_reasoning_tokens: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    rate_limit_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    unknown_cost_events_count: int = 0
    spend_provenance: str = "estimated_via_pricing_registry"

class TimeseriesPoint(BaseModel):
    timestamp: str
    spend_usd: Optional[float] = 0.0
    requests: int = 0
    tokens: int = 0
    errors: int = 0

class TimeseriesResponse(BaseModel):
    granularity: str
    points: List[TimeseriesPoint]

class BreakdownItem(BaseModel):
    name: str
    spend_usd: Optional[float] = 0.0
    requests: int = 0
    tokens: int = 0
    percentage: float = 0.0

class BreakdownResponse(BaseModel):
    by_provider: List[BreakdownItem]
    by_model: List[BreakdownItem]

class UsageEventResponse(BaseModel):
    id: str
    event_id: str
    time: datetime
    provider: str
    model: str
    endpoint: Optional[str] = None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    cost_usd: Optional[float] = None
    cost_reason: Optional[str] = None
    latency_ms: int
    status_code: int
    request_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class EventsListResponse(BaseModel):
    events: List[UsageEventResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: int = 0

# --- Pricing Schemas ---
class PricingRateCreate(BaseModel):
    provider: str
    model: str
    input_cost_per_1k: Decimal = Field(default=Decimal(0))
    output_cost_per_1k: Decimal = Field(default=Decimal(0))
    cache_read_cost_per_1k: Decimal = Field(default=Decimal(0))
    reasoning_cost_per_1k: Decimal = Field(default=Decimal(0))
    source_url: Optional[str] = None

class PricingRateResponse(BaseModel):
    id: str
    provider: str
    model: str
    input_cost_per_1k: float
    output_cost_per_1k: float
    cache_read_cost_per_1k: float
    reasoning_cost_per_1k: float
    currency: str
    source_url: Optional[str] = None
    effective_from: datetime
    is_deprecated: bool

    model_config = ConfigDict(from_attributes=True)

