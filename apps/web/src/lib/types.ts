export interface Project {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface ProjectSummary {
  project_id: string;
  total_events: number;
  total_cost_usd: number;
  total_tokens: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  active_alerts_count: number;
}

export interface TimeseriesPoint {
  timestamp: string;
  requests: number;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  avg_latency_ms: number;
}

export interface BreakdownItem {
  dimension: string;
  value: string;
  requests: number;
  cost_usd: number;
  tokens: number;
}

export interface TelemetryEvent {
  id: string;
  event_id: string;
  time: string;
  provider: string;
  model: string;
  endpoint: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  status_code: number;
  metadata?: Record<string, unknown>;
}

export interface EventsListResponse {
  events: TelemetryEvent[];
  total: number;
  has_more: boolean;
  next_cursor?: string;
}

export interface Budget {
  id: string;
  project_id: string;
  name: string;
  amount_usd: number;
  period: string;
  metric: string;
  thresholds_json: number[];
  destinations_json: Array<Record<string, unknown>>;
  is_active: boolean;
}
