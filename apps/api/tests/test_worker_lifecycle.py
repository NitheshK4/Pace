import pytest
import asyncio
from app.worker.scheduler import BackgroundWorker, DistributedLockManager

@pytest.mark.asyncio
async def test_worker_lifecycle_start_stop():
    worker = BackgroundWorker(interval_seconds=1)
    await worker.start()
    assert worker._running is True
    assert worker._task is not None
    
    # Wait briefly
    await asyncio.sleep(0.1)
    
    await worker.stop()
    assert worker._running is False
    assert worker._task is None

@pytest.mark.asyncio
async def test_worker_lock_contention(db_session):
    worker = BackgroundWorker(interval_seconds=1)

    # Manually hold lock
    async with DistributedLockManager.acquire_lock(db_session, DistributedLockManager.WORKER_EVALUATION_LOCK_ID) as acquired:
        assert acquired is True
        
        # Second attempt should be rejected/skipped
        async with DistributedLockManager.acquire_lock(db_session, DistributedLockManager.WORKER_EVALUATION_LOCK_ID) as second_acquired:
            assert second_acquired is False

    # Once released, lock can be acquired again
    async with DistributedLockManager.acquire_lock(db_session, DistributedLockManager.WORKER_EVALUATION_LOCK_ID) as third_acquired:
        assert third_acquired is True
