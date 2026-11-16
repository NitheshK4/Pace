# ==============================================================================
# LOGIC OVERVIEW:
# Asynchronous Background Worker and Distributed Lock Manager.
# Runs an evaluation cycle every 60 seconds to process pending outbox alert retries,
# evaluate budget thresholds, and detect cost anomalies across all active projects.
#
# CORE CODE HIGHLIGHTS:
# - DistributedLockManager: Uses PostgreSQL advisory locks (pg_try_advisory_lock)
#   so that when scaling Pace across multiple container replicas, only ONE worker
#   executes the evaluation cycle at a time (prevents duplicate alert runs).
# - BackgroundWorker: Asyncio task loop that manages graceful startup, evaluation execution,
#   and cancellation on API shutdown.
# - run_evaluation_cycle(): The 3-phase periodic workflow:
#   1. Process pending outbox retries (exponential backoff).
#   2. Evaluate active budgets (BudgetEvaluationService).
#   3. Detect sudden cost/rate-limit anomalies (AnomalyDetectorService).
# ==============================================================================

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

# ------------------------------------------------------------------------------
# CORE CODE: Distributed Advisory Lock Manager
# LOGIC:
# Coordinates multiple horizontal API replicas.
# In PostgreSQL, uses pg_try_advisory_lock(lock_id). If another replica already
# holds the lock, this node gracefully skips the cycle without blocking.
# ------------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # CORE CODE: Worker Periodic Evaluation Cycle
    # LOGIC:
    # 1. Obtains distributed lock (ensures single-replica execution).
    # 2. Retries transient webhook alert deliveries from outbox.
    # 3. Evaluates spend for all active budgets against thresholds (50%, 80%, 100%, 120%).
    # 4. Runs anomaly detection scans for cost spikes (>3x baseline) and 429 rate limit storms.
    # --------------------------------------------------------------------------
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
