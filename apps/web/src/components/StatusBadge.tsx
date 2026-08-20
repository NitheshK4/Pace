import React from 'react';

interface StatusBadgeProps {
  status: 'active' | 'inactive' | 'warning' | 'error' | 'success' | string;
  label?: string;
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, label, size = 'md' }: StatusBadgeProps) {
  const normalizedStatus = status.toLowerCase();
  
  let badgeStyles = 'bg-gray-800 text-gray-300 border-gray-700';
  let dotStyles = 'bg-gray-400';

  if (normalizedStatus === 'active' || normalizedStatus === 'success') {
    badgeStyles = 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60';
    dotStyles = 'bg-emerald-400 animate-pulse';
  } else if (normalizedStatus === 'warning') {
    badgeStyles = 'bg-amber-950/60 text-amber-400 border-amber-800/60';
    dotStyles = 'bg-amber-400';
  } else if (normalizedStatus === 'error' || normalizedStatus === 'inactive') {
    badgeStyles = 'bg-rose-950/60 text-rose-400 border-rose-800/60';
    dotStyles = 'bg-rose-400';
  }

  const sizeStyles = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm';

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${badgeStyles} ${sizeStyles}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotStyles}`} />
      {label || status}
    </span>
  );
}

export function getStatusColorClass(status: string): string {
  const normalized = (status || '').toLowerCase();
  if (normalized === 'active' || normalized === 'success') return 'emerald';
  if (normalized === 'warning') return 'amber';
  if (normalized === 'error' || normalized === 'inactive') return 'rose';
  return 'gray';
}
