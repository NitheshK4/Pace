export interface TelemetryEvent {
  event_id?: string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens?: number;
  reasoning_tokens?: number;
  latency_ms: number;
  status_code?: number;
  metadata?: Record<string, unknown>;
}

export interface PaceOptions {
  apiKey: string;
  endpoint?: string;
  batchSize?: number;
  flushIntervalMs?: number;
  maxQueueSize?: number;
  onError?: (err: Error) => void;
}

export class ResilientTelemetryQueue {
  private queue: TelemetryEvent[] = [];
  private apiKey: string;
  private endpoint: string;
  private batchSize: number;
  private flushIntervalMs: number;
  private maxQueueSize: number;
  private timer: ReturnType<typeof setInterval> | null = null;
  private isFlushing = false;

  private onError?: (err: Error) => void;

  constructor(options: PaceOptions) {
    this.apiKey = options.apiKey;
    this.endpoint = (options.endpoint || 'http://localhost:8000').replace(/\/$/, '');
    this.batchSize = options.batchSize || 20;
    this.flushIntervalMs = options.flushIntervalMs || 2000;
    this.maxQueueSize = Math.max(1, options.maxQueueSize || 1000);
    this.onError = options.onError;

    this.startPeriodicFlush();
  }

  public validateEvent(event: Partial<TelemetryEvent>): boolean {
    if (!event || typeof event !== 'object') return false;
    if (!event.provider || typeof event.provider !== 'string' || !event.provider.trim()) return false;
    if (!event.model || typeof event.model !== 'string' || !event.model.trim()) return false;
    return true;
  }

  public enqueue(event: TelemetryEvent): void {
    if (!this.validateEvent(event)) {
      return; // Silently drop invalid events
    }

    if (this.queue.length >= this.maxQueueSize) {
      // Drop oldest event when queue is full to remain non-blocking
      this.queue.shift();
    }
    const fullEvent: TelemetryEvent = {
      event_id: event.event_id || `evt_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      status_code: event.status_code ?? 200,
      cached_input_tokens: event.cached_input_tokens ?? 0,
      reasoning_tokens: event.reasoning_tokens ?? 0,
      ...event,
    };
    this.queue.push(fullEvent);

    if (this.queue.length >= this.batchSize) {
      void this.flush();
    }
  }

  public async flush(): Promise<void> {
    if (this.isFlushing || this.queue.length === 0) return;
    this.isFlushing = true;

    const batch = this.queue.splice(0, this.batchSize);
    const maxAttempts = 3;
    let backoffMs = 100;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await fetch(`${this.endpoint}/v1/ingest/events`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.apiKey}`,
          },
          body: JSON.stringify({ events: batch }),
        });

        if (response.ok || (response.status >= 400 && response.status < 500)) {
          // Success or client error (non-retryable)
          this.isFlushing = false;
          return;
        }
      } catch (err) {
        if (this.onError && err instanceof Error) {
          this.onError(err);
        }
      }

      if (attempt < maxAttempts) {
        await new Promise((resolve) => setTimeout(resolve, backoffMs));
        backoffMs *= 2;
      }
    }

    this.isFlushing = false;
  }

  public getStats(): { pendingEvents: number } {
    return { pendingEvents: this.queue.length };
  }

  public clear(): void {
    this.queue = [];
  }

  public stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  private startPeriodicFlush(): void {
    this.timer = setInterval(() => {
      void this.flush();
    }, this.flushIntervalMs);
  }
}
