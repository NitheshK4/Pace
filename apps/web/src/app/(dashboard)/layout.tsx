'use client';

import { useState, useEffect } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { Navbar } from '@/components/Navbar';
import { CreateProjectModal } from '@/components/CreateProjectModal';
import { ApiKeyModal } from '@/components/ApiKeyModal';
import { ProjectProvider, useProject } from '@/context/ProjectContext';

function DashboardContent({ children }: { children: React.ReactNode }) {
  const { selectedProject, setSelectedProject, refreshProjects } = useProject();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newApiKeyData, setNewApiKeyData] = useState<any>(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && !localStorage.getItem('pace_token')) {
      window.location.href = '/login';
    }
  }, []);

  const handleProjectCreated = (project: any, initialKey: any) => {
    setIsCreateOpen(false);
    void refreshProjects();
    if (project && project.id) {
      setSelectedProject(project);
    }
    if (initialKey && initialKey.raw_key) {
      setNewApiKeyData(initialKey);
    }
  };

  return (
    <div className="flex min-h-screen bg-pace-bg text-pace-text">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar
          selectedProjectId={selectedProject?.id || null}
          onSelectProject={(id) => {}}
          onOpenCreateProject={() => setIsCreateOpen(true)}
        />
        <main className="flex-1 p-8 overflow-y-auto">{children}</main>
      </div>

      <CreateProjectModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onSuccess={handleProjectCreated}
      />

      <ApiKeyModal
        apiKeyData={newApiKeyData}
        onClose={() => setNewApiKeyData(null)}
      />
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProjectProvider>
      <DashboardContent>{children}</DashboardContent>
    </ProjectProvider>
  );
}
