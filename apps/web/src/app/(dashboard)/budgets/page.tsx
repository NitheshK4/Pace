'use client';

import { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import { formatINR, formatINRShort } from '@/lib/currency';
import { Wallet, Plus, Bell, RefreshCw, X, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';

interface Budget {
  id: string;
  name: string;
  amount_usd: number;
  period: string;
  metric: string;
  thresholds: number[];
  destinations: any[];
  is_active: boolean;
}

interface AlertItem {
  id: string;
  event_type: string;
  threshold_percent: number;
  severity: string;
  observed_value: number;
  limit_value: number;
  destination_type: string;
  status: string;
  delivered_at: string;
}

import { useProject } from '@/context/ProjectContext';

export default function BudgetsPage() {
  const { selectedProject, isLoading: projectsLoading } = useProject();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAddOpen, setIsAddOpen] = useState(false);

  // Form state
  const [name, setName] = useState('Monthly Cost Limit');
  const [amountUsd, setAmountUsd] = useState('500');
  const [period, setPeriod] = useState('monthly');
  const [webhookUrl, setWebhookUrl] = useState('');

  useEffect(() => {
    if (selectedProject) {
      loadBudgetsAndAlerts(selectedProject.id);
    } else if (!projectsLoading) {
      setLoading(false);
    }
  }, [selectedProject, projectsLoading]);

  const loadBudgetsAndAlerts = async (pid: string) => {
    setLoading(true);
    try {
      const [bData, aData] = await Promise.all([
        apiFetch<Budget[]>(`/budgets?project_id=${pid}`),
        apiFetch<AlertItem[]>(`/budgets/alerts?project_id=${pid}`),
      ]);
      setBudgets(bData);
      setAlerts(aData);
    } catch {} finally {
      setLoading(false);
    }
  };

  const handleCreateBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) return;

    try {
      const dests: Array<{ type: string; url?: string }> = [{ type: 'console' }];
      if (webhookUrl.trim()) {
        dests.push({ type: 'webhook', url: webhookUrl.trim() });
      }

      await apiFetch('/budgets', {
        method: 'POST',
        body: JSON.stringify({
          project_id: selectedProject.id,
          name,
          amount_usd: parseFloat(amountUsd),
          period,
          metric: 'spend',
          thresholds: [50, 80, 100, 120],
          destinations: dests,
        }),
      });

      setIsAddOpen(false);
      loadBudgetsAndAlerts(selectedProject.id);
    } catch (err: any) {
      alert(err.message || 'Failed to create budget');
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-pace-border pb-5">
        <div>
          <h2 className="text-xl font-mono font-extrabold text-white tracking-wider uppercase flex items-center space-x-2.5">
            <Wallet className="w-5 h-5 text-pace-lime" />
            <span>Budgets & Alert Controls</span>
          </h2>
          <p className="text-xs text-pace-muted font-mono mt-1">Configure threshold limits, deduplicated alerts, and webhook destinations.</p>
        </div>
        <button
          onClick={() => setIsAddOpen(true)}
          className="bg-pace-lime hover:bg-pace-accentHover text-pace-bg text-xs font-mono font-bold px-4 py-2.5 rounded-xl flex items-center space-x-2 transition shadow-lg shadow-pace-lime/20"
        >
          <Plus className="w-4 h-4" />
          <span>NEW BUDGET LIMIT →</span>
        </button>
      </div>

      {/* Active Budgets Grid */}
      <div className="space-y-4">
        <h3 className="text-xs font-mono font-bold text-pace-muted uppercase tracking-wider">Active Budget Controls</h3>
        {loading ? (
          <div className="p-8 text-center font-mono text-xs text-pace-muted flex items-center justify-center space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin text-pace-lime" />
            <span>Loading budget controls...</span>
          </div>
        ) : budgets.length === 0 ? (
          <div className="bg-pace-surface border border-pace-border p-6 rounded-2xl text-center font-mono text-xs text-pace-muted">
            No budgets configured yet. Click "New Budget Limit" above to set a spend limit.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {budgets.map((b) => (
              <div key={b.id} className="bg-pace-surface border border-pace-border rounded-2xl p-5 space-y-4 shadow-xl card-glow-hover">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-mono font-bold text-white text-base">{b.name}</h4>
                    <span className="text-[10px] text-pace-muted font-mono uppercase tracking-wider font-bold">{b.period} {b.metric} limit</span>
                  </div>
                  <div className="text-right font-mono">
                    <div className="text-2xl font-extrabold text-white">{formatINRShort(b.amount_usd, 2)}</div>
                    <span className="inline-flex items-center gap-1 text-[9px] text-pace-emerald font-bold bg-pace-emerald/10 px-2 py-0.5 rounded border border-pace-emerald/30">
                      <span className="w-1.5 h-1.5 rounded-full bg-pace-emerald animate-pulse"></span> ACTIVE CONTROL
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5 font-mono text-xs">
                  <div className="flex justify-between text-pace-muted text-[11px]">
                    <span>Threshold Alerts:</span>
                    <span className="text-white font-bold">{b.thresholds.join('%, ')}%</span>
                  </div>
                  <div className="w-full bg-pace-bg h-2 rounded-full overflow-hidden border border-pace-border">
                    <div className="bg-gradient-to-r from-pace-lime to-pace-amber h-full w-[25%] rounded-full"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Alert Delivery History Feed */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl overflow-hidden shadow-xl space-y-4 p-5">
        <div className="flex items-center space-x-2 text-white font-mono font-bold text-sm uppercase border-b border-pace-border pb-3">
          <Bell className="w-4 h-4 text-pace-amber" />
          <span>Recorded Alert Deliveries & Audit Trail</span>
        </div>

        {alerts.length === 0 ? (
          <div className="text-center font-mono text-xs text-pace-muted py-6">No alert deliveries recorded yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono text-pace-text">
              <thead className="bg-pace-bg/80 border-b border-pace-border text-pace-muted uppercase tracking-wider font-bold text-[10px]">
                <tr>
                  <th className="py-3 px-4">Delivered At (UTC)</th>
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Threshold</th>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Observed / Limit</th>
                  <th className="py-3 px-4">Destination</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-pace-border/50">
                {alerts.map((a) => (
                  <tr key={a.id} className="hover:bg-pace-surfaceHover/70 transition">
                    <td className="py-3.5 px-4 text-pace-muted">{new Date(a.delivered_at).toLocaleString()}</td>
                    <td className="py-3.5 px-4 font-bold text-white">{a.event_type}</td>
                    <td className="py-3.5 px-4 font-bold text-pace-lime">{a.threshold_percent}%</td>
                    <td className="py-3.5 px-4 uppercase font-bold text-[10px]">
                      <span className={`px-2 py-0.5 rounded ${
                        a.severity === 'critical' ? 'bg-pace-coral/10 border border-pace-coral/30 text-pace-coral' : 'bg-pace-amber/10 border border-pace-amber/30 text-pace-amber'
                      }`}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">{formatINRShort(a.observed_value, 2)} / {formatINRShort(a.limit_value, 2)}</td>
                    <td className="py-3.5 px-4 text-pace-muted">{a.destination_type}</td>
                    <td className="py-3.5 px-4">
                      <span className="bg-pace-emerald/10 border border-pace-emerald/30 text-pace-emerald px-2 py-0.5 rounded text-[10px] font-bold uppercase">
                        {a.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Budget Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-pace-surface border border-pace-border w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-pace-border pb-3">
              <h3 className="font-mono font-bold text-lg text-white">Create Budget Limit</h3>
              <button onClick={() => setIsAddOpen(false)} className="text-pace-muted hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateBudget} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-pace-muted mb-1.5 font-bold uppercase">Budget Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Monthly Production LLM Cap"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-pace-bg border border-pace-border rounded-xl p-3 text-white focus:outline-none focus:border-pace-lime"
                />
              </div>

              <div>
                <label className="block text-pace-muted mb-1.5 font-bold uppercase">Amount (USD - auto-converted to INR)</label>
                <input
                  type="number"
                  step="1"
                  required
                  value={amountUsd}
                  onChange={(e) => setAmountUsd(e.target.value)}
                  className="w-full bg-pace-bg border border-pace-border rounded-xl p-3 text-white focus:outline-none focus:border-pace-lime font-bold"
                />
              </div>

              <div>
                <label className="block text-pace-muted mb-1.5 font-bold uppercase">Period</label>
                <select
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  className="w-full bg-pace-bg border border-pace-border rounded-xl p-3 text-white focus:outline-none focus:border-pace-lime font-bold"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="rolling_24h">Rolling 24 Hours</option>
                </select>
              </div>

              <div>
                <label className="block text-pace-muted mb-1.5 font-bold uppercase">Webhook Destination URL (Optional)</label>
                <input
                  type="url"
                  placeholder="https://hooks.slack.com/services/..."
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  className="w-full bg-pace-bg border border-pace-border rounded-xl p-3 text-white focus:outline-none focus:border-pace-lime"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button type="button" onClick={() => setIsAddOpen(false)} className="px-4 py-2.5 text-pace-muted hover:text-white font-bold">CANCEL</button>
                <button type="submit" className="bg-pace-lime hover:bg-pace-accentHover text-pace-bg font-bold px-5 py-2.5 rounded-xl">SAVE BUDGET →</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
