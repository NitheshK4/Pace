import React from 'react';

interface LatencyBadgeProps {
  latencyMs: number;
}

export function LatencyBadge({ latencyMs }: LatencyBadgeProps) {
  let badgeColor = 'bg-green-500/10 text-green-400 border-green-500/20';
  let tier = 'Fast';

  if (latencyMs > 2000) {
    badgeColor = 'bg-red-500/10 text-red-400 border-red-500/20';
    tier = 'Slow';
  } else if (latencyMs > 800) {
    badgeColor = 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    tier = 'Moderate';
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${badgeColor}`}
    >
      {latencyMs} ms ({tier})
    </span>
  );
}
