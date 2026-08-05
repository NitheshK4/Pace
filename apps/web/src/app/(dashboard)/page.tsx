'use client';

import { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import { formatINR } from '@/lib/currency';
import { 
  IndianRupee, 
  Activity, 
  Cpu, 
  Clock, 
  AlertTriangle, 
  ArrowUpRight,
  Code2,
  RefreshCw,
  Zap,
  TrendingUp,
  Layers,
  ShieldCheck,
  Radio,
  ExternalLink
} from 'lucide-react';

interface OverviewData {
  total_spend_usd: number;
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cached_tokens: number;
  total_reasoning_tokens: number;
  error_count: number;
  error_rate: number;
  rate_limit_count: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  unknown_cost_events_count: number;
  spend_provenance: string;
}

interface EventItem {
  id: string;
  event_id: string;
  time: string;
  provider: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number | null;
  latency_ms: number;
  status_code: number;
}

export default function OverviewPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFirstProject();
  }, []);

  useEffect(() => {
    if (projectId) {
      loadData(projectId);
    }
  }, [projectId]);

  const fetchFirstProject = async () => {
    try {
      const projects = await apiFetch<any[]>('/projects');
      if (projects.length > 0) {
        setProjectId(projects[0].id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  };

  const loadData = async (pid: string) => {
    setLoading(true);
    try {
      const [ovData, evData] = await Promise.all([
        apiFetch<OverviewData>(`/analytics/overview?project_id=${pid}`),
        apiFetch<{ events: EventItem[] }>(`/analytics/events?project_id=${pid}&limit=20`),
      ]);
      setOverview(ovData);
      setEvents(evData.events);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  // Compute Model Mix statistics from events
  const modelMixMap: Record<string, { name: string; provider: string; count: number; tokens: number; cost: number }> = {};
  events.forEach((ev) => {
    const key = `${ev.provider}:${ev.model}`;
    if (!modelMixMap[key]) {
      modelMixMap[key] = { name: ev.model, provider: ev.provider, count: 0, tokens: 0, cost: 0 };
    }
    modelMixMap[key].count += 1;
    modelMixMap[key].tokens += (ev.input_tokens + ev.output_tokens);
    modelMixMap[key].cost += (ev.cost_usd || 0);
  });

  const modelMixList = Object.values(modelMixMap).sort((a, b) => b.tokens - a.tokens);
  const totalMixTokens = modelMixList.reduce((sum, item) => sum + item.tokens, 0);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-pace-muted space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-pace-surface border border-pace-border flex items-center justify-center shadow-lg">
          <RefreshCw className="w-6 h-6 animate-spin text-pace-lime" />
        </div>
        <div className="text-center font-mono text-xs space-y-1">
          <div className="text-white font-bold">CONNECTING TO TELEMETRY STREAM...</div>
          <div className="text-pace-muted">Aggregating real-time model events and cost estimates</div>
        </div>
      </div>
    );
  }

  if (!projectId || !overview) {
    return (
      <div className="max-w-2xl mx-auto mt-12 bg-pace-surface border border-pace-border rounded-2xl p-8 text-center space-y-6 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-pace-lime via-pace-lavender to-pace-cyan" />
        <div className="w-14 h-14 rounded-2xl bg-pace-bg border border-pace-lime/30 mx-auto flex items-center justify-center text-pace-lime shadow-lg">
          <Radio className="w-7 h-7 animate-pulse" />
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-extrabold text-white tracking-wide">No Telemetry Signals Received Yet</h2>
          <p className="text-xs text-pace-muted max-w-md mx-auto leading-relaxed">
            Create a project, copy your ingestion key, and instrument your LLM application using the Pace SDK to view real-time telemetry analytics.
          </p>
        </div>

        <div className="bg-pace-bg border border-pace-border p-4 rounded-xl text-left font-mono text-xs text-pace-muted space-y-2">
          <div className="text-pace-lime font-bold uppercase tracking-wider">Quick Instrument Snippet (Python):</div>
          <pre className="text-white text-[11px] overflow-x-auto p-2 bg-pace-surface rounded border border-pace-border">
{`from pace import PaceClient
with PaceClient(api_key="YOUR_KEY") as pace:
    client = pace.track(OpenAI())`}
          </pre>
        </div>

        <a
          href="/quickstart"
          className="inline-flex items-center space-x-2 bg-pace-lime hover:bg-pace-accentHover text-pace-bg text-xs font-mono font-bold px-6 py-3 rounded-xl transition shadow-lg shadow-pace-lime/20"
        >
          <Code2 className="w-4 h-4" />
          <span>VIEW QUICK START SDK GUIDE →</span>
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Banner / Mission Control Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-pace-border pb-5">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-pace-lime animate-pulse" />
            <h2 className="text-xl font-mono font-extrabold text-white tracking-wider uppercase">
              Mission Control Overview
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-pace-surface border border-pace-border text-pace-lime">
              TELEMETRY LIVE
            </span>
          </div>
          <p className="text-xs text-pace-muted font-mono mt-1">
            Real-time LLM cost tracking, token mix, and latency observability.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => loadData(projectId)}
            className="bg-pace-surface hover:bg-pace-surfaceHover border border-pace-border text-white text-xs font-mono font-bold px-3.5 py-2 rounded-xl flex items-center space-x-2 transition shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5 text-pace-lime" />
            <span>SYNC DATA</span>
          </button>
        </div>
      </div>

      {/* Hero "Mission Control" Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Estimated Spend Card */}
        <div className="bg-pace-surface border border-pace-border rounded-2xl p-5 space-y-3 relative overflow-hidden card-glow-hover">
          <div className="flex items-center justify-between text-pace-muted text-[11px] font-mono font-bold uppercase tracking-wider">
            <span>Estimated Spend</span>
            <IndianRupee className="w-4 h-4 text-pace-lime" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-white tracking-tight">
            {formatINR(overview.total_spend_usd, 2)}
          </div>
          <div className="text-[10px] font-mono text-pace-muted flex items-center justify-between border-t border-pace-border/60 pt-2">
            <span className="text-pace-lime font-bold">~${overview.total_spend_usd.toFixed(4)} USD</span>
            <span>Transparent Rates</span>
          </div>
        </div>

        {/* Total Requests Card */}
        <div className="bg-pace-surface border border-pace-border rounded-2xl p-5 space-y-3 card-glow-hover">
          <div className="flex items-center justify-between text-pace-muted text-[11px] font-mono font-bold uppercase tracking-wider">
            <span>System Requests</span>
            <Activity className="w-4 h-4 text-pace-cyan" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-white tracking-tight">
            {overview.total_requests.toLocaleString()}
          </div>
          <div className="text-[10px] font-mono text-pace-muted flex items-center justify-between border-t border-pace-border/60 pt-2">
            <span className="text-pace-cyan font-bold">100% Server Validated</span>
            <span>Rate Limits: {overview.rate_limit_count}</span>
          </div>
        </div>

        {/* Tokens Processed Card */}
        <div className="bg-pace-surface border border-pace-border rounded-2xl p-5 space-y-3 card-glow-hover">
          <div className="flex items-center justify-between text-pace-muted text-[11px] font-mono font-bold uppercase tracking-wider">
            <span>Tokens Processed</span>
            <Cpu className="w-4 h-4 text-pace-lavender" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-white tracking-tight">
            {(overview.total_input_tokens + overview.total_output_tokens).toLocaleString()}
          </div>
          <div className="text-[10px] font-mono text-pace-muted flex items-center justify-between border-t border-pace-border/60 pt-2">
            <span>In: <strong className="text-white">{overview.total_input_tokens.toLocaleString()}</strong></span>
            <span>Out: <strong className="text-white">{overview.total_output_tokens.toLocaleString()}</strong></span>
          </div>
        </div>

        {/* Latency & Error Rate Card */}
        <div className="bg-pace-surface border border-pace-border rounded-2xl p-5 space-y-3 card-glow-hover">
          <div className="flex items-center justify-between text-pace-muted text-[11px] font-mono font-bold uppercase tracking-wider">
            <span>Avg Latency & Errors</span>
            <Clock className="w-4 h-4 text-pace-amber" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-white tracking-tight">
            {overview.avg_latency_ms} <span className="text-xs font-mono font-normal text-pace-muted">ms</span>
          </div>
          <div className="text-[10px] font-mono text-pace-muted flex items-center justify-between border-t border-pace-border/60 pt-2">
            <span>P95: <strong className="text-white">{overview.p95_latency_ms}ms</strong></span>
            <span className={overview.error_rate > 0 ? 'text-pace-coral font-bold' : 'text-pace-emerald font-bold'}>
              Errors: {overview.error_rate}%
            </span>
          </div>
        </div>
      </div>

      {/* Unknown Cost Notice Banner if any */}
      {overview.unknown_cost_events_count > 0 && (
        <div className="bg-pace-amber/10 border border-pace-amber/30 rounded-2xl p-4 flex items-center justify-between text-xs font-mono text-pace-amber shadow-lg">
          <div className="flex items-center space-x-2.5">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>
              {overview.unknown_cost_events_count} event(s) used unlisted models or models without pricing rates. Cost is recorded as NULL.
            </span>
          </div>
          <a href="/pricing" className="underline font-bold hover:text-white flex items-center space-x-1">
            <span>Configure Rates</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      )}

      {/* Grid Row: Model Mix Panel + Telemetry Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Model Mix Distribution Panel */}
        <div className="bg-pace-surface border border-pace-border rounded-2xl p-6 space-y-5 shadow-xl">
          <div className="flex items-center justify-between border-b border-pace-border pb-3">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-pace-lavender" />
              <h3 className="font-mono font-bold text-white text-sm uppercase">Model Mix & Volume</h3>
            </div>
            <span className="text-[10px] font-mono text-pace-muted">{modelMixList.length} Model(s)</span>
          </div>

          {modelMixList.length === 0 ? (
            <div className="text-xs font-mono text-pace-muted text-center py-6">
              No model mix telemetry available yet.
            </div>
          ) : (
            <div className="space-y-4 font-mono text-xs">
              {modelMixList.map((item) => {
                const percent = totalMixTokens > 0 ? ((item.tokens / totalMixTokens) * 100).toFixed(1) : '0.0';
                return (
                  <div key={`${item.provider}:${item.name}`} className="space-y-1.5">
                    <div className="flex justify-between items-center text-xs">
                      <div className="flex items-center space-x-2">
                        <span className="uppercase text-[10px] px-1.5 py-0.5 rounded bg-pace-bg border border-pace-border text-pace-lavender font-bold">
                          {item.provider}
                        </span>
                        <span className="text-white font-bold">{item.name}</span>
                      </div>
                      <span className="text-pace-lime font-bold">{percent}%</span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-pace-bg h-2 rounded-full overflow-hidden border border-pace-border">
                      <div
                        className="bg-gradient-to-r from-pace-lavender to-pace-lime h-full rounded-full transition-all"
                        style={{ width: `${percent}%` }}
                      />
                    </div>

                    <div className="flex justify-between text-[10px] text-pace-muted pt-0.5">
                      <span>Requests: {item.count}</span>
                      <span>Cost: {formatINR(item.cost, 4)}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Telemetry Event Stream Table (Takes 2 Cols) */}
        <div className="lg:col-span-2 bg-pace-surface border border-pace-border rounded-2xl overflow-hidden shadow-xl flex flex-col justify-between">
          <div>
            <div className="p-5 border-b border-pace-border flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Radio className="w-4 h-4 text-pace-lime animate-pulse" />
                <h3 className="font-mono font-bold text-white text-sm uppercase">Recent Ingested Telemetry</h3>
              </div>
              <a
                href="/explorer"
                className="text-xs font-mono text-pace-lime hover:underline flex items-center space-x-1 font-bold"
              >
                <span>EXPLORE ALL EVENTS</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </a>
            </div>

            {events.length === 0 ? (
              <div className="p-8 text-center text-xs font-mono text-pace-muted">
                No recent events recorded in this time range.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs font-mono text-pace-text">
                  <thead className="bg-pace-bg/80 border-b border-pace-border text-pace-muted uppercase tracking-wider font-bold text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Time (UTC)</th>
                      <th className="py-3 px-4">Provider</th>
                      <th className="py-3 px-4">Model</th>
                      <th className="py-3 px-4">Tokens (In / Out)</th>
                      <th className="py-3 px-4">Est. Cost</th>
                      <th className="py-3 px-4">Latency</th>
                      <th className="py-3 px-4">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-pace-border/50">
                    {events.map((ev) => (
                      <tr key={ev.id} className="hover:bg-pace-surfaceHover/70 transition">
                        <td className="py-3 px-4 text-pace-muted">{new Date(ev.time).toLocaleTimeString()}</td>
                        <td className="py-3 px-4">
                          <span className="uppercase font-bold text-[10px] px-1.5 py-0.5 rounded bg-pace-bg border border-pace-border text-white">
                            {ev.provider}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-pace-lavender font-bold">{ev.model}</td>
                        <td className="py-3 px-4 text-white">
                          {ev.input_tokens} / {ev.output_tokens}
                        </td>
                        <td className="py-3 px-4 text-pace-lime font-bold">
                          {ev.cost_usd !== null ? formatINR(ev.cost_usd, 4) : <span className="text-pace-muted italic">NULL</span>}
                        </td>
                        <td className="py-3 px-4 text-white">{ev.latency_ms} ms</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            ev.status_code < 400
                              ? 'bg-pace-emerald/10 border border-pace-emerald/30 text-pace-emerald'
                              : 'bg-pace-coral/10 border border-pace-coral/30 text-pace-coral'
                          }`}>
                            {ev.status_code}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
