export function getLatencyTier(latencyMs: number): { tier: 'Fast' | 'Moderate' | 'Slow'; variant: 'success' | 'warning' | 'error' } {
  if (latencyMs > 2000) {
    return { tier: 'Slow', variant: 'error' };
  }
  if (latencyMs > 800) {
    return { tier: 'Moderate', variant: 'warning' };
  }
  return { tier: 'Fast', variant: 'success' };
}
