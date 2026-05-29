const API_BASE = 'http://localhost:8000/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {}
  if (!(options?.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  if (options?.headers) {
    Object.assign(headers, options.headers as Record<string, string>)
  }

  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  })
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || '请求失败')
  }
  return res.json()
}

export const api = {
  projects: {
    list: async () => {
      const res = await request<{ projects: any[] }>('/projects')
      return res.projects || []
    },
    get: (id: string) => request<any>(`/projects/${id}`),
    create: (file: File, name: string) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', name)
      return request<any>('/projects', {
        method: 'POST',
        body: formData,
      })
    },
    delete: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),
  },
  pipeline: {
    run: (projectId: string, options?: any) =>
      request<any>(`/projects/${projectId}/pipeline`, {
        method: 'POST',
        body: JSON.stringify(options || {}),
      }),
    runStage: (projectId: string, stage: string, chapterIndices?: number[]) =>
      request<any>(`/projects/${projectId}/pipeline`, {
        method: 'POST',
        body: JSON.stringify({
          stages: [stage],
          chapter_indices: chapterIndices || undefined,
        }),
      }),
    status: (projectId: string) =>
      new EventSource(`${API_BASE}/projects/${projectId}/pipeline/status`),
  },
  chapters: {
    list: async (projectId: string) => {
      const res = await request<{ chapters: any[]; total: number }>(
        `/projects/${projectId}/chapters`
      )
      return res.chapters || []
    },
  },
  entities: {
    list: async (projectId: string, type?: string) => {
      const res = await request<{ entities: any[]; total: number }>(
        `/projects/${projectId}/entities${type ? `?type=${type}` : ''}`
      )
      return res.entities || []
    },
    get: (projectId: string, entityId: string) =>
      request<any>(`/projects/${projectId}/entities/${entityId}`),
    update: (projectId: string, entityId: string, data: any) =>
      request<any>(`/projects/${projectId}/entities/${entityId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },
  worldBible: {
    get: (projectId: string) => request<any>(`/projects/${projectId}/world-bible`),
  },
  images: {
    list: async (projectId: string) => {
      const res = await request<{ images: any[]; total: number }>(
        `/projects/${projectId}/images`
      )
      return (res.images || []).map((img: any) => ({
        ...img,
        url: img.path || img.url,
        name: img.filename || img.name,
      }))
    },
    generate: (projectId: string, options?: any) =>
      request<any>(`/projects/${projectId}/generate`, {
        method: 'POST',
        body: JSON.stringify(options || {}),
      }),
    generateSingle: (projectId: string, entityId: string) =>
      request<any>(`/projects/${projectId}/generate/${entityId}`, { method: 'POST' }),
  },
  settings: {
    get: () => request<any>('/settings'),
    update: (data: any) =>
      request<any>('/settings', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    testConnection: () =>
      request<any>('/settings/test-connection', { method: 'POST' }),
  },
}
