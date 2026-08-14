import os
import time
import functools
import logging
from typing import Any, Dict, Optional
from pace.queue import ResilientTelemetryQueue
from pace.privacy import sanitize_metadata
from pace.adapters.openai_adapter import OpenAIAdapter
from pace.adapters.anthropic_adapter import AnthropicAdapter

logger = logging.getLogger("pace.sdk")

_global_queue: Optional[ResilientTelemetryQueue] = None

def get_telemetry_queue(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None
) -> ResilientTelemetryQueue:
    global _global_queue
    if _global_queue is None:
        target_endpoint = endpoint or os.getenv("PACE_ENDPOINT", "http://localhost:8000")
        target_key = api_key or os.getenv("PACE_API_KEY", "")
        _global_queue = ResilientTelemetryQueue(endpoint=target_endpoint, api_key=target_key)
    return _global_queue

def flush(timeout: float = 5.0):
    global _global_queue
    if _global_queue:
        _global_queue.flush(timeout=timeout)

def track(
    client: Any,
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    enabled: bool = True
) -> Any:
    if not enabled:
        return client

    queue_inst = get_telemetry_queue(endpoint, api_key)
    sanitized_meta = sanitize_metadata(metadata)

    # Detect OpenAI client (.chat.completions)
    if hasattr(client, "chat") and hasattr(client.chat, "completions"):
        _wrap_openai_client(client, queue_inst, sanitized_meta)

    # Detect Anthropic client (.messages)
    elif hasattr(client, "messages"):
        _wrap_anthropic_client(client, queue_inst, sanitized_meta)

    return client

def _wrap_openai_client(client: Any, telemetry_queue: ResilientTelemetryQueue, base_metadata: Dict[str, Any]):
    original_create = client.chat.completions.create
    adapter = OpenAIAdapter()

    @functools.wraps(original_create)
    def sync_wrapper(*args, **kwargs):
        model_name = kwargs.get("model", "unknown-model")
        start_time = time.time()
        try:
            res = original_create(*args, **kwargs)
            latency_ms = int((time.time() - start_time) * 1000)
            telemetry = adapter.extract_telemetry(res, model_name=model_name, latency_ms=latency_ms, is_error=False)
            if base_metadata:
                telemetry["metadata"] = base_metadata
            telemetry_queue.enqueue(telemetry)
            return res
        except Exception as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            telemetry = adapter.extract_telemetry(exc, model_name=model_name, latency_ms=latency_ms, is_error=True)
            if base_metadata:
                telemetry["metadata"] = base_metadata
            telemetry_queue.enqueue(telemetry)
            raise exc

    client.chat.completions.create = sync_wrapper

def _wrap_anthropic_client(client: Any, telemetry_queue: ResilientTelemetryQueue, base_metadata: Dict[str, Any]):
    original_create = client.messages.create
    adapter = AnthropicAdapter()

    @functools.wraps(original_create)
    def sync_wrapper(*args, **kwargs):
        model_name = kwargs.get("model", "unknown-model")
        start_time = time.time()
        try:
            res = original_create(*args, **kwargs)
            latency_ms = int((time.time() - start_time) * 1000)
            telemetry = adapter.extract_telemetry(res, model_name=model_name, latency_ms=latency_ms, is_error=False)
            if base_metadata:
                telemetry["metadata"] = base_metadata
            telemetry_queue.enqueue(telemetry)
            return res
        except Exception as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            telemetry = adapter.extract_telemetry(exc, model_name=model_name, latency_ms=latency_ms, is_error=True)
            if base_metadata:
                telemetry["metadata"] = base_metadata
            telemetry_queue.enqueue(telemetry)
            raise exc

class PaceClient:
    """
    Context-managed Pace telemetry client for explicit tracking and auto-flushing.
    Usage:
        with PaceClient(api_key="pace_key", endpoint="http://localhost:8000") as pace:
            client = pace.track(openai_client)
            client.chat.completions.create(...)
    """
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        self.api_key = api_key
        self.endpoint = endpoint
        self.queue = get_telemetry_queue(endpoint, api_key)

    def track(
        self,
        client: Any,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        enabled: bool = True
    ) -> Any:
        combined_meta = dict(metadata or {})
        if tags:
            combined_meta["tags"] = tags
        return track(
            client,
            api_key=self.api_key,
            endpoint=self.endpoint,
            metadata=combined_meta,
            enabled=enabled
        )

    def flush(self, timeout: float = 5.0):
        if self.queue:
            self.queue.flush(timeout=timeout)

    def shutdown(self, timeout: float = 5.0):
        if self.queue:
            self.queue.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()

