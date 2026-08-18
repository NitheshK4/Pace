import { describe, it } from 'node:test';
import assert from 'node:assert';
import { LoadingSpinner } from '../components/LoadingSpinner';

describe('LoadingSpinner component export', () => {
  it('is a valid React component function', () => {
    assert.strictEqual(typeof LoadingSpinner, 'function');
  });
});
