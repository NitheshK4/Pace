'use client';

import { useState, useEffect } from 'react';
import { apiFetch } from '@/lib/api';
import { useProject } from '@/context/ProjectContext';
import { Plus, FolderGit2, LogOut, ChevronDown, RefreshCw } from 'lucide-react';

interface NavbarProps {
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onOpenCreateProject: () => void;
}

export function Navbar({ selectedProjectId, onSelectProject, onOpenCreateProject }: NavbarProps) {
  const { projects, selectedProject, setSelectedProject, refreshProjects } = useProject();
  const [userEmail, setUserEmail] = useState<string>('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    fetchUser();
  }, []);

  const fetchUser = async () => {
    try {
      const user = await apiFetch<{ email: string }>('/auth/me');
      setUserEmail(user.email);
    } catch {
      // fallback
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refreshProjects();
    setTimeout(() => setIsRefreshing(false), 500);
  };

  const handleLogout = () => {
    localStorage.removeItem('pace_token');
    localStorage.removeItem('pace_active_project_id');
    window.location.href = '/login';
  };

  return (
    <header className="h-16 bg-pace-surface border-b border-pace-border px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Project Switcher */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2 text-xs font-mono text-pace-muted uppercase tracking-wider">
          <FolderGit2 className="w-4 h-4 text-pace-lime" />
          <span>Active Project:</span>
        </div>

        <div className="relative flex items-center space-x-2">
          <select
            value={selectedProject?.id || ''}
            onChange={(e) => {
              const p = projects.find(proj => proj.id === e.target.value);
              if (p) setSelectedProject(p);
            }}
            className="bg-pace-bg border border-pace-border text-white text-xs font-mono font-bold rounded-lg px-3 py-1.5 focus:outline-none focus:border-pace-lime appearance-none pr-8 cursor-pointer shadow-inner"
          >
            {projects.length === 0 && <option value="">No projects found</option>}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-pace-muted absolute right-2.5 pointer-events-none" />
        </div>

        <button
          onClick={onOpenCreateProject}
          className="bg-pace-bg border border-pace-border hover:border-pace-lime text-white text-xs px-3 py-1.5 rounded-lg flex items-center space-x-1.5 font-medium transition shadow-sm"
        >
          <Plus className="w-3.5 h-3.5 text-pace-lime" />
          <span>New Project</span>
        </button>
      </div>

      {/* Center / Right Telemetry Status & User Profile */}
      <div className="flex items-center space-x-5 text-xs font-mono">
        <div className="hidden sm:flex items-center space-x-2 bg-pace-bg border border-pace-border px-3 py-1.5 rounded-lg text-pace-muted">
          <span className="w-2 h-2 rounded-full bg-pace-emerald animate-pulse" />
          <span>SYSTEM HEALTH:</span>
          <span className="text-pace-emerald font-bold">OPERATIONAL</span>
        </div>

        <button
          onClick={handleRefresh}
          className="text-pace-muted hover:text-white transition p-1.5 rounded-lg hover:bg-pace-bg border border-transparent hover:border-pace-border"
          title="Refresh Projects & Telemetry"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-pace-lime' : ''}`} />
        </button>

        <div className="flex items-center space-x-3 pl-2 border-l border-pace-border">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded-full bg-pace-bg border border-pace-lavender/40 text-pace-lavender font-mono font-bold text-xs flex items-center justify-center">
              {userEmail ? userEmail[0].toUpperCase() : 'U'}
            </div>
            <span className="text-pace-text font-medium hidden md:inline">{userEmail || 'developer@company.com'}</span>
          </div>

          <button
            onClick={handleLogout}
            className="text-pace-muted hover:text-pace-coral transition flex items-center space-x-1 p-1.5 rounded-lg hover:bg-pace-bg"
            title="Sign out of Pace"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}
