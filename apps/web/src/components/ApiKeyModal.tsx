'use client';

import { useState } from 'react';
import { Copy, Check, ShieldAlert, Key, Lock } from 'lucide-react';

interface ApiKeyModalProps {
  apiKeyData: { name: string; key_prefix: string; raw_key: string } | null;
  onClose: () => void;
}

export function ApiKeyModal({ apiKeyData, onClose }: ApiKeyModalProps) {
  const [copied, setCopied] = useState(false);

  if (!apiKeyData) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKeyData.raw_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-pace-surface border border-pace-border w-full max-w-lg rounded-2xl p-6 shadow-2xl space-y-5 relative overflow-hidden">
        {/* Glow Accent Top Bar */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-pace-amber via-pace-lime to-pace-lavender" />

        <div className="flex items-center space-x-3 text-pace-amber">
          <div className="w-10 h-10 rounded-xl bg-pace-amber/10 border border-pace-amber/30 flex items-center justify-center">
            <ShieldAlert className="w-5 h-5 text-pace-amber" />
          </div>
          <div>
            <h3 className="font-bold text-lg text-white">Save Ingestion Key</h3>
            <p className="text-xs text-pace-muted font-mono">CRITICAL SECURITY CREDENTIAL</p>
          </div>
        </div>

        <p className="text-xs text-pace-muted leading-relaxed">
          Here is your new project ingestion key. <strong className="text-white">This key will only be displayed once.</strong> Store it securely in your environment variables or secret manager.
        </p>

        <div className="bg-pace-bg border border-pace-border rounded-xl p-4 flex items-center justify-between font-mono text-sm shadow-inner">
          <span className="text-pace-lime select-all overflow-x-auto whitespace-nowrap mr-3 font-bold">{apiKeyData.raw_key}</span>
          <button
            onClick={handleCopy}
            className="bg-pace-surface hover:bg-pace-surfaceHover border border-pace-border text-white px-3.5 py-2 rounded-lg flex items-center space-x-1.5 text-xs transition font-mono font-bold"
          >
            {copied ? <Check className="w-4 h-4 text-pace-emerald" /> : <Copy className="w-4 h-4" />}
            <span>{copied ? 'COPIED' : 'COPY'}</span>
          </button>
        </div>

        <div className="bg-pace-amber/10 border border-pace-amber/20 p-3.5 rounded-xl text-xs text-pace-amber leading-normal flex items-start space-x-2">
          <Lock className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>Pace stores only a cryptographic salted HMAC-SHA256 hash of this key. If lost, you will need to generate a new key from System Settings.</span>
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={onClose}
            className="bg-pace-lime hover:bg-pace-accentHover text-pace-bg text-xs font-mono font-bold px-5 py-2.5 rounded-xl transition shadow-lg shadow-pace-lime/20"
          >
            DONE & SAVED KEY →
          </button>
        </div>
      </div>
    </div>
  );
}
