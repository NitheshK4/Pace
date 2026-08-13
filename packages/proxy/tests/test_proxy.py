import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport, Response
from pace_proxy.server import app, clean_headers

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
            assert mock_client.request.called
            kwargs = mock_client.request.call_args.kwargs
            assert kwargs["url"] == "https://api.openai.com/v1/chat/completions"
            assert kwargs["headers"]["authorization"] == "Bearer sk-test-openai-key"

@pytest.mark.asyncio
async def test_anthropic_forwarding_and_headers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        mock_client = AsyncMock()
        mock_client.request.return_value = Response(200, json={
            "id": "msg_123",
            "type": "message",
            "usage": {"input_tokens": 15, "output_tokens": 8}
        }, headers={"Content-Type": "application/json"})

        with patch("pace_proxy.server.httpx.AsyncClient", return_value=mock_client):
            res = await ac.post(
                "/v1/messages",
                json={"model": "claude-3-5-sonnet-20241022", "messages": [{"role": "user", "content": "hi"}]},
                headers={"x-api-key": "sk-ant-testkey", "anthropic-version": "2023-06-01"}
            )
            assert res.status_code == 200
            assert mock_client.request.called
            kwargs = mock_client.request.call_args.kwargs
            assert kwargs["url"] == "https://api.anthropic.com/v1/messages"
            assert kwargs["headers"]["x-api-key"] == "sk-ant-testkey"
            assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
