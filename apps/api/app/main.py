# ==============================================================================
# LOGIC OVERVIEW:
# This is the primary FastAPI entry point for Pace API.
# It initializes the application lifecycle (seeding pricing rates & demo users),
# mounts security middlewares (CORS, Rate Limiting, 1MB payload caps, security headers),
# starts/stops the background scheduler worker, and mounts all v1 API routers.
#
# CORE CODE HIGHLIGHTS:
# - lifespan(): Application lifecycle manager (seeds rates, boots background worker).
# - security_headers_and_limits_middleware(): Enforces 1MB payload cap & attaches telemetry headers.
# - app.include_router(...): Aggregates all modular route domains under /v1.
# ==============================================================================

import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.logging import setup_logging, logger
from app.models.models import User
from app.core.security import get_password_hash
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.api_keys import router as keys_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.pricing import router as pricing_router, seed_default_pricing_rates
from app.api.v1.budgets import router as budgets_router
from app.api.v1.exports import router as exports_router
from app.api.v1.system import router as system_router
from app.core.rate_limit import RateLimitMiddleware

setup_logging()

from app.worker.scheduler import BackgroundWorker

worker = BackgroundWorker()

# ------------------------------------------------------------------------------
# CORE CODE: Application Lifespan Handler
# LOGIC:
# 1. On startup: Opens an async DB session to seed default LLM pricing rates
#    (OpenAI, Anthropic) if they don't exist yet, and creates a demo user if DEMO_MODE=true.
# 2. Starts the background worker thread (evaluates budgets/anomalies every 60s).
# 3. On shutdown: Gracefully stops the background worker to avoid dangling async tasks.
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed default pricing rates and demo user if configured
    async with AsyncSessionLocal() as session:
        await seed_default_pricing_rates(session)
        if settings.DEMO_MODE:
            res = await session.execute(select(User).where(User.email == settings.SEEDED_USER_EMAIL))
            if not res.scalar_one_or_none():
                demo_user = User(
                    email=settings.SEEDED_USER_EMAIL,
                    password_hash=get_password_hash(settings.SEEDED_USER_PASSWORD),
                    full_name="Demo User"
                )
                session.add(demo_user)
                await session.commit()
                logger.info(f"Seeded demo user: {settings.SEEDED_USER_EMAIL}")
                
    if settings.WORKER_ENABLED:
        await worker.start()

    logger.info("Pace API Service initialized successfully.")
    yield
    if settings.WORKER_ENABLED:
        await worker.stop()
    logger.info("Shutting down Pace API Service.")

openapi_tags = [
    {"name": "System", "description": "Health diagnostics and Prometheus metrics endpoints"},
    {"name": "Authentication", "description": "User registration, login, and profile operations"},
    {"name": "Projects", "description": "Project workspace management and initial API key provisioning"},
    {"name": "API Keys", "description": "Project API key management, rotation, and revocation"},
    {"name": "Ingestion", "description": "Real-time telemetry usage event ingestion and deduplication"},
    {"name": "Analytics", "description": "LLM cost overview, timeseries, breakdown, and event explorer"},
    {"name": "Pricing Registry", "description": "LLM model token pricing rate configuration"},
    {"name": "Budgets", "description": "Cost threshold budgets and anomaly alert rules"},
    {"name": "Exports", "description": "Telemetry event CSV export generation"},
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Pace Open-Source LLM Cost Tracking & Optimization Infrastructure API",
    version=settings.VERSION,
    openapi_tags=openapi_tags,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

# ------------------------------------------------------------------------------
# CORE CODE: Security Headers, Latency Measurement & Payload Limit Middleware
# LOGIC:
# 1. Protection against DoS: Rejects request bodies > 1 MB with HTTP 413.
# 2. Telemetry & Auditing: Measures request duration with high-precision perf_counter
#    and adds X-Response-Time-Ms and X-Request-ID headers.
# 3. HTTP Security: Sets nosniff, DENY frame options, and XSS protection.
# ------------------------------------------------------------------------------
@app.middleware("http")
async def security_headers_and_limits_middleware(request: Request, call_next):
    start_t = time.perf_counter()
    # Enforce max body payload limit (1 MB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_048_576:
        return JSONResponse(
            status_code=413,
            content={"detail": "Payload too large. Maximum request body size is 1MB."}
        )

    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
    req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Global Exception Handler to ensure clean JSON responses without leaking internal stack trace
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please check server diagnostics."}
    )

# ------------------------------------------------------------------------------
# CORE CODE: Mounting Subsystem Routers
# LOGIC:
# Registers modular endpoints under /v1 (Auth, Projects, Keys, Ingestion,
# Analytics, Pricing, Budgets, Exports) plus root system diagnostics (/healthz, /metrics).
# ------------------------------------------------------------------------------
app.include_router(system_router)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(keys_router, prefix=settings.API_V1_STR)
app.include_router(ingest_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(pricing_router, prefix=settings.API_V1_STR)
app.include_router(budgets_router, prefix=settings.API_V1_STR)
app.include_router(exports_router, prefix=settings.API_V1_STR)
