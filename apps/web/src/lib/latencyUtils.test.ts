import { describe, it } from 'node:test';
import assert from 'node:assert';
import { getLatencyTier } from './latencyUtils';

describe('getLatencyTier', () => {
  it('returns Fast for latency <= 800ms', () => {
    const res = getLatencyTier(350);
    assert.strictEqual(res.tier, 'Fast');
    assert.strictEqual(res.variant, 'success');
  });

  it('returns Moderate for latency between 801ms and 2000ms', () => {
    const res = getLatencyTier(1200);
    assert.strictEqual(res.tier, 'Moderate');
    assert.strictEqual(res.variant, 'warning');
  });

  it('returns Slow for latency > 2000ms', () => {
    const res = getLatencyTier(2500);
    assert.strictEqual(res.tier, 'Slow');
    assert.strictEqual(res.variant, 'error');
  });
});
