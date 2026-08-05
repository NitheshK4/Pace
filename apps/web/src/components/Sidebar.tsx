'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Activity, 
  Search, 
  Radio, 
  Wallet, 
  Database, 
  Code2, 
  Settings,
  ShieldCheck,
  Zap,
  Layers,
  Terminal
} from 'lucide-react';

const NAV_GROUPS = [
  {
    title: 'Telemetry Command',
    items: [
      { label: 'Overview', href: '/', icon: Activity, badge: 'Live' },
      { label: 'Live Tail', href: '/live-tail', icon: Radio, pulse: true },
      { label: 'Project Explorer', href: '/explorer', icon: Search },
    ]
  },
  {
    title: 'Cost & Governance',
    items: [
      { label: 'Budgets & Alerts', href: '/budgets', icon: Wallet },
      { label: 'Pricing Catalog', href: '/pricing', icon: Database },
    ]
  },
  {
    title: 'Developer Resources',
    items: [
      { label: 'Quick Start SDK', href: '/quickstart', icon: Code2 },
      { label: 'System & Security', href: '/settings/system', icon: Settings },
    ]
  }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-pace-surface border-r border-pace-border flex flex-col h-screen sticky top-0 z-40 select-none">
      {/* Pace Brand Mark */}
      <div className="p-5 border-b border-pace-border flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-3 group">
          <div className="w-9 h-9 rounded-xl bg-pace-bg border border-pace-lime/40 flex items-center justify-center relative shadow-lg shadow-pace-lime/10 group-hover:border-pace-lime transition-all">
            <Zap className="w-5 h-5 text-pace-lime" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-pace-lime rounded-full animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <h1 className="font-extrabold text-lg text-white tracking-wider font-mono">PACE</h1>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-pace-lime/10 text-pace-lime border border-pace-lime/30 font-bold">
                v0.1
              </span>
            </div>
            <p className="text-[10px] text-pace-muted font-mono tracking-widest uppercase">Signal Observatory</p>
          </div>
        </Link>
      </div>

      {/* Navigation Groups */}
      <nav className="flex-1 p-3.5 space-y-6 overflow-y-auto">
        {NAV_GROUPS.map((group) => (
          <div key={group.title} className="space-y-1.5">
            <h2 className="px-3 text-[10px] font-mono font-bold text-pace-mutedDark uppercase tracking-widest">
              {group.title}
            </h2>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`group relative flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-pace-surfaceHover text-white font-semibold shadow-inner border border-pace-borderLight'
                        : 'text-pace-muted hover:text-white hover:bg-pace-surfaceHover/60'
                    }`}
                  >
                    {/* Active Left Indicator Bar */}
                    {isActive && (
                      <span className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-pace-lime rounded-r-full shadow-sm shadow-pace-lime" />
                    )}

                    <div className="flex items-center space-x-2.5">
                      <Icon className={`w-4 h-4 transition-colors ${
                        isActive ? 'text-pace-lime' : 'text-pace-mutedDark group-hover:text-pace-muted'
                      }`} />
                      <span className={isActive ? 'text-white' : ''}>{item.label}</span>
                    </div>

                    {/* Item Badges */}
                    {item.pulse && (
                      <span className="flex items-center space-x-1 text-[9px] font-mono font-bold text-pace-lime bg-pace-lime/10 border border-pace-lime/30 px-1.5 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-pace-lime animate-ping" />
                        <span>LIVE</span>
                      </span>
                    )}

                    {item.badge && !item.pulse && (
                      <span className="text-[9px] font-mono font-bold text-pace-muted bg-pace-bg px-1.5 py-0.5 rounded border border-pace-border">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* System Security & Zero-Content Status Footer */}
      <div className="p-3.5 border-t border-pace-border bg-pace-bg/40">
        <div className="bg-pace-surface border border-pace-border p-3 rounded-xl space-y-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-1.5 text-pace-emerald text-[11px] font-bold">
              <ShieldCheck className="w-4 h-4" />
              <span>Zero-Content Shield</span>
            </div>
            <span className="w-2 h-2 rounded-full bg-pace-emerald animate-pulse" />
          </div>
          <p className="text-[10px] text-pace-muted font-mono leading-tight">
            Prompts, completions & provider keys are never logged or stored.
          </p>
        </div>
      </div>
    </aside>
  );
}
