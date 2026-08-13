'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { Project } from '../lib/types';
import { paceApi } from '../lib/api';

interface ProjectContextType {
  projects: Project[];
  selectedProject: Project | null;
  setSelectedProject: (project: Project) => void;
  isLoading: boolean;
  error: string | null;
  refreshProjects: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProjectState] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const setSelectedProject = (project: Project) => {
    setSelectedProjectState(project);
    if (typeof window !== 'undefined') {
      localStorage.setItem('pace_active_project_id', project.id);
    }
  };

  const refreshProjects = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await paceApi.getProjects();
      setProjects(data);

      if (data.length > 0) {
        const savedId = typeof window !== 'undefined' ? localStorage.getItem('pace_active_project_id') : null;
        const matching = savedId ? data.find(p => p.id === savedId) : null;
        setSelectedProjectState(matching || data[0]);
      } else {
        setSelectedProjectState(null);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch projects');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshProjects();
  }, []);

  return (
    <ProjectContext.Provider
      value={{
        projects,
        selectedProject,
        setSelectedProject,
        isLoading,
        error,
        refreshProjects,
      }}
    >
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
}
