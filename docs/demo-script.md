# Pace — 3–5 Minute End-to-End Demo Walkthrough Script

This script demonstrates the end-to-end flow of **Pace**:

`sign up → create project → reveal one-time ingestion key → instrument OpenAI/Anthropic client → emit real usage event → see analytics overview & live tail → configure budget → receive deduplicated alert`

---

## Step 1: Self-Hosted Docker Startup (30 seconds)
1. In terminal, run:
   ```bash
   docker compose up --build -d
   ```
2. Verify all services reach healthy status (`http://localhost:3000` for Web Console, `http://localhost:8000/healthz` and `/readyz` for API).
3. Verify auth session using `GET /v1/auth/me`.

---

## Step 2: Sign Up & Project Creation (1 minute)
1. Open browser to `http://localhost:3000`.
2. Click **Create account** and register:
   - Email: `operator@company.com`
   - Password: `Password123!`
3. Click **New Project**:
   - Name: `Production Customer Support Bot`
4. The **Save Ingestion Key** modal opens:
   - Observe `pace_...` raw key displayed ONCE.
   - Click **Copy** to save the key to clipboard.

---

## Step 3: Instrument & Emit Real LLM Usage (1 minute)
1. Run Python sample script using the `pace` Python SDK:
   ```python
   from openai import OpenAI
   from pace import track

   client = track(
       OpenAI(api_key="sk-dummy-key"),
       api_key="pace_YOUR_COPIED_KEY",
       endpoint="http://localhost:8000",
       metadata={"service": "support-chat", "environment": "production"}
   )

   # Emit call
   response = client.chat.completions.create(
       model="gpt-4o",
       messages=[{"role": "user", "content": "Hello Pace!"}]
   )
   ```
2. Or run a direct curl test ingestion (using `Authorization: Bearer <pace_key>` header):
   ```bash
   curl -X POST http://localhost:8000/v1/ingest/events \
     -H "Authorization: Bearer pace_YOUR_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "event_id": "demo_evt_001",
       "provider": "openai",
       "model": "gpt-4o",
       "input_tokens": 1200,
       "output_tokens": 400,
       "latency_ms": 350,
       "status_code": 200,
       "metadata": {"environment": "demo"}
     }'
   ```

---

## Step 4: Explore Dashboard & Live Tail Feed (1 minute)
1. In the Web Console:
   - View **Overview Cards**: Spend total, Request count, Token mix, Latency percentiles.
   - View **Live Tail**: Observe event arriving in real-time over SSE stream!
   - View **Project Explorer**: Click on event to inspect sanitized telemetry details in the side drawer. Note zero content leakage!

---

## Step 5: Configure Budget & Trigger Deduplicated Alert (1 minute)
1. Navigate to **Budgets & Alerts**:
   - Click **New Budget Limit**.
   - Set Name: `Demo $5 Cap`, Amount: `$5.00`, Period: `Monthly`.
   - Set Webhook URL (optional).
2. The background worker evaluates usage.
3. Observe **Recorded Alert Deliveries**: Threshold breached alert recorded and dispatched to console/webhook!
4. Re-evaluate or send second event: observe alert is **deduplicated** and NOT spammed!

---

## Step 6: Export & Operations (30 seconds)
1. Go to **Project Explorer** -> Click **Export CSV** to download usage logs.
2. Go to **System & Security** -> View System Diagnostics & execute **Retention Purge**.
