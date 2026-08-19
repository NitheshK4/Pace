import React from 'react';

interface EnvironmentBadgeProps {
  environment: string;
  size?: 'sm' | 'md';
}

export function EnvironmentBadge({ environment, size = 'md' }: EnvironmentBadgeProps) {
  const env = environment.toLowerCase().trim();

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';

  if (env === 'production' || env === 'prod') {
    colorClasses = 'bg-indigo-950/60 text-indigo-400 border-indigo-800/60';
  } else if (env === 'staging') {
    colorClasses = 'bg-amber-950/60 text-amber-400 border-amber-800/60';
  } else if (env === 'development' || env === 'dev') {
    colorClasses = 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60';
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-semibold';

  return (
    <span className={`inline-flex items-center uppercase tracking-wider rounded-md border ${colorClasses} ${sizeClasses}`}>
      {environment}
    </span>
  );
}
