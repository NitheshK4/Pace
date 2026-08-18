import assert from 'node:assert';
import { test, describe } from 'node:test';
import { PaceClient, ResilientTelemetryQueue } from './index.js';

describe('Pace TypeScript SDK', () => {
  test('initializes client and queues telemetry without throwing', () => {
    const client = new PaceClient({
      apiKey: 'pace_test_key_12345',
      endpoint: 'http://localhost:8000',
      flushIntervalMs: 10000,
    });

    client.record({
      provider: 'openai',
      model: 'gpt-4o',
      input_tokens: 100,
      output_tokens: 50,
      latency_ms: 120,
    });

    const stats = client.getStats();
    assert.strictEqual(stats.pendingEvents, 1);
    client.shutdown();
  });

  test('drops oldest items when queue exceeds max size', () => {
    const queue = new ResilientTelemetryQueue({
      apiKey: 'pace_test_key_12345',
      maxQueueSize: 2,
      flushIntervalMs: 10000,
    });

    queue.enqueue({ provider: 'openai', model: 'gpt-4o', input_tokens: 10, output_tokens: 5, latency_ms: 100 });
    queue.enqueue({ provider: 'openai', model: 'gpt-4o', input_tokens: 20, output_tokens: 5, latency_ms: 100 });
    queue.enqueue({ provider: 'openai', model: 'gpt-4o', input_tokens: 30, output_tokens: 5, latency_ms: 100 });

    assert.strictEqual(queue.getStats().pendingEvents, 2);
    queue.stop();
  });

  test('flushes queue gracefully on network failure without throwing errors', async () => {
    const client = new PaceClient({
      apiKey: 'pace_invalid_key',
      endpoint: 'http://127.0.0.1:9999', // Non-existent port
      flushIntervalMs: 10000,
    });

    client.record({
      provider: 'anthropic',
      model: 'claude-3-5-sonnet',
      input_tokens: 500,
      output_tokens: 200,
      latency_ms: 350,
    });

    assert.strictEqual(client.getStats().pendingEvents, 1);
    
    // Should swallow network exception cleanly and empty queue
    await assert.doesNotReject(async () => {
      await client.flush();
    });

    assert.strictEqual(client.getStats().pendingEvents, 0);
    client.shutdown();
  });

  test('returns queue size via getQueueSize method', () => {
    const client = new PaceClient({
      apiKey: 'pace_test_key_12345',
      endpoint: 'http://localhost:8000',
      flushIntervalMs: 10000,
    });
    assert.strictEqual(client.getQueueSize(), 0);
    client.record({ provider: 'openai', model: 'gpt-4o', input_tokens: 10, output_tokens: 5, latency_ms: 100 });
    assert.strictEqual(client.getQueueSize(), 1);
    client.shutdown();
  });

  test('throws TypeError on empty endpoint string', () => {
    assert.throws(() => {
      new PaceClient({
        apiKey: 'pace_key',
        endpoint: '  ',
      });
    }, /Pace endpoint must be a non-empty string URL/);
  });

  test('clears pending telemetry events on clear()', () => {
    const client = new PaceClient({
      apiKey: 'pace_test_key_12345',
      flushIntervalMs: 10000,
    });
    client.record({ provider: 'openai', model: 'gpt-4o', input_tokens: 10, output_tokens: 5, latency_ms: 100 });
    assert.strictEqual(client.getQueueSize(), 1);
    client.clear();
    assert.strictEqual(client.getQueueSize(), 0);
    client.shutdown();
  });

  test('returns configured flush interval in ms via getFlushIntervalMs', () => {
    const client = new PaceClient({
      apiKey: 'pace_test_key_12345',
      flushIntervalMs: 5000,
    });
    assert.strictEqual(client.getFlushIntervalMs(), 5000);
    client.shutdown();
  });

  test('returns configured max retries via getMaxRetries', () => {
    const defaultClient = new PaceClient({ apiKey: 'pace_test' });
    assert.strictEqual(defaultClient.getMaxRetries(), 3);
    defaultClient.shutdown();

    const customClient = new PaceClient({ apiKey: 'pace_test', maxRetries: 5 });
    assert.strictEqual(customClient.getMaxRetries(), 5);
    customClient.shutdown();
  });
});
