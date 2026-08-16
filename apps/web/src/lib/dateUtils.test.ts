import assert from 'node:assert';
import { test, describe } from 'node:test';
import { formatRelativeTime, formatShortTimestamp } from './dateUtils';

describe('Web Date Utilities', () => {
  test('formats relative time correctly for various deltas', () => {
    const base = new Date('2026-08-16T12:00:00Z');

    assert.strictEqual(formatRelativeTime('2026-08-16T11:59:58Z', base), 'just now');
    assert.strictEqual(formatRelativeTime('2026-08-16T11:59:30Z', base), '30s ago');
    assert.strictEqual(formatRelativeTime('2026-08-16T11:45:00Z', base), '15m ago');
    assert.strictEqual(formatRelativeTime('2026-08-16T08:00:00Z', base), '4h ago');
    assert.strictEqual(formatRelativeTime('2026-08-14T12:00:00Z', base), '2d ago');
    assert.strictEqual(formatRelativeTime('invalid-date-string'), 'Invalid date');
  });

  test('formats short timestamp string properly', () => {
    assert.strictEqual(formatShortTimestamp('2026-08-16T12:34:56.789Z'), '2026-08-16 12:34:56 UTC');
    assert.strictEqual(formatShortTimestamp('not-a-date'), 'N/A');
  });
});
