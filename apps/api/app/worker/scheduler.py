import asyncio
import logging
from contextlib import asynccontextmanager
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.models import Budget, Project
from app.services.budget_service import BudgetEvaluationService
from app.services.anomaly_service import AnomalyDetectorService
from app.services.alert_service import AlertDeliveryService

logger = logging.getLogger("pace.worker")

class DistributedLockManager:
    WORKER_EVALUATION_LOCK_ID = 884729103
    _active_locks = set()

    @classmethod
    @asynccontextmanager
    async def acquire_lock(cls, db: AsyncSession, lock_id: int):
        dialect = db.bind.dialect.name if db.bind else ""
        acquired = False

        if dialect == "postgresql":
            try:
                res = await db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id})
                acquired = bool(res.scalar())
            except Exception as e:
                logger.warning(f"PostgreSQL advisory lock attempt failed: {e}. Defaulting to single-execution.")
                acquired = True
        else:
            if lock_id not in cls._active_locks:
                cls._active_locks.add(lock_id)
                acquired = True

        try:
            yield acquired
        finally:
            if acquired:
                if dialect == "postgresql":
                    try:
                        await db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id})
                    except Exception:
                        pass
                else:
                    if lock_id in cls._active_locks:
                        cls._active_locks.remove(lock_id)

class BackgroundWorker:
    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self._running = False
        self._task = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Pace background worker started (interval: {self.interval}s).")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Pace background worker stopped cleanly.")

    async def _run_loop(self):
        try:
            while self._running:
                try:
                    await self.run_evaluation_cycle()
                except Exception as e:
                    logger.error(f"Error during worker evaluation cycle: {e}")
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            logger.debug("Worker loop cancelled.")
            raise

    async def run_evaluation_cycle(self):
        async with AsyncSessionLocal() as db:
            async with DistributedLockManager.acquire_lock(db, DistributedLockManager.WORKER_EVALUATION_LOCK_ID) as acquired:
                if not acquired:
                    logger.info("Another worker replica is executing evaluation cycle. Skipping cycle.")
                    return

                # 1. Process Outbox Retries
                try:
                    await AlertDeliveryService.process_outbox_retries(db)
                except Exception as e:
                    logger.error(f"Error processing outbox retries: {e}")

                # 2. Evaluate Budgets
                b_stmt = select(Budget).where(Budget.is_active == True)
                b_res = await db.execute(b_stmt)
                budgets = b_res.scalars().all()

                for b in budgets:
                    try:
                        await BudgetEvaluationService.evaluate_budget(db, b)
                    except Exception as e:
                        logger.error(f"Error evaluating budget {b.id}: {e}")

                # 3. Evaluate Anomalies
                p_stmt = select(Project.id)
                p_res = await db.execute(p_stmt)
                project_ids = p_res.scalars().all()

                for pid in project_ids:
                    try:
                        anomalies = await AnomalyDetectorService.detect_anomalies(db, pid)
                        for a in anomalies:
                            logger.warning(f"[ANOMALY DETECTED] Project {pid}: {a['explanation']}")
                    except Exception as e:
                        logger.error(f"Error detecting anomalies for project {pid}: {e}")
