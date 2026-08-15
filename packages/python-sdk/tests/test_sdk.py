import pytest
import time
from unittest.mock import MagicMock
from pace import track, flush
from pace.privacy import sanitize_metadata
from pace.adapters.openai_adapter import OpenAIAdapter
from pace.adapters.anthropic_adapter import AnthropicAdapter
from pace.queue import ResilientTelemetryQueue

def test_privacy_sanitizer():
    raw_meta = {
        "environment": "staging",
        "user_id": 12345,
        "prompt": "Tell me a secret",
        "completion": "The secret is...",
        "api_key": "sk-12345678",
        "authorization": "Bearer token"
    }
    sanitized = sanitize_metadata(raw_meta)
    assert "environment" in sanitized
    assert "user_id" in sanitized
    assert "prompt" not in sanitized
    assert "completion" not in sanitized
    assert "api_key" not in sanitized
    assert "authorization" not in sanitized

def test_openai_adapter_parsing():
    adapter = OpenAIAdapter()
    
    # Mock OpenAI Completion Response
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 120
    mock_usage.completion_tokens = 45
    mock_usage.prompt_tokens_details = MagicMock(cached_tokens=30)
    mock_usage.completion_tokens_details = MagicMock(reasoning_tokens=15)

    mock_resp = MagicMock()
    mock_resp.id = "chatcmpl-test12345"
    mock_resp.model = "gpt-4o"
    mock_resp.usage = mock_usage

    telemetry = adapter.extract_telemetry(mock_resp, model_name="gpt-4o", latency_ms=250)
    assert telemetry["provider"] == "openai"
    assert telemetry["model"] == "gpt-4o"
    assert telemetry["input_tokens"] == 120
    assert telemetry["output_tokens"] == 45
    assert telemetry["cached_input_tokens"] == 30
    assert telemetry["reasoning_tokens"] == 15
    assert telemetry["status_code"] == 200

def test_anthropic_adapter_parsing():
    adapter = AnthropicAdapter()
    
    mock_usage = MagicMock()
    mock_usage.input_tokens = 200
    mock_usage.output_tokens = 80
    mock_usage.cache_read_input_tokens = 50

    mock_resp = MagicMock()
    mock_resp.id = "msg_test12345"
    mock_resp.model = "claude-3-5-sonnet-20241022"
    mock_resp.usage = mock_usage

    telemetry = adapter.extract_telemetry(mock_resp, model_name="claude-3-5-sonnet-20241022", latency_ms=350)
    assert telemetry["provider"] == "anthropic"
    assert telemetry["model"] == "claude-3-5-sonnet-20241022"
    assert telemetry["input_tokens"] == 200
    assert telemetry["output_tokens"] == 80
    assert telemetry["cached_input_tokens"] == 50
    assert telemetry["status_code"] == 200

def test_sdk_wrapper_resilience():
    # Mock OpenAI Client
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.id = "chatcmpl-999"
    mock_resp.model = "gpt-4o"
    mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, prompt_tokens_details=None, completion_tokens_details=None)
    mock_client.chat.completions.create.return_value = mock_resp

    tracked_client = track(
        mock_client,
        api_key="pace_testkey123",
        endpoint="http://localhost:9999", # Invalid port to simulate offline server
        metadata={"service": "test"}
    )

    # Call wrapped client - MUST NOT crash even if Pace server is offline!
    res = tracked_client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": "hello"}])
    assert res == mock_resp

def test_queue_overflow_behavior():
    # Test queue with maxsize=2
    tq = ResilientTelemetryQueue(endpoint="http://localhost:9999", api_key="pace_key", max_queue_size=2)
    tq.enqueue({"test": 1})
    tq.enqueue({"test": 2})
    tq.enqueue({"test": 3})  # Should overflow safely

    assert tq.dropped_events_count >= 1
    tq.close()

def test_queue_get_stats():
    tq = ResilientTelemetryQueue(endpoint="http://localhost:9999", api_key="pace_key", max_queue_size=10)
    tq.enqueue({"test": 1})
    stats = tq.get_stats()
    assert "queued" in stats
    assert "sent" in stats
    assert "dropped" in stats
    tq.close()

from pace import PaceClient

def test_pace_client_context_manager_and_tags():
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.id = "chatcmpl-ctx"
    mock_resp.model = "gpt-4o"
    mock_resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5, prompt_tokens_details=None, completion_tokens_details=None)
    mock_client.chat.completions.create.return_value = mock_resp

    with PaceClient(api_key="pace_ctx_key", endpoint="http://localhost:9999") as pace:
        tracked = pace.track(mock_client, tags={"env": "unit-test", "tier": "premium"})
        res = tracked.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": "hi"}])
        assert res == mock_resp

    # Verified context manager entered, tracked call executed, and flushed gracefully

from pace.attributes import AttributeBuilder

def test_attribute_builder():
    builder = AttributeBuilder({"initial": "val"})
    attrs = builder.set_environment("production").set_user_id("user_42").set_session_id("sess_99").build()
    assert attrs["initial"] == "val"
    assert attrs["environment"] == "production"
    assert attrs["user_id"] == "user_42"
    assert attrs["session_id"] == "sess_99"

def test_pace_client_shutdown_and_flush():
    client = PaceClient(api_key="pace_shutdown_key", endpoint="http://localhost:9999")
    client.flush(timeout=1.0)
    client.shutdown(timeout=1.0)

def test_pace_client_custom_headers():
    client = PaceClient(api_key="pace_key", endpoint="http://localhost:9999", custom_headers={"X-Custom-Header": "value"})
    assert client.custom_headers == {"X-Custom-Header": "value"}




