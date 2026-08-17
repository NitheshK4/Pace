export function formatStatusLabel(statusCode: number): { label: string; variant: 'success' | 'warning' | 'error' } {
  if (statusCode >= 200 && statusCode < 300) {
    return { label: `${statusCode} OK`, variant: 'success' };
  }
  if (statusCode >= 400 && statusCode < 500) {
    return { label: `${statusCode} Client Error`, variant: 'warning' };
  }
  if (statusCode >= 500) {
    return { label: `${statusCode} Server Error`, variant: 'error' };
  }
  return { label: `${statusCode}`, variant: 'warning' };
}
