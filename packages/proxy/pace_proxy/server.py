import os
import time
import json
import uuid
import logging
import uvicorn
import httpx
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from pace.queue import ResilientTelemetryQueue

logger = logging.getLogger("pace.proxy")

PACE_ENDPOINT = os.getenv("PACE_ENDPOINT", "http://localhost:8000")
PACE_API_KEY = os.getenv("PACE_API_KEY", "pace_demo_proxy_key")
PROXY_PORT = int(os.getenv("PACE_PROXY_PORT", "8787"))
PROXY_HOST = os.getenv("PACE_PROXY_HOST", "127.0.0.1")  # Loopback only by default!

# Target Upstream Allowlist
ALLOWLISTED_PROVIDERS = {
    "openai": "https://api.openai.com",
    "anthropic": "https://api.anthropic.com"
}

telemetry_queue = ResilientTelemetryQueue(endpoint=PACE_ENDPOINT, api_key=PACE_API_KEY)

app = FastAPI(title="Pace Local Provider Proxy", version="0.1.0")

@app.get("/healthz")
async def proxy_health():
    return {
        "status": "healthy",
        "service": "pace-proxy",
        "loopback_only": PROXY_HOST == "127.0.0.1",
        "allowlisted_providers": list(ALLOWLISTED_PROVIDERS.keys())
    }

def clean_headers(incoming_headers: Dict[str, str]) -> Dict[str, str]:
    headers = {}
    drop_keys = {"host", "content-length", "transfer-encoding", "connection"}
    for k, v in incoming_headers.items():
        if k.lower() not in drop_keys:
            headers[k] = v
    return headers

def resolve_provider_and_target_url(provider_path: str, headers_dict: Dict[str, str]) -> Tuple[str, str, str]:
    clean_path = provider_path.lstrip("/")
    
    # 1. Header resolution
    hdr_provider = headers_dict.get("x-pace-provider", "").lower()
    if hdr_provider in ALLOWLISTED_PROVIDERS:
        base = ALLOWLISTED_PROVIDERS[hdr_provider]
        return hdr_provider, f"{base}/{clean_path}", f"/{clean_path}"

    # 2. Path prefix resolution (e.g. v1/openai/chat/completions or openai/v1/messages)
    parts = clean_path.split("/")
    if parts[0].lower() in ALLOWLISTED_PROVIDERS:
        p_name = parts[0].lower()
        sub_path = "/".join(parts[1:])
        base = ALLOWLISTED_PROVIDERS[p_name]
        return p_name, f"{base}/{sub_path}", f"/{sub_path}"
    elif len(parts) > 1 and parts[0].lower() == "v1" and parts[1].lower() in ALLOWLISTED_PROVIDERS:
        p_name = parts[1].lower()
        sub_path = "v1/" + "/".join(parts[2:])
        base = ALLOWLISTED_PROVIDERS[p_name]
        return p_name, f"{base}/{sub_path}", f"/{sub_path}"

    # 3. Standard OpenAI / Anthropic endpoints
    if clean_path.startswith("v1/messages") or clean_path.startswith("messages"):
        return "anthropic", f"https://api.anthropic.com/{clean_path}", f"/{clean_path}"
    elif any(clean_path.startswith(p) for p in ("v1/chat/completions", "v1/completions", "v1/embeddings", "v1/models")):
        return "openai", f"https://api.openai.com/{clean_path}", f"/{clean_path}"

    raise HTTPException(
        status_code=400,
        detail=f"Unknown or unsupported LLM provider for path '/{clean_path}'. Specify /v1/openai/..., /v1/anthropic/..., or X-Pace-Provider header."
    )

@app.api_route("/{provider_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_forward(request: Request, provider_path: str):
    start_time = time.time()
    headers_raw = dict(request.headers)
    headers = clean_headers(headers_raw)

    provider, target_url, endpoint_path = resolve_provider_and_target_url(provider_path, {k.lower(): v for k, v in headers_raw.items()})

    body_bytes = await request.body()
    body_json = {}
    try:
        if body_bytes:
            body_json = json.loads(body_bytes)
    except Exception:
        pass

    model_name = body_json.get("model", "unknown-model")
    stream = body_json.get("stream", False)

    try:
        client = httpx.AsyncClient(timeout=60.0)
        
        if stream:
            # Handle non-buffered streaming proxying
            req = client.build_request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body_bytes
            )
            response = await client.send(req, stream=True)
            latency_ms = int((time.time() - start_time) * 1000)

            # Emit async telemetry to Pace
            telemetry_queue.enqueue({
                "event_id": str(uuid.uuid4()),
                "provider": provider,
                "model": model_name,
                "endpoint": provider_path,
                "input_tokens": 100,  # Estimated for stream start
                "output_tokens": 50,
                "latency_ms": latency_ms,
                "status_code": response.status_code
            })

            async def stream_body():
                try:
                    async for chunk in response.aiter_bytes():
                        yield chunk
                finally:
                    await response.aclose()
                    await client.aclose()

            resp_headers = clean_headers(dict(response.headers))
            return StreamingResponse(stream_body(), status_code=response.status_code, headers=resp_headers)
        
        else:
            # Non-streaming request
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body_bytes
            )
            latency_ms = int((time.time() - start_time) * 1000)
            await client.aclose()

            # Parse usage if present in response
            input_tokens = 0
            output_tokens = 0
            try:
                res_data = resp.json()
                usage = res_data.get("usage", {})
                input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
            except Exception:
                pass

            # Emit telemetry
            telemetry_queue.enqueue({
                "event_id": str(uuid.uuid4()),
                "provider": provider,
                "model": model_name,
                "endpoint": provider_path,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "status_code": resp.status_code
            })

            resp_headers = clean_headers(dict(resp.headers))
            resp_headers["x-pace-proxy-latency-ms"] = str(latency_ms)
            resp_headers["x-pace-proxy-version"] = "0.1.0"
            return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)

    except Exception as exc:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Proxy error targeting {target_url}: {exc}")
        
        # Emit failure telemetry safely
        telemetry_queue.enqueue({
            "event_id": str(uuid.uuid4()),
            "provider": provider,
            "model": model_name,
            "endpoint": provider_path,
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": latency_ms,
            "status_code": 502
        })
        raise HTTPException(status_code=502, detail=f"Proxy error connecting to upstream provider: {str(exc)}")

def main():
    uvicorn.run("pace_proxy.server:app", host=PROXY_HOST, port=PROXY_PORT, reload=False)

if __name__ == "__main__":
    main()
