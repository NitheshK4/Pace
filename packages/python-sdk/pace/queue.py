import time
import queue
import threading
import uuid
import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger("pace.sdk")

class ResilientTelemetryQueue:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        max_queue_size: int = 1000,
        batch_size: int = 20,
        flush_interval_seconds: float = 2.0,
        http_timeout_seconds: float = 3.0
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.flush_interval = flush_interval_seconds
        self.timeout = http_timeout_seconds
        
        self._queue = queue.Queue(maxsize=max_queue_size)
        self.dropped_events_count = 0
        self.sent_events_count = 0
        self._shutdown_event = threading.Event()
        
        # Background sender thread
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def validate_event(self, event_data: Dict[str, Any]) -> bool:
        if not isinstance(event_data, dict):
            return False
        provider = event_data.get("provider")
        model = event_data.get("model")
        if not provider or not isinstance(provider, str) or not provider.strip():
            return False
        if not model or not isinstance(model, str) or not model.strip():
            return False
        return True

    def enqueue(self, event_data: Dict[str, Any]):
        if not self.validate_event(event_data):
            self.dropped_events_count += 1
            logger.warning(f"[Pace Telemetry Invalid] Event missing required provider or model: {event_data}")
            return

        if not event_data.get("event_id"):
            event_data["event_id"] = str(uuid.uuid4())
            
        try:
            self._queue.put_nowait(event_data)
        except queue.Full:
            self.dropped_events_count += 1
            logger.warning(
                f"[Pace Telemetry Drop] Queue full ({self.max_queue_size}). "
                f"Total dropped: {self.dropped_events_count}"
            )

    def _worker_loop(self):
        try:
            client = httpx.Client(timeout=self.timeout)
            while not self._shutdown_event.is_set():
                batch = []
                start_time = time.time()
                
                while len(batch) < self.batch_size and (time.time() - start_time) < self.flush_interval:
                    try:
                        item = self._queue.get(timeout=0.2)
                        batch.append(item)
                    except queue.Empty:
                        if self._shutdown_event.is_set():
                            break

                if batch:
                    self._send_batch_with_retry(client, batch)
        except Exception as exc:
            logger.error(f"[Pace Worker Thread Error] Worker loop caught exception: {exc}")

    def _send_batch_with_retry(self, client: httpx.Client, batch: list):
        url = f"{self.endpoint}/v1/ingest/events"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        max_attempts = 3
        backoff = 0.5

        for attempt in range(max_attempts):
            try:
                resp = client.post(url, json={"events": batch}, headers=headers)
                if resp.status_code == 200:
                    self.sent_events_count += len(batch)
                    return
                elif resp.status_code in (401, 403, 422):
                    logger.error(f"[Pace Telemetry Rejected] HTTP {resp.status_code}: {resp.text}")
                    return  # Non-retryable user error
            except Exception as e:
                logger.warning(f"[Pace Telemetry Warning] Attempt {attempt+1}/{max_attempts} failed: {e}")
                
            time.sleep(backoff)
            backoff *= 2.0

        # If all retries fail, increment local drop count safely without crashing user app
        self.dropped_events_count += len(batch)
        logger.error(
            f"[Pace Telemetry Failure] Dropped batch of {len(batch)} events after {max_attempts} attempts. "
            f"Pace server might be unreachable."
        )

    def get_stats(self) -> Dict[str, int]:
        return {
            "queued": self._queue.qsize(),
            "sent": self.sent_events_count,
            "dropped": self.dropped_events_count
        }

    def flush(self, timeout: float = 5.0):
        start = time.time()
        while not self._queue.empty() and (time.time() - start) < timeout:
            time.sleep(0.1)

    def close(self):
        self.flush()
        self._shutdown_event.set()
        self._thread.join(timeout=2.0)

