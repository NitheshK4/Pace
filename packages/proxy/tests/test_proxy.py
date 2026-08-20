import pytest
import json
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport, Response
from pace_proxy.server import app, clean_headers, parse_sse_usage, telemetry_queue

@pytest.mark.asyncio
async def test_proxy_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "pace-proxy"
        assert data["loopback_only"] is True
        assert "allowlisted_providers" in data
        assert "server_time" in data
        assert "application/json" in res.headers.get("content-type", "")

def test_clean_headers():
    headers = {
        "Host": "api.openai.com",
        "Authorization": "Bearer sk-testkey123",
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }
    cleaned = clean_headers(headers)
    assert "Host" not in cleaned
    assert "Connection" not in cleaned
    assert "Authorization" in cleaned
    assert cleaned["Content-Type"] == "application/json"

def test_parse_sse_usage_openai():
    sse_text = (
        'data: {"id":"chatcmpl-1","model":"gpt-4o-2024-08-06","choices":[{"delta":{"content":"Hi"}}]}\n\n'
        'data: {"id":"chatcmpl-1","model":"gpt-4o-2024-08-06","choices":[],"usage":{"prompt_tokens":14,"completion_tokens":42}}\n\n'
        'data: [DONE]\n\n'
    )
    model, in_tok, out_tok = parse_sse_usage("openai", sse_text, {"model": "gpt-4o"})
    assert model == "gpt-4o-2024-08-06"
    assert in_tok == 14
    assert out_tok == 42

def test_parse_sse_usage_anthropic():
    sse_text = (
        'event: message_start\n'
        'data: {"type":"message_start","message":{"id":"msg_1","model":"claude-3-5-sonnet-20241022","usage":{"input_tokens":25,"output_tokens":1}}}\n\n'
        'event: message_delta\n'
        'data: {"type":"message_delta","usage":{"output_tokens":30}}\n\n'
    )
    model, in_tok, out_tok = parse_sse_usage("anthropic", sse_text, {"model": "claude-3-5-sonnet"})
    assert model == "claude-3-5-sonnet-20241022"
    assert in_tok == 25
    assert out_tok == 30

@pytest.mark.asyncio
async def test_unknown_provider_rejection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/v1/unknown_provider/do_something", json={"model": "test"})
        assert res.status_code == 400
        assert "Unknown or unsupported LLM provider" in res.json()["detail"]

@pytest.mark.asyncio
async def test_openai_forwarding_and_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        mock_client = AsyncMock()
        mock_client.request.return_value = Response(200, json={
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}
        }, headers={"Content-Type": "application/json"})

        with patch("pace_proxy.server.httpx.AsyncClient", return_value=mock_client):
            res = await ac.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]},
                headers={"Authorization": "Bearer sk-test-openai-key"}
            )
            assert res.status_code == 200
            assert "x-pace-proxy-latency-ms" in res.headers
            assert "x-pace-request-id" in res.headers
            assert "x-proxy-server-time" in res.headers
            assert mock_client.request.called
            kwargs = mock_client.request.call_args.kwargs
            assert kwargs["url"] == "https://api.openai.com/v1/chat/completions"
            assert kwargs["headers"]["authorization"] == "Bearer sk-test-openai-key"

@pytest.mark.asyncio
async def test_streaming_proxy_enqueues_accurate_telemetry():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        sse_payload = (
            'data: {"id":"chatcmpl-stream","model":"gpt-4o","choices":[{"delta":{"content":"World"}}]}\n\n'
            'data: {"usage":{"prompt_tokens":18,"completion_tokens":33}}\n\n'
            'data: [DONE]\n\n'
        ).encode("utf-8")

        async def mock_aiter_bytes():
            yield sse_payload

        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "text/event-stream"}
        mock_resp.aiter_bytes = mock_aiter_bytes
        mock_resp.aclose = AsyncMock()

        mock_client = AsyncMock()
        mock_client.send.return_value = mock_resp
        mock_client.aclose = AsyncMock()

        with patch("pace_proxy.server.httpx.AsyncClient", return_value=mock_client), \
             patch.object(telemetry_queue, "enqueue") as mock_enqueue:

            res = await ac.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "stream": True, "messages": [{"role": "user", "content": "Hello"}]}
            )
            assert res.status_code == 200
            content = await res.aread()
            assert b"World" in content

            assert mock_enqueue.called
            enqueued_event = mock_enqueue.call_args.args[0]
            assert enqueued_event["provider"] == "openai"
            assert enqueued_event["input_tokens"] == 18
            assert enqueued_event["output_tokens"] == 33

def test_proxy_upstream_timeout_config():
    from pace_proxy.server import UPSTREAM_TIMEOUT_SECONDS
    assert UPSTREAM_TIMEOUT_SECONDS > 0

@pytest.mark.asyncio
async def test_proxy_non_dict_json_payload():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        mock_client = AsyncMock()
        mock_client.request.return_value = Response(200, json={"status": "ok"}, headers={"Content-Type": "application/json"})
        with patch("pace_proxy.server.httpx.AsyncClient", return_value=mock_client):
            res = await ac.post("/v1/chat/completions", content=b"[1, 2, 3]", headers={"Content-Type": "application/json"})
            assert res.status_code == 200

from pace_proxy.server import parse_user_agent, validate_auth_header_format, sanitize_header_value

def test_parse_user_agent():
    assert parse_user_agent("") == "unknown"
    assert parse_user_agent(None) == "unknown"
    assert parse_user_agent("OpenAI/Python 1.12.0") == "openai-sdk"
    assert parse_user_agent("anthropic-python/0.8.0") == "anthropic-sdk"
    assert parse_user_agent("Pace-TS-SDK/0.1.0") == "pace-sdk"
    assert parse_user_agent("python-requests/2.31.0") == "python-http"
    assert parse_user_agent("node-fetch/3.0") == "js-runtime"
    assert parse_user_agent("CustomApp/1.0") == "generic-http"

def test_validate_auth_header_format():
    assert validate_auth_header_format(None) is False
    assert validate_auth_header_format("") is False
    assert validate_auth_header_format("Basic 12345") is False
    assert validate_auth_header_format("Bearer") is False
    assert validate_auth_header_format("Bearer secret_token_123") is True

def test_sanitize_header_value():
    assert sanitize_header_value(None) == ""
    assert sanitize_header_value("") == ""
    assert sanitize_header_value("Bearer key\r\n") == "Bearer key"
    assert sanitize_header_value("CleanValue") == "CleanValue"


