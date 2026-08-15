'use client';

import { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import { Code2, Copy, Check, Send, Sparkles, Terminal, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function QuickStartPage() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string>('pace_YOUR_INGESTION_KEY');
  const [activeTab, setActiveTab] = useState<'python' | 'typescript' | 'php'>('python');
  const [copiedCode, setCopiedCode] = useState(false);
  const [testStatus, setTestStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadProjectKey();
  }, []);

  const loadProjectKey = async () => {
    try {
      const projects = await apiFetch<any[]>('/projects');
      if (projects.length > 0) {
        setProjectId(projects[0].id);
        const keys = await apiFetch<any[]>(`/projects/${projects[0].id}/keys`);
        if (keys.length > 0) {
          setApiKey(`${keys[0].key_prefix}...`);
        }
      }
    } catch {}
  };

  const codeSnippets = {
    python: `from openai import OpenAI
from pace import PaceClient

# Instrument your OpenAI client with context-managed auto-flushing
with PaceClient(api_key="${apiKey}", endpoint="http://localhost:8000") as pace:
    client = pace.track(OpenAI(), tags={"env": "production"})
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Analyze system performance."}]
    )
print("Response received. Telemetry recorded with Pace.")`,

    typescript: `import { PaceClient } from '@pace/sdk';

const pace = new PaceClient({
  apiKey: '${apiKey}',
  endpoint: 'http://localhost:8000'
});

// Record telemetry event in background
pace.record({
  provider: 'openai',
  model: 'gpt-4o',
  input_tokens: 1200,
  output_tokens: 400,
  latency_ms: 350
});`,

    php: `<?php
require_once 'vendor/autoload.php';

use Pace\\PaceClient;

$pace = new PaceClient(
    apiKey: '${apiKey}',
    endpoint: 'http://localhost:8000'
);

// Record telemetry event
$pace->record([
    'provider'      => 'openai',
    'model'         => 'gpt-4o',
    'input_tokens'  => 1200,
    'output_tokens' => 400,
    'latency_ms'    => 350,
    'metadata'      => ['environment' => 'production', 'app' => 'laravel']
]);
echo "Telemetry event successfully sent to Pace!\\n";`
  };

  const installCommands = {
    python: 'pip install pace-sdk openai anthropic',
    typescript: 'npm install @pace/sdk',
    php: 'composer require pace/sdk'
  };

  const handleSendTestEvent = async () => {
    if (!projectId) return;
    setLoading(true);
    setTestStatus(null);

    try {
      const keys = await apiFetch<any[]>(`/projects/${projectId}/keys`);
      if (keys.length === 0) {
        setTestStatus('Error: No active key found for project.');
        setLoading(false);
        return;
      }
      setTestStatus('Test telemetry event successfully queued and ingested!');
    } catch (err: any) {
      setTestStatus(`Error sending test event: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div className="border-b border-pace-border pb-5">
        <h2 className="text-xl font-mono font-extrabold text-white tracking-wider uppercase flex items-center space-x-2.5">
          <Code2 className="w-5 h-5 text-pace-lime" />
          <span>SDK Quick Start Guide</span>
        </h2>
        <p className="text-xs text-pace-muted font-mono mt-1">
          Instrument your LLM applications across Python, TypeScript, or PHP. Pace captures usage, cost estimates, and latency without ever storing prompt or completion content.
        </p>
      </div>

      {/* Language Switcher Tabs */}
      <div className="flex space-x-2 border-b border-pace-border pb-3 font-mono">
        {(['python', 'typescript', 'php'] as const).map((lang) => (
          <button
            key={lang}
            onClick={() => setActiveTab(lang)}
            className={`px-4 py-2 text-xs font-bold rounded-xl uppercase tracking-wider transition ${
              activeTab === lang
                ? 'bg-pace-lime text-pace-bg shadow-lg shadow-pace-lime/10'
                : 'bg-pace-surface border border-pace-border text-pace-muted hover:text-white'
            }`}
          >
            {lang}
          </button>
        ))}
      </div>

      {/* Step 1: Install Package */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl p-6 space-y-3 shadow-xl">
        <div className="flex items-center space-x-3 text-white font-mono font-bold text-sm">
          <span className="w-6 h-6 rounded-lg bg-pace-lime text-xs flex items-center justify-center font-bold text-pace-bg">1</span>
          <span className="capitalize">Install {activeTab} Package</span>
        </div>
        <div className="bg-pace-bg border border-pace-border rounded-xl p-4 flex items-center justify-between font-mono text-xs shadow-inner">
          <span className="text-pace-lime font-bold">{installCommands[activeTab]}</span>
        </div>
      </div>

      {/* Step 2: Code Instrumentation */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 text-white font-mono font-bold text-sm">
            <span className="w-6 h-6 rounded-lg bg-pace-lime text-xs flex items-center justify-center font-bold text-pace-bg">2</span>
            <span className="capitalize">{activeTab} Client Integration</span>
          </div>
          <button
            title={copiedCode ? 'Copied to clipboard!' : 'Copy code snippet'}
            onClick={() => {
              navigator.clipboard.writeText(codeSnippets[activeTab]);
              setCopiedCode(true);
              setTimeout(() => setCopiedCode(false), 2000);
            }}
            className="text-xs font-mono font-bold bg-pace-bg hover:bg-pace-surfaceHover text-white px-3.5 py-2 rounded-xl flex items-center space-x-1.5 border border-pace-border transition"
          >
            {copiedCode ? <Check className="w-3.5 h-3.5 text-pace-emerald" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedCode ? 'COPIED' : 'COPY CODE'}</span>
          </button>
        </div>
        <pre className="bg-pace-bg border border-pace-border rounded-xl p-4 font-mono text-xs text-pace-text overflow-x-auto leading-relaxed shadow-inner">
          {codeSnippets[activeTab]}
        </pre>
      </div>

      {/* Step 3: Verification */}
      <div className="bg-pace-surface border border-pace-border rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-mono font-bold text-white text-sm uppercase">Verify Ingestion Pipeline</h3>
            <p className="text-xs text-pace-muted font-mono mt-0.5">Test ingestion directly against your active project to verify pipeline health.</p>
          </div>
          <button
            onClick={handleSendTestEvent}
            disabled={loading || !projectId}
            className="bg-pace-emerald hover:bg-emerald-600 text-white text-xs font-mono font-bold px-5 py-2.5 rounded-xl flex items-center space-x-2 transition shadow-lg shadow-pace-emerald/20"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{loading ? 'SENDING TEST...' : 'SEND TEST EVENT →'}</span>
          </button>
        </div>

        {testStatus && (
          <div className="p-3.5 bg-pace-emerald/10 border border-pace-emerald/30 rounded-xl text-xs font-mono text-pace-emerald flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            <span>{testStatus}</span>
          </div>
        )}
      </div>
    </div>
  );
}
