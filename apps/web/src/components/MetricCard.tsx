import { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: ReactNode;
  subtitle?: string;
  icon?: ReactNode;
  accentColorClass?: string;
  trend?: string;
}

export function MetricCard({
  label,
  value,
  subtitle,
  icon,
  accentColorClass = 'text-white',
  trend,
}: MetricCardProps) {
  return (
    <div className="bg-pace-surface border border-pace-border p-4 rounded-2xl shadow-md space-y-1.5 transition hover:border-pace-border/80">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-pace-muted font-mono font-bold uppercase tracking-wider">
          {label}
        </span>
        {icon && <div className="text-pace-muted">{icon}</div>}
      </div>
      <div className={`text-2xl font-extrabold font-mono ${accentColorClass}`}>
        {value}
      </div>
      {trend && (
        <div className="text-[11px] font-mono text-pace-muted">
          {trend}
        </div>
      )}
      {subtitle && (
        <div className="text-[10px] font-mono text-pace-muted/70">
          {subtitle}
        </div>
      )}
    </div>
  );
}
