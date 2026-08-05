'use client';

import { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import { formatINR } from '@/lib/currency';
import { Search, Download, Filter, X, ChevronRight, CheckCircle, AlertCircle, RefreshCw, Terminal, Layers } from 'lucide-react';

export default function ExplorerPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null);
  const [providerFilter, setProviderFilter] = useState('');
  const [modelFilter, setModelFilter] = useState('');
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [minLatencyMs, setMinLatencyMs] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchFirstProject();
  }, []);

  useEffect(() => {
    if (projectId) {
      loadEvents(projectId);
    }
  }, [projectId, providerFilter, modelFilter, errorsOnly, minLatencyMs]);

  const fetchFirstProject = async () => {
    try {
      const projects = await apiFetch<any[]>('/projects');
      if (projects.length > 0) setProjectId(projects[0].id);
    } catch {}
  };

  const loadEvents = async (pid: string) => {
    setLoading(true);
    try {
      let query = `/analytics/events?project_id=${pid}&limit=50`;
      if (providerFilter) query += `&provider=${providerFilter}`;
      if (modelFilter) query += `&model=${modelFilter}`;
      if (errorsOnly) query += `&errors_only=true`;
      if (minLatencyMs) query += `&min_latency_ms=${minLatencyMs}`;
      const data = await apiFetch<{ events: any[] }>(query);
      setEvents(data.events);
    } catch {} finally {
      setLoading(false);
    }
  };

  const totalCost = events.reduce((sum, ev) => sum + (ev.cost_usd || 0), 0);
  const avgLatency = events.length > 0 ? Math.round(events.reduce((sum, ev) => sum + (ev.latency_ms || 0), 0) / events.length) : 0;
  const errorCount = events.filter((ev) => ev.status_code >= 400).length;
  const errorRate = events.length > 0 ? ((errorCount / events.length) * 100).toFixed(1) : '0.0';

  const [exporting, setExporting] = useState(false);

  const handleExportCSV = async () => {
    if (!projectId) return;
    setExporting(true);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('pace_token') : null;
      const res = await fetch(`http://localhost:8000/v1/exports/csv?project_id=${projectId}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error('Failed to export CSV');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pace_telemetry_${projectId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      window.open(`http://localhost:8000/v1/exports/csv?project_id=${projectId}`, '_blank');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-pace-border pb-5">
        <div>
          <h2 className="text-xl font-mono font-extrabold text-white tracking-wider uppercase flex items-center space-x-2.5">
            <Search className="w-5 h-5 text-pace-lime" />
            <span>Project Telemetry Explorer</span>
          </h2>
          <p className="text-xs text-pace-muted font-mono mt-1">Filter, inspect, and export LLM usage events in real-time.</p>
        </div>
        <button
          onClick={handleExportCSV}
          disabled={exporting || !projectId}
          className="bg-pace-surface border border-pace-border hover:border-pace-lime text-white text-xs font-mono font-bold px-4 py-2.5 rounded-xl flex items-center space-x-2 transition shadow-md disabled:opacity-50"
        >
          {exporting ? (
            <RefreshCw className="w-4 h-4 text-pace-lime animate-spin" />
          ) : (
            <Download className="w-4 h-4 text-pace-lime" />
          )}
          <span>{exporting ? 'EXPORTING...' : 'EXPORT CSV'}</span>
        </button>
      </div>

      {/* Summary Telemetry Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-pace-surface border border-pace-border p-4 rounded-2xl shadow-md space-y-1">
          <div className="text-[10px] text-pace-muted font-mono font-bold uppercase tracking-wider">Filtered Events</div>
          <div className="text-2xl font-extrabold font-mono text-white">{events.length}</div>
        </div>
        <div className="bg-pace-surface border border-pace-border p-4 rounded-2xl shadow-md space-y-1">
          <div className="text-[10px] text-pace-muted font-mono font-bold uppercase tracking-wider">Filtered Spend</div>
          <div className="text-2xl font-extrabold font-mono text-pace-lime">{formatINR(totalCost, 4)}</div>
        </div>
        <div className="bg-pace-surface border border-pace-border p-4 rounded-2xl shadow-md space-y-1">
          <div className="text-[10px] text-pace-muted font-mono font-bold uppercase tracking-wider">Avg Latency</div>
          <div className="text-2xl font-extrabold font-mono text-pace-cyan">{avgLatency} ms</div>
        </div>
        <div className="bg-pace-surface border border-pace-border p-4 rounded-2xl shadow-md space-y-1">
          <div className="text-[10px] text-pace-muted font-mono font-bold uppercase tracking-wider">Error Rate</div>
          <div className={`text-2xl font-extrabold font-mono ${errorCount > 0 ? 'text-pace-coral' : 'text-pace-emerald'}`}>
            {errorRate}%
          </div>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl p-4 flex flex-wrap gap-4 items-center justify-between shadow-lg">
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
          <Filter className="w-4 h-4 text-pace-lime" />
          <input
            type="text"
            placeholder="Filter by Provider..."
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="bg-pace-bg border border-pace-border rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-pace-lime w-44 font-mono shadow-inner"
          />
          <input
            type="text"
            placeholder="Filter by Model..."
            value={modelFilter}
            onChange={(e) => setModelFilter(e.target.value)}
            className="bg-pace-bg border border-pace-border rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-pace-lime w-44 font-mono shadow-inner"
          />
          <select
            value={minLatencyMs}
            onChange={(e) => setMinLatencyMs(e.target.value)}
            className="bg-pace-bg border border-pace-border rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-pace-lime font-mono shadow-inner"
          >
            <option value="">All Latencies</option>
            <option value="100">≥ 100 ms</option>
            <option value="500">≥ 500 ms</option>
            <option value="1000">≥ 1000 ms (1s)</option>
            <option value="3000">≥ 3000 ms (3s)</option>
          </select>
          <label className="flex items-center space-x-2 text-xs font-mono text-pace-muted cursor-pointer hover:text-white transition">
            <input
              type="checkbox"
              checked={errorsOnly}
              onChange={(e) => setErrorsOnly(e.target.checked)}
              className="rounded border-pace-border text-pace-lime focus:ring-pace-lime bg-pace-bg"
            />
            <span>Errors Only</span>
          </label>
        </div>
        <div className="text-xs font-mono text-pace-muted">
          Showing {events.length} event(s)
        </div>
      </div>

      {/* Events Stream Table */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl overflow-hidden shadow-2xl">
        {loading ? (
          <div className="p-8 text-center font-mono text-xs text-pace-muted flex items-center justify-center space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin text-pace-lime" />
            <span>Loading telemetry events...</span>
          </div>
        ) : events.length === 0 ? (
          <div className="p-8 text-center font-mono text-xs text-pace-muted">No usage events match the current filter parameters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono text-pace-text">
              <thead className="bg-pace-bg/80 border-b border-pace-border text-pace-muted uppercase tracking-wider font-bold text-[10px]">
                <tr>
                  <th className="py-3 px-4">Time (UTC)</th>
                  <th className="py-3 px-4">Provider</th>
                  <th className="py-3 px-4">Model</th>
                  <th className="py-3 px-4">Input Tokens</th>
                  <th className="py-3 px-4">Output Tokens</th>
                  <th className="py-3 px-4">Cost (INR)</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-pace-border/50">
                {events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-pace-surfaceHover/70 transition cursor-pointer" onClick={() => setSelectedEvent(ev)}>
                    <td className="py-3.5 px-4 text-pace-muted">{new Date(ev.time).toLocaleString()}</td>
                    <td className="py-3.5 px-4 font-bold text-white uppercase">
                      <span className="px-1.5 py-0.5 rounded bg-pace-bg border border-pace-border text-white text-[10px]">
                        {ev.provider}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-pace-lavender font-bold">{ev.model}</td>
                    <td className="py-3.5 px-4 text-white">{ev.input_tokens}</td>
                    <td className="py-3.5 px-4 text-white">{ev.output_tokens}</td>
                    <td className="py-3.5 px-4 text-pace-lime font-bold">
                      {ev.cost_usd !== null ? formatINR(ev.cost_usd, 4) : <span className="text-pace-muted italic">NULL</span>}
                    </td>
                    <td className="py-3.5 px-4 text-white">{ev.latency_ms} ms</td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        ev.status_code < 400 ? 'bg-pace-emerald/10 border border-pace-emerald/30 text-pace-emerald' : 'bg-pace-coral/10 border border-pace-coral/30 text-pace-coral'
                      }`}>
                        {ev.status_code}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right text-pace-muted hover:text-white">
                      <ChevronRight className="w-4 h-4 ml-auto" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Event Details Side Drawer */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex justify-end animate-fade-in">
          <div className="bg-pace-surface border-l border-pace-border w-full max-w-md h-full p-6 overflow-y-auto space-y-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-pace-border pb-4">
              <div className="flex items-center space-x-2">
                <Terminal className="w-5 h-5 text-pace-lime" />
                <h3 className="font-mono font-bold text-lg text-white uppercase">Event Telemetry</h3>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="text-pace-muted hover:text-white p-1 rounded-lg hover:bg-pace-bg">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 font-mono text-xs">
              <div className="bg-pace-bg border border-pace-border p-4 rounded-xl space-y-2.5 shadow-inner">
                <div className="text-pace-muted">Event ID: <span className="text-white font-bold">{selectedEvent.event_id}</span></div>
                <div className="text-pace-muted">Timestamp: <span className="text-white">{selectedEvent.time}</span></div>
                <div className="text-pace-muted">Provider: <span className="text-pace-lime font-bold uppercase">{selectedEvent.provider}</span></div>
                <div className="text-pace-muted">Model: <span className="text-white font-bold">{selectedEvent.model}</span></div>
                <div className="text-pace-muted">Request ID: <span className="text-white">{selectedEvent.request_id || 'N/A'}</span></div>
              </div>

              <div className="bg-pace-bg border border-pace-border p-4 rounded-xl space-y-2 shadow-inner">
                <div className="text-pace-lime font-bold uppercase tracking-wider text-[10px] mb-1">Token Mix & Cost</div>
                <div className="flex justify-between"><span>Input Tokens:</span><span className="text-white font-bold">{selectedEvent.input_tokens}</span></div>
                <div className="flex justify-between"><span>Output Tokens:</span><span className="text-white font-bold">{selectedEvent.output_tokens}</span></div>
                <div className="flex justify-between"><span>Cached Tokens:</span><span className="text-white">{selectedEvent.cached_input_tokens || 0}</span></div>
                <div className="flex justify-between"><span>Reasoning Tokens:</span><span className="text-white">{selectedEvent.reasoning_tokens || 0}</span></div>
                <div className="flex justify-between border-t border-pace-border pt-2 font-bold">
                  <span>Estimated Cost:</span>
                  <span className="text-pace-lime">{selectedEvent.cost_usd !== null ? formatINR(selectedEvent.cost_usd, 4) : 'NULL (Unknown)'}</span>
                </div>
              </div>

              {selectedEvent.metadata_json && (
                <div className="bg-pace-bg border border-pace-border p-4 rounded-xl space-y-2 shadow-inner">
                  <div className="text-pace-cyan font-bold uppercase tracking-wider text-[10px] mb-1">Sanitized Metadata</div>
                  <pre className="text-pace-text text-[11px] overflow-x-auto p-2 bg-pace-surface rounded border border-pace-border">
                    {JSON.stringify(selectedEvent.metadata_json, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
