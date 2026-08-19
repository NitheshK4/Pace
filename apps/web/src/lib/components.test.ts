import { describe, it } from 'node:test';
import assert from 'node:assert';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { EnvironmentBadge } from '../components/EnvironmentBadge';

describe('UI components export sanity', () => {
  it('is a valid React component function for LoadingSpinner', () => {
    assert.strictEqual(typeof LoadingSpinner, 'function');
  });

  it('is a valid React component function for EnvironmentBadge', () => {
    assert.strictEqual(typeof EnvironmentBadge, 'function');
  });
});
