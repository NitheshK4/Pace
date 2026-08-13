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

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
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

# Security Headers & Payload Limit Middleware
@app.middleware("http")
async def security_headers_and_limits_middleware(request: Request, call_next):
    # Enforce max body payload limit (1 MB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_048_576:
        return JSONResponse(
            status_code=413,
            content={"detail": "Payload too large. Maximum request body size is 1MB."}
        )

    response = await call_next(request)
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

# Include Routers
app.include_router(system_router)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(keys_router, prefix=settings.API_V1_STR)
app.include_router(ingest_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(pricing_router, prefix=settings.API_V1_STR)
app.include_router(budgets_router, prefix=settings.API_V1_STR)
app.include_router(exports_router, prefix=settings.API_V1_STR)
