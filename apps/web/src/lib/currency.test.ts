import { describe, it } from 'node:test';
import assert from 'node:assert';
import { formatINR, formatINRShort, formatUSD } from './currency';

describe('Currency Formatter Utilities', () => {
  it('formats INR properly', () => {
    const res = formatINR(1.0, 2);
    assert.strictEqual(res, '₹83.50');
  });

  it('formats USD properly', () => {
    const res = formatUSD(12.345, 2);
    assert.strictEqual(res, '$12.35');
  });

  it('handles null/undefined gracefully', () => {
    assert.strictEqual(formatUSD(null), '$0.00');
    assert.strictEqual(formatINRShort(undefined), '₹0.00');
  });
});
