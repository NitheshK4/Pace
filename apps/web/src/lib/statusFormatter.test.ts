import { describe, it } from 'node:test';
import assert from 'node:assert';
import { formatStatusLabel } from './statusFormatter';

describe('Status Formatter Utilities', () => {
  it('formats 200 series status codes as success', () => {
    const res = formatStatusLabel(200);
    assert.strictEqual(res.label, '200 OK');
    assert.strictEqual(res.variant, 'success');
  });

  it('formats 400 series status codes as client errors', () => {
    const res = formatStatusLabel(429);
    assert.strictEqual(res.label, '429 Client Error');
    assert.strictEqual(res.variant, 'warning');
  });

  it('formats 500 series status codes as server errors', () => {
    const res = formatStatusLabel(502);
    assert.strictEqual(res.label, '502 Server Error');
    assert.strictEqual(res.variant, 'error');
  });
});
