import { create } from 'zustand'
import { api } from '@/api/client'
import type { Project } from '@/api/types'

interface ProjectState {
  projects: Project[]
  currentProject: Project | null
  loading: boolean
  fetchProjects: () => Promise<void>
  selectProject: (id: string) => Promise<void>
  createProject: (file: File, name: string) => Promise<void>
  deleteProject: (id: string) => Promise<void>
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  loading: false,

  fetchProjects: async () => {
    set({ loading: true })
    try {
      const projects = await api.projects.list()
      set({ projects, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  selectProject: async (id: string) => {
    try {
      const project = await api.projects.get(id)
      set({ currentProject: project })
    } catch {
      const found = get().projects.find((p) => p.id === id)
      if (found) set({ currentProject: found })
    }
  },

  createProject: async (file: File, name: string) => {
    set({ loading: true })
    try {
      const project = await api.projects.create(file, name)
      set((state) => ({
        projects: [project, ...state.projects],
        currentProject: project,
        loading: false,
      }))
    } catch {
      set({ loading: false })
    }
  },

  deleteProject: async (id: string) => {
    try {
      await api.projects.delete(id)
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProject:
          state.currentProject?.id === id ? null : state.currentProject,
      }))
    } catch (error) {
      void error
    }
  },
}))

export type { Project }
