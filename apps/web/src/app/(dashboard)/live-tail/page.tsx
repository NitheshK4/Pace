'use client';

import { useState, useEffect, useRef } from 'react';
import { apiFetch } from '@/lib/api';
import { formatINR } from '@/lib/currency';
import { Radio, Pause, Play, Wifi, WifiOff, Trash2, Terminal } from 'lucide-react';

interface LiveEvent {
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

export default function LiveTailPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [statusFilter, setStatusFilter] = useState<'all' | '2xx' | '429' | '5xx'>('all');
  const [isPaused, setIsPaused] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    fetchFirstProject();
  }, []);

  useEffect(() => {
    if (!projectId || isPaused) return;

    const token = localStorage.getItem('pace_token') || '';
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/v1';
    const url = `${baseUrl}/analytics/live-tail?project_id=${projectId}`;

    const es = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
    };

    es.onmessage = (e) => {
      try {
        const evData: LiveEvent = JSON.parse(e.data);
        setEvents((prev) => [evData, ...prev.slice(0, 99)]);
      } catch {}
    };

    es.onerror = () => {
      setIsConnected(false);
    };

    return () => {
      es.close();
      setIsConnected(false);
    };
  }, [projectId, isPaused]);

  const fetchFirstProject = async () => {
    try {
      const projects = await apiFetch<any[]>('/projects');
      if (projects.length > 0) setProjectId(projects[0].id);
    } catch {}
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-pace-border pb-5">
        <div>
          <h2 className="text-xl font-mono font-extrabold text-white tracking-wider uppercase flex items-center space-x-2.5">
            <Radio className="w-5 h-5 text-pace-lime animate-pulse" />
            <span>Live Telemetry Tail Stream</span>
          </h2>
          <p className="text-xs text-pace-muted font-mono mt-1">Real-time SSE event stream for live LLM model execution.</p>
        </div>

        <div className="flex items-center space-x-3 font-mono text-xs">
          {/* Connection Status Badge */}
          <div className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl font-bold ${
            isConnected ? 'bg-pace-emerald/10 text-pace-emerald border border-pace-emerald/30' : 'bg-pace-amber/10 text-pace-amber border border-pace-amber/30'
          }`}>
            {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            <span>{isConnected ? 'STREAM ACTIVE' : 'RECONNECTING'}</span>
          </div>

          {/* Pause / Play toggle */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className="bg-pace-surface border border-pace-border hover:border-pace-lime text-white font-bold px-3.5 py-1.5 rounded-xl flex items-center space-x-1.5 transition"
          >
            {isPaused ? <Play className="w-3.5 h-3.5 text-pace-emerald" /> : <Pause className="w-3.5 h-3.5 text-pace-amber" />}
            <span>{isPaused ? 'RESUME STREAM' : 'PAUSE STREAM'}</span>
          </button>

          {/* Clear Feed */}
          <button
            onClick={() => setEvents([])}
            className="bg-pace-surface border border-pace-border hover:text-white text-pace-muted px-3 py-1.5 rounded-xl flex items-center space-x-1 transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>CLEAR</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs Bar */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl p-3.5 flex items-center justify-between font-mono text-xs shadow-lg">
        <div className="flex items-center space-x-2">
          <span className="text-pace-muted font-bold mr-2 uppercase">Filter Status:</span>
          {(['all', '2xx', '429', '5xx'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setStatusFilter(mode)}
              className={`px-3 py-1 rounded-lg font-bold uppercase transition ${
                statusFilter === mode
                  ? 'bg-pace-lime text-pace-bg shadow'
                  : 'bg-pace-bg border border-pace-border text-pace-muted hover:text-white'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
        <div className="text-pace-muted">
          Feed events: <strong className="text-white">{events.length}</strong>
        </div>
      </div>

      {/* Stream Events Terminal Box */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl p-5 shadow-2xl space-y-3 font-mono text-xs max-h-[600px] overflow-y-auto">
        {events.length === 0 ? (
          <div className="p-12 text-center text-pace-muted space-y-3">
            <Terminal className="w-8 h-8 animate-pulse mx-auto text-pace-lime" />
            <div className="text-white font-bold">LISTENING FOR INCOMING TELEMETRY SIGNALS...</div>
            <div className="text-[11px] text-pace-muted">Events will populate in real-time as your application makes LLM requests.</div>
          </div>
        ) : (
          events
            .filter((ev) => {
              if (statusFilter === '2xx') return ev.status_code >= 200 && ev.status_code < 300;
              if (statusFilter === '429') return ev.status_code === 429;
              if (statusFilter === '5xx') return ev.status_code >= 500;
              return true;
            })
            .map((ev) => (
              <div
                key={ev.id}
                className="bg-pace-bg border border-pace-border/70 p-3.5 rounded-xl flex flex-wrap items-center justify-between gap-3 animate-fade-in hover:border-pace-lime/50 transition shadow-inner"
              >
                <div className="flex items-center space-x-3">
                  <span className="text-pace-muted">{new Date(ev.time).toLocaleTimeString()}</span>
                  <span className="bg-pace-surface border border-pace-border text-pace-lime px-2 py-0.5 rounded uppercase text-[10px] font-bold">
                    {ev.provider}
                  </span>
                  <span className="text-white font-bold">{ev.model}</span>
                </div>

                <div className="flex items-center space-x-4">
                  <span>In: <strong className="text-white">{ev.input_tokens}</strong></span>
                  <span>Out: <strong className="text-white">{ev.output_tokens}</strong></span>
                  <span className="text-pace-lime font-bold">
                    {ev.cost_usd !== null ? formatINR(ev.cost_usd, 4) : 'NULL'}
                  </span>
                  <span>{ev.latency_ms} ms</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    ev.status_code < 400 ? 'bg-pace-emerald/10 border border-pace-emerald/30 text-pace-emerald' : 'bg-pace-coral/10 border border-pace-coral/30 text-pace-coral'
                  }`}>
                    {ev.status_code}
                  </span>
                </div>
              </div>
            ))
        )}
      </div>
    </div>
  );
}
