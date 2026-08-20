import { describe, it } from 'node:test';
import assert from 'node:assert';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { EnvironmentBadge } from '../components/EnvironmentBadge';
import { StatusBadge, getStatusColorClass } from '../components/StatusBadge';

describe('UI components export sanity', () => {
  it('is a valid React component function for LoadingSpinner', () => {
    assert.strictEqual(typeof LoadingSpinner, 'function');
  });

  it('is a valid React component function for EnvironmentBadge', () => {
    assert.strictEqual(typeof EnvironmentBadge, 'function');
  });

  it('is a valid React component function for StatusBadge and tests getStatusColorClass', () => {
    assert.strictEqual(typeof StatusBadge, 'function');
    assert.strictEqual(getStatusColorClass('active'), 'emerald');
    assert.strictEqual(getStatusColorClass('warning'), 'amber');
    assert.strictEqual(getStatusColorClass('error'), 'rose');
    assert.strictEqual(getStatusColorClass('unknown'), 'gray');
  });
});
