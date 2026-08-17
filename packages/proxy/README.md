# Pace Local Provider Proxy (`pace-proxy`)

The **Pace Local Provider Proxy** acts as a lightweight, zero-latency local sidecar that forwards LLM API requests directly to upstream providers (OpenAI, Anthropic) while asynchronously queuing usage telemetry to your Pace ingestion backend.

## Environment Variables & Configuration

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PACE_ENDPOINT` | The URL of your Pace API server | `http://localhost:8000` |
| `PACE_API_KEY` | Ingestion API key for telemetry submission | `pace_demo_proxy_key` |
| `PACE_PROXY_PORT` | Local port for proxy listener | `8787` |
| `PACE_PROXY_HOST` | Local host binding (`127.0.0.1` for loopback security) | `127.0.0.1` |
| `PACE_PROXY_UPSTREAM_TIMEOUT` | Upstream request timeout in seconds | `60.0` |

## Supported Providers

- **OpenAI**: `https://api.openai.com`
- **Anthropic**: `https://api.anthropic.com`

## Running the Proxy

```bash
python3 -m pace_proxy.server
```
