'use client';

import { useState } from 'react';
import { apiFetch } from '@/lib/api';
import { X, Sparkles, FolderPlus } from 'lucide-react';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (project: any, initialKey: any) => void;
}

export function CreateProjectModal({ isOpen, onClose, onSuccess }: CreateProjectModalProps) {
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError('');

    try {
      const res = await apiFetch<{ project: any; initial_api_key: any }>('/projects', {
        method: 'POST',
        body: JSON.stringify({ name }),
      });
      setName('');
      onSuccess(res.project, res.initial_api_key);
    } catch (err: any) {
      setError(err.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-pace-surface border border-pace-border w-full max-w-md rounded-2xl p-6 shadow-2xl space-y-5 relative overflow-hidden">
        {/* Top Glow Accent Bar */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-pace-lime to-pace-lavender" />

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-pace-lime/10 border border-pace-lime/30 flex items-center justify-center">
              <FolderPlus className="w-5 h-5 text-pace-lime" />
            </div>
            <div>
              <h3 className="font-bold text-lg text-white">Create New Project</h3>
              <p className="text-xs text-pace-muted font-mono">TELEMETRY INGESTION DOMAIN</p>
            </div>
          </div>
          <button onClick={onClose} className="text-pace-muted hover:text-white p-1 rounded-lg hover:bg-pace-bg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="text-xs text-pace-coral bg-pace-coral/10 p-3.5 rounded-xl border border-pace-coral/20 font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono font-bold text-pace-muted mb-1.5 uppercase tracking-wider">
              Project Name
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Customer Support AI Agent"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-pace-bg border border-pace-border rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-pace-lime font-mono shadow-inner"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-xs text-pace-muted hover:text-white font-mono font-bold"
            >
              CANCEL
            </button>
            <button
              type="submit"
              disabled={loading}
              className="bg-pace-lime hover:bg-pace-accentHover text-pace-bg text-xs font-mono font-bold px-5 py-2.5 rounded-xl transition shadow-lg shadow-pace-lime/20"
            >
              {loading ? 'CREATING...' : 'CREATE PROJECT →'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
