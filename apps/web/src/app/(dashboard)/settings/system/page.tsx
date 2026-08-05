'use client';

import { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import { Settings, ShieldCheck, Database, RefreshCw, Trash2, CheckCircle2, Server, Cpu } from 'lucide-react';

interface DiagnosticsData {
  component: string;
  version: string;
  database_status: string;
  timescale_enabled: boolean;
  demo_mode: boolean;
  worker_enabled: boolean;
  data_retention_days: number;
  pricing_registry_version: string;
}

export default function SystemSettingsPage() {
  const [diag, setDiag] = useState<DiagnosticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [purging, setPurging] = useState(false);
  const [purgeStatus, setPurgeStatus] = useState<string | null>(null);

  useEffect(() => {
    loadDiagnostics();
  }, []);

  const loadDiagnostics = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<DiagnosticsData>('/system/diagnostics');
      setDiag(data);
    } catch {} finally {
      setLoading(false);
    }
  };

  const handlePurge = async () => {
    if (!confirm('Are you sure you want to purge telemetry data older than 90 days?')) return;
    setPurging(true);
    setPurgeStatus(null);

    try {
      const res = await apiFetch<{ message: string; purged_count: number }>('/system/retention-purge?days=90', {
        method: 'POST',
      });
      setPurgeStatus(`Purge complete: ${res.purged_count} historical telemetry events removed.`);
    } catch (err: any) {
      setPurgeStatus(`Purge error: ${err.message}`);
    } finally {
      setPurging(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div className="border-b border-pace-border pb-5">
        <h2 className="text-xl font-mono font-extrabold text-white tracking-wider uppercase flex items-center space-x-2.5">
          <Settings className="w-5 h-5 text-pace-lime" />
          <span>System Diagnostics & Security</span>
        </h2>
        <p className="text-xs text-pace-muted font-mono mt-1">Component health, zero-content privacy verification, and data retention controls.</p>
      </div>

      {/* Component Status Cards */}
      {loading || !diag ? (
        <div className="p-8 text-center font-mono text-xs text-pace-muted flex items-center justify-center space-x-2">
          <RefreshCw className="w-4 h-4 animate-spin text-pace-lime" />
          <span>Fetching system diagnostics...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 font-mono text-xs">
          <div className="bg-pace-surface border border-pace-border rounded-2xl p-5 space-y-3.5 shadow-xl card-glow-hover">
            <div className="flex items-center space-x-2 text-white font-bold text-sm">
              <Server className="w-4 h-4 text-pace-lime" />
              <span>Core API & Engine</span>
            </div>
            <div className="space-y-2 text-pace-muted border-t border-pace-border pt-2.5">
              <div className="flex justify-between"><span>Version:</span><span className="text-white font-bold">{diag.version}</span></div>
              <div className="flex justify-between">
                <span>Database Status:</span>
                <span className="text-pace-emerald font-bold uppercase">{diag.database_status}</span>
              </div>
              <div className="flex justify-between">
                <span>TimescaleDB Acceleration:</span>
                <span className={diag.timescale_enabled ? 'text-pace-emerald font-bold' : 'text-pace-muted'}>
                  {diag.timescale_enabled ? 'ENABLED' : 'OPTIONAL (Postgres Baseline)'}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-pace-surface border border-pace-border rounded-2xl p-5 space-y-3.5 shadow-xl card-glow-hover">
            <div className="flex items-center space-x-2 text-white font-bold text-sm">
              <Cpu className="w-4 h-4 text-pace-lavender" />
              <span>Worker & Pricing Engine</span>
            </div>
            <div className="space-y-2 text-pace-muted border-t border-pace-border pt-2.5">
              <div className="flex justify-between">
                <span>Background Worker:</span>
                <span className="text-pace-emerald font-bold uppercase">{diag.worker_enabled ? 'ACTIVE' : 'INACTIVE'}</span>
              </div>
              <div className="flex justify-between"><span>Pricing Registry:</span><span className="text-white font-bold">{diag.pricing_registry_version}</span></div>
              <div className="flex justify-between"><span>Configured Retention:</span><span className="text-white font-bold">{diag.data_retention_days} Days</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Security & Zero-Content Statement */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="flex items-center space-x-2.5 text-pace-emerald font-mono font-bold text-sm uppercase">
          <ShieldCheck className="w-5 h-5" />
          <span>Zero-Content & Privacy Hardening Policy</span>
        </div>
        <div className="text-xs font-mono text-pace-muted leading-relaxed space-y-2">
          <p>Pace is engineered with strict zero-content principles. By design:</p>
          <ul className="list-disc list-inside space-y-1 text-pace-text">
            <li>Provider API keys (e.g. OpenAI/Anthropic keys) are NEVER requested, received, or stored.</li>
            <li>Prompts, completions, message content, and system instructions are NEVER logged or saved.</li>
            <li>Project ingestion keys are stored as salted HMAC-SHA256 hashes, never raw.</li>
            <li>Cost metrics are transparent estimates calculated via the versioned pricing registry.</li>
          </ul>
        </div>
      </div>

      {/* Retention Purge Control */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-mono font-bold text-white text-sm uppercase">Manual Telemetry Retention Purge</h3>
            <p className="text-xs text-pace-muted font-mono mt-0.5">Purge telemetry events older than 90 days to free up database storage.</p>
          </div>
          <button
            onClick={handlePurge}
            disabled={purging}
            className="bg-pace-coral/10 hover:bg-pace-coral/20 text-pace-coral border border-pace-coral/30 text-xs font-mono font-bold px-4 py-2.5 rounded-xl flex items-center space-x-2 transition"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>{purging ? 'PURGING...' : 'EXECUTE PURGE'}</span>
          </button>
        </div>

        {purgeStatus && (
          <div className="p-3.5 bg-pace-bg border border-pace-border rounded-xl text-xs text-pace-lime flex items-center space-x-2 font-mono shadow-inner">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{purgeStatus}</span>
          </div>
        )}
      </div>
    </div>
  );
}
