'use client';

import { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import { formatINR } from '@/lib/currency';
import { Database, Plus, ExternalLink, RefreshCw, X } from 'lucide-react';

interface PricingRate {
  id: string;
  provider: string;
  model: string;
  input_cost_per_1k: number;
  output_cost_per_1k: number;
  cache_read_cost_per_1k: number;
  reasoning_cost_per_1k: number;
  currency: string;
  source_url: string;
  effective_from: string;
}

export default function PricingPage() {
  const [rates, setRates] = useState<PricingRate[]>([]);
  const [loading, setLoading] = useState(true);
  const [isAddOpen, setIsAddOpen] = useState(false);

  // Form state
  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('');
  const [inputRate, setInputRate] = useState('0.0025');
  const [outputRate, setOutputRate] = useState('0.0100');

  useEffect(() => {
    loadRates();
  }, []);

  const loadRates = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<PricingRate[]>('/pricing');
      setRates(data);
    } catch {} finally {
      setLoading(false);
    }
  };

  const handleAddRate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!model.trim()) return;

    try {
      await apiFetch('/pricing', {
        method: 'POST',
        body: JSON.stringify({
          provider,
          model,
          input_cost_per_1k: parseFloat(inputRate),
          output_cost_per_1k: parseFloat(outputRate),
        }),
      });
      setIsAddOpen(false);
      setModel('');
      loadRates();
    } catch (err: any) {
      alert(err.message || 'Failed to add pricing rate');
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-pace-border pb-5">
        <div>
          <h2 className="text-xl font-mono font-extrabold text-white tracking-wider uppercase flex items-center space-x-2.5">
            <Database className="w-5 h-5 text-pace-lime" />
            <span>Pricing Registry Catalog</span>
          </h2>
          <p className="text-xs text-pace-muted font-mono mt-1">Auditable versioned cost calculation rates for LLM provider models.</p>
        </div>
        <button
          onClick={() => setIsAddOpen(true)}
          className="bg-pace-lime hover:bg-pace-accentHover text-pace-bg text-xs font-mono font-bold px-4 py-2.5 rounded-xl flex items-center space-x-2 transition shadow-lg shadow-pace-lime/20"
        >
          <Plus className="w-4 h-4" />
          <span>ADD CUSTOM RATE →</span>
        </button>
      </div>

      {/* Pricing Table */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl overflow-hidden shadow-2xl">
        {loading ? (
          <div className="p-8 text-center font-mono text-xs text-pace-muted flex items-center justify-center space-x-2">
            <RefreshCw className="w-4 h-4 animate-spin text-pace-lime" />
            <span>Loading pricing registry rates...</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono text-pace-text">
              <thead className="bg-pace-bg/80 border-b border-pace-border text-pace-muted uppercase tracking-wider font-bold text-[10px]">
                <tr>
                  <th className="py-3.5 px-4">Provider</th>
                  <th className="py-3.5 px-4">Model</th>
                  <th className="py-3.5 px-4">Input / 1k (INR)</th>
                  <th className="py-3.5 px-4">Output / 1k (INR)</th>
                  <th className="py-3.5 px-4">Cache Read / 1k</th>
                  <th className="py-3.5 px-4">Reasoning / 1k</th>
                  <th className="py-3.5 px-4">Effective From</th>
                  <th className="py-3.5 px-4">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-pace-border/50">
                {rates.map((r) => (
                  <tr key={r.id} className="hover:bg-pace-surfaceHover/70 transition">
                    <td className="py-3.5 px-4 font-bold text-white uppercase">
                      <span className="px-1.5 py-0.5 rounded bg-pace-bg border border-pace-border text-white text-[10px]">
                        {r.provider}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-pace-lavender font-bold">{r.model}</td>
                    <td className="py-3.5 px-4 text-white font-bold">{formatINR(r.input_cost_per_1k, 4)}</td>
                    <td className="py-3.5 px-4 text-white font-bold">{formatINR(r.output_cost_per_1k, 4)}</td>
                    <td className="py-3.5 px-4 text-pace-muted">{formatINR(r.cache_read_cost_per_1k, 4)}</td>
                    <td className="py-3.5 px-4 text-pace-muted">{formatINR(r.reasoning_cost_per_1k, 4)}</td>
                    <td className="py-3.5 px-4 text-pace-muted">{new Date(r.effective_from).toLocaleDateString()}</td>
                    <td className="py-3.5 px-4">
                      {r.source_url ? (
                        <a href={r.source_url} target="_blank" rel="noreferrer" className="text-pace-lime hover:underline flex items-center space-x-1 font-bold">
                          <span>Official</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ) : (
                        <span className="text-pace-muted">Custom</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Rate Modal */}
      {isAddOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-pace-surface border border-pace-border w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-pace-border pb-3">
              <h3 className="font-mono font-bold text-lg text-white">Add Custom Pricing Rate</h3>
              <button onClick={() => setIsAddOpen(false)} className="text-pace-muted hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddRate} className="space-y-4 font-mono text-xs">
              <div>
                <label className="block text-pace-muted mb-1.5 font-bold uppercase">Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full bg-pace-bg border border-pace-border rounded-xl p-3 text-white focus:outline-none focus:border-pace-lime font-bold"
                >
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="azure">Azure</option>
                  <option value="custom">Custom Provider</option>
                </select>
              </div>

              <div>
                <label className="block text-pace-muted mb-1.5 font-bold uppercase">Model Identifier</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. gpt-4o-custom"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-pace-bg border border-pace-border rounded-xl p-3 text-white focus:outline-none focus:border-pace-lime font-bold"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-pace-muted mb-1.5 font-bold uppercase">Input / 1k ($)</label>
                  <input
                    type="number"
                    step="0.000001"
                    required
                    value={inputRate}
                    onChange={(e) => setInputRate(e.target.value)}
                    className="w-full bg-pace-bg border border-pace-border rounded-xl p-3 text-white focus:outline-none focus:border-pace-lime font-bold"
                  />
                </div>
                <div>
                  <label className="block text-pace-muted mb-1.5 font-bold uppercase">Output / 1k ($)</label>
                  <input
                    type="number"
                    step="0.000001"
                    required
                    value={outputRate}
                    onChange={(e) => setOutputRate(e.target.value)}
                    className="w-full bg-pace-bg border border-pace-border rounded-xl p-3 text-white focus:outline-none focus:border-pace-lime font-bold"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button type="button" onClick={() => setIsAddOpen(false)} className="px-4 py-2.5 text-pace-muted hover:text-white font-bold">CANCEL</button>
                <button type="submit" className="bg-pace-lime hover:bg-pace-accentHover text-pace-bg font-bold px-5 py-2.5 rounded-xl">SAVE RATE →</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
