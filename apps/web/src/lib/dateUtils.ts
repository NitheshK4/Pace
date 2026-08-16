/**
 * Utility functions for formatting timestamps and calculating relative dates.
 */

export function formatRelativeTime(dateString: string, nowOverride?: Date): string {
  const date = new Date(dateString);
  const now = nowOverride || new Date();
  const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (isNaN(diffSeconds)) return 'Invalid date';
  if (diffSeconds < 5) return 'just now';
  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function formatShortTimestamp(dateString: string): string {
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return 'N/A';
  return date.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
}
