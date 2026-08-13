import { Project, ProjectSummary, TimeseriesPoint, BreakdownItem, TelemetryEvent, EventsListResponse, Budget } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/v1';

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('pace_token') : null;
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('pace_token');
    }
  }

  if (!response.ok) {
    let errorMsg = 'An unexpected error occurred';
    try {
      const errJson = await response.json();
      errorMsg = errJson.detail || errorMsg;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const paceApi = {
  getProjects: () => apiFetch<Project[]>('/projects'),

  getProjectSummary: (projectId: string, timeframe: string = '24h') =>
    apiFetch<ProjectSummary>(`/analytics/summary?project_id=${projectId}&timeframe=${timeframe}`),

  getTimeseries: (projectId: string, timeframe: string = '24h', interval: string = '1h', provider?: string, model?: string) => {
    let url = `/analytics/timeseries?project_id=${projectId}&timeframe=${timeframe}&interval=${interval}`;
    if (provider) url += `&provider=${encodeURIComponent(provider)}`;
    if (model) url += `&model=${encodeURIComponent(model)}`;
    return apiFetch<TimeseriesPoint[]>(url);
  },

  getBreakdown: (projectId: string, group_by: string = 'model', timeframe: string = '24h', provider?: string, model?: string) => {
    let url = `/analytics/breakdown?project_id=${projectId}&group_by=${group_by}&timeframe=${timeframe}`;
    if (provider) url += `&provider=${encodeURIComponent(provider)}`;
    if (model) url += `&model=${encodeURIComponent(model)}`;
    return apiFetch<BreakdownItem[]>(url);
  },

  getEvents: (projectId: string, limit: number = 50, cursor?: string, provider?: string, model?: string) => {
    let url = `/analytics/events?project_id=${projectId}&limit=${limit}`;
    if (cursor) url += `&cursor=${encodeURIComponent(cursor)}`;
    if (provider) url += `&provider=${encodeURIComponent(provider)}`;
    if (model) url += `&model=${encodeURIComponent(model)}`;
    return apiFetch<EventsListResponse>(url);
  },

  getBudgets: (projectId: string) => apiFetch<Budget[]>(`/budgets?project_id=${projectId}`),
};
