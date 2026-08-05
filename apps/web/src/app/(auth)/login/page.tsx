'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/api';
import { Zap, ShieldCheck, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const res = await apiFetch<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem('pace_token', res.access_token);
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-pace-bg flex items-center justify-center p-4 bg-observatory-grid relative overflow-hidden">
      {/* Background Ambient Radial Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-pace-lime/5 rounded-full blur-3xl pointer-events-none" />

      <div className="bg-pace-surface border border-pace-border w-full max-w-md rounded-2xl p-8 shadow-2xl space-y-6 relative overflow-hidden card-glow-hover">
        {/* Glow Accent Line */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-pace-lime via-pace-lavender to-pace-cyan" />

        <div className="text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-pace-bg border border-pace-lime/40 mx-auto flex items-center justify-center text-pace-lime shadow-lg shadow-pace-lime/10">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-mono font-extrabold text-white tracking-wider uppercase">Sign in to Pace</h2>
            <p className="text-xs font-mono text-pace-muted mt-1">LLM Telemetry Command & Cost Observatory</p>
          </div>
        </div>

        {error && (
          <div className="bg-pace-coral/10 border border-pace-coral/30 text-pace-coral text-xs font-mono p-3.5 rounded-xl text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4 font-mono">
          <div>
            <label className="block text-[10px] font-bold text-pace-muted mb-1.5 uppercase tracking-wider">Email Address</label>
            <input
              type="email"
              required
              placeholder="developer@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-pace-bg border border-pace-border rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-pace-lime shadow-inner"
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold text-pace-muted mb-1.5 uppercase tracking-wider">Password</label>
            <input
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-pace-bg border border-pace-border rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-pace-lime shadow-inner"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-pace-lime hover:bg-pace-accentHover text-pace-bg font-bold py-3 rounded-xl transition shadow-lg shadow-pace-lime/20 text-xs tracking-wider uppercase flex items-center justify-center space-x-2"
          >
            <span>{loading ? 'SIGNING IN...' : 'AUTHENTICATE & ENTER OBSERVATORY'}</span>
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        <div className="text-center text-xs font-mono text-pace-muted border-t border-pace-border pt-4">
          Don't have an account?{' '}
          <Link href="/register" className="text-pace-lime hover:underline font-bold">
            Create account
          </Link>
        </div>
      </div>
    </div>
  );
}
