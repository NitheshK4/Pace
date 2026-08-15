# @pace/sdk — Pace TypeScript SDK

Official TypeScript SDK for Pace LLM Observability.

## Installation

```bash
npm install @pace/sdk
```

## Quick Start

```typescript
import { PaceClient } from '@pace/sdk';

const pace = new PaceClient({
  apiKey: 'pace_YOUR_INGESTION_KEY',
  endpoint: 'http://localhost:8000'
});

// Record telemetry event in background
pace.record({
  provider: 'openai',
  model: 'gpt-4o',
  input_tokens: 1200,
  output_tokens: 400,
  latency_ms: 350
});

// Inspect pending queue count
console.log('Pending events:', pace.getQueueSize());

// Manually flush pending events
await pace.flush();
```
