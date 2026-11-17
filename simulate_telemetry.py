#!/usr/bin/env python3
"""
Simulate real-time LLM telemetry calls into Pace.
Run this script while viewing http://localhost:3000 to see live events arrive!
"""

import os
import time
import random
import json
try:
    import httpx
    def post_json(url, data, headers):
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=data, headers=headers)
            return r.status_code, r.text
except ImportError:
    try:
        import requests
        def post_json(url, data, headers):
            r = requests.post(url, json=data, headers=headers, timeout=10.0)
            return r.status_code, r.text
    except ImportError:
        import urllib.request
        def post_json(url, data, headers):
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=10.0) as resp:
                    return resp.getcode(), resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                return e.code, e.read().decode("utf-8")

API_ENDPOINT = os.getenv("PACE_API_ENDPOINT", "http://localhost:8000/v1/ingest/events")
API_KEY = os.getenv("PACE_API_KEY", "pace_lkPaI8cxPobhSAH7wwQbLWUro16FwdpIWu_7nICvs4g")

MODELS = [
    {"provider": "openai", "model": "gpt-4o", "min_in": 800, "max_in": 3000, "min_out": 200, "max_out": 800},
    {"provider": "openai", "model": "gpt-4o-mini", "min_in": 300, "max_in": 1200, "min_out": 50, "max_out": 300},
    {"provider": "anthropic", "model": "claude-3-5-sonnet", "min_in": 1000, "max_in": 4000, "min_out": 300, "max_out": 1200},
    {"provider": "anthropic", "model": "claude-3-5-haiku", "min_in": 200, "max_in": 800, "min_out": 50, "max_out": 250},
]

FEATURES = ["customer-support-bot", "document-summarizer", "code-assistant", "search-reranker"]

def generate_event(index):
    m = random.choice(MODELS)
    status = random.choices([200, 429, 500], weights=[90, 7, 3])[0]
    latency = random.randint(120, 1500) if status == 200 else random.randint(30, 200)

    return {
        "event_id": f"sim_evt_{int(time.time()*1000)}_{index}",
        "provider": m["provider"],
        "model": m["model"],
        "input_tokens": random.randint(m["min_in"], m["max_in"]),
        "output_tokens": random.randint(m["min_out"], m["max_out"]) if status == 200 else 0,
        "latency_ms": latency,
        "status_code": status,
        "metadata": {
            "environment": "production",
            "feature": random.choice(FEATURES)
        }
    }

def main():
    print("🚀 Pace Live Telemetry Simulator Started!")
    print(f"Sending telemetry events to {API_ENDPOINT}...")
    print("Open http://localhost:3000 -> Live Tail tab to watch events stream in real-time!\n")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        count = 1
        while True:
            batch = [generate_event(i) for i in range(random.randint(1, 3))]
            status_code, text = post_json(API_ENDPOINT, {"events": batch}, headers)

            if status_code in (200, 202):
                for evt in batch:
                    status_icon = "✅" if evt['status_code'] == 200 else ("🟡 429" if evt['status_code'] == 429 else "🔴 500")
                    print(f"[{count}] {status_icon} {evt['provider']}/{evt['model']} — {evt['input_tokens']}in / {evt['output_tokens']}out — {evt['latency_ms']}ms")
                    count += 1
            else:
                print(f"❌ Failed to ingest: {status_code} {text}")

            time.sleep(random.uniform(1.5, 3.0))
    except KeyboardInterrupt:
        print("\nStopped telemetry simulation.")

if __name__ == "__main__":
    main()
