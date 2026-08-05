'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/api';
import { Zap, ArrowRight } from 'lucide-react';

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, full_name: fullName }),
      });
      // Auto login after registration
      const loginRes = await apiFetch<{ access_token: string }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem('pace_token', loginRes.access_token);
      router.push('/');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-pace-bg flex items-center justify-center p-4 bg-observatory-grid relative overflow-hidden">
      {/* Background Ambient Radial Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-pace-lavender/5 rounded-full blur-3xl pointer-events-none" />

      <div className="bg-pace-surface border border-pace-border w-full max-w-md rounded-2xl p-8 shadow-2xl space-y-6 relative overflow-hidden card-glow-hover">
        {/* Glow Accent Line */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-pace-lavender via-pace-lime to-pace-cyan" />

        <div className="text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-pace-bg border border-pace-lavender/40 mx-auto flex items-center justify-center text-pace-lavender shadow-lg shadow-pace-lavender/10">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-mono font-extrabold text-white tracking-wider uppercase">Create Pace Account</h2>
            <p className="text-xs font-mono text-pace-muted mt-1">Start Monitoring LLM Costs & Model Telemetry</p>
          </div>
        </div>

        {error && (
          <div className="bg-pace-coral/10 border border-pace-coral/30 text-pace-coral text-xs font-mono p-3.5 rounded-xl text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-4 font-mono">
          <div>
            <label className="block text-[10px] font-bold text-pace-muted mb-1.5 uppercase tracking-wider">Full Name</label>
            <input
              type="text"
              required
              placeholder="Jane Doe"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full bg-pace-bg border border-pace-border rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-pace-lime shadow-inner"
            />
          </div>

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
              minLength={8}
              placeholder="Minimum 8 characters"
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
            <span>{loading ? 'CREATING ACCOUNT...' : 'REGISTER OBSERVATORY ACCOUNT'}</span>
            {!loading && <ArrowRight className="w-4 h-4" />}
          </button>
        </form>

        <div className="text-center text-xs font-mono text-pace-muted border-t border-pace-border pt-4">
          Already have an account?{' '}
          <Link href="/login" className="text-pace-lime hover:underline font-bold">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
