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

  public getFlushIntervalMs(): number {
    return this.queue.getFlushIntervalMs();
  }

  public getMaxRetries(): number {
    return this.queue.getMaxRetries();
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
