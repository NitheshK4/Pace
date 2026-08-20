import { ResilientTelemetryQueue, TelemetryEvent, PaceOptions } from './queue.js';

export { ResilientTelemetryQueue, TelemetryEvent, PaceOptions };

export class PaceClient {
  private queue: ResilientTelemetryQueue;

  constructor(options: PaceOptions) {
    this.queue = new ResilientTelemetryQueue(options);
  }

  public record(event: TelemetryEvent): void {
    this.queue.enqueue(event);
  }

  public async flush(): Promise<void> {
    await this.queue.flush();
  }

  public getStats(): { pendingEvents: number } {
    return this.queue.getStats();
  }

  public getQueueSize(): number {
    return this.queue.getStats().pendingEvents;
  }

  public isQueueEmpty(): boolean {
    return this.getQueueSize() === 0;
  }

  public isConfigured(): boolean {
    return Boolean(this.queue);
  }

  public getFlushIntervalMs(): number {
    return this.queue.getFlushIntervalMs();
  }

  public getMaxRetries(): number {
    return this.queue.getMaxRetries();
  }

  public getCustomHeaders(): Record<string, string> {
    return this.queue.getCustomHeaders();
  }

  public clear(): void {
    this.queue.clear();
  }

  public shutdown(): void {
    this.queue.stop();
  }
}

export function createPaceClient(options: PaceOptions): PaceClient {
  return new PaceClient(options);
}

export function maskApiKey(apiKey: string, visibleChars = 4): string {
  if (!apiKey || typeof apiKey !== 'string') return '';
  if (apiKey.length <= visibleChars) return '*'.repeat(apiKey.length);
  return apiKey.slice(0, visibleChars) + '*'.repeat(apiKey.length - visibleChars);
}
