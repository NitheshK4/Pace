# ==============================================================================
# LOGIC OVERVIEW:
# Async database engine, connection pool, and session lifecycle manager for Pace.
#
# CORE CODE HIGHLIGHTS:
# - create_async_engine(): Sets up non-blocking async DB pool (asyncpg for PostgreSQL,
#   aiosqlite for local dev/testing) with pool_pre_ping for connection health recovery.
# - get_db(): FastAPI dependency managing transaction commit, rollback on error, and session cleanup.
# ==============================================================================

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Adjust sqlite database url for async engine if sqlite is used
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite://"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

# ------------------------------------------------------------------------------
# CORE CODE: Async Database Engine & Session Maker
# LOGIC:
# Configures SQLAlchemy 2.0 async engine with pool_pre_ping=True to guard against
# dropped TCP connections in production database clusters.
# ------------------------------------------------------------------------------
engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True if not db_url.startswith("sqlite") else False
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

# ------------------------------------------------------------------------------
# CORE CODE: Database Session Dependency (get_db)
# LOGIC:
# Yields an async session to FastAPI route handlers.
# Automatically commits on success, rolls back on uncaught exception, and closes session.
# ------------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
