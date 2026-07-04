import type {
  AiAttachmentsResponse,
  AiPrepareResponse,
  AiRequestPayload,
  AiRunResponse,
  AiRunsResponse,
  AiTasksResponse,
  ApiMessageResponse,
  ApiRecord,
  AppearanceUpdateRequest,
  AutoIllustrationStartRequest,
  AutoIllustrationStatus,
  ChapterDetailResponse,
  ChaptersResponse,
  DeleteImageResponse,
  EntitiesResponse,
  Entity,
  EntityBulkDeleteResponse,
  EntityDeleteResponse,
  EntityUpdateRequest,
  EntityUpdateResponse,
  GenerateImagesOptions,
  GenerateImagesResponse,
  GenerateSingleImageResponse,
  ImageItem,
  ImagesResponse,
  LockImageResponse,
  PipelineRunOptions,
  PipelineStartResponse,
  Project,
  ProjectsResponse,
  PromptListItem,
  PromptTemplate,
  SceneGroup,
  SceneGroupInput,
  SceneGroupsResponse,
  SceneSegmentationResponse,
  SettingsData,
  TestConnectionRequest,
  WorldBible,
} from '@/api/types'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'
const ASSET_BASE = API_BASE.replace(/\/api\/?$/, '')

function normalizeAssetUrl(url?: string | null) {
  if (!url) return url
  if (/^https?:\/\//i.test(url)) return url
  if (url.startsWith('/output/') || url.startsWith('/legacy-output/')) return `${ASSET_BASE}${url}`
  return url
}

function normalizeEntity(entity: Entity): Entity {
  return {
    ...entity,
    image_url: normalizeAssetUrl(entity.image_url),
    locked_image_url: normalizeAssetUrl(entity.locked_image_url),
  }
}

function normalizeImageItem(img: ImageItem): ImageItem {
  return {
    ...img,
    id: img.id || img.path || img.url || img.filename,
    path: img.path || img.url,
    url: normalizeAssetUrl(img.path || img.url),
    name: img.filename || img.name,
  }
}

function errorMessageFromPayload(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== 'object') return fallback
  const record = payload as ApiRecord
  const detail = record.detail || record.message
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)
  return fallback
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers)
  if (!(options?.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    if (!body.trim()) {
      throw new Error(res.statusText || '请求失败')
    }
    try {
      throw new Error(errorMessageFromPayload(JSON.parse(body), res.statusText || '请求失败'))
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new Error(body)
      }
      throw error
    }
  }

  if (res.status === 204 || res.headers.get('Content-Length')?.trim() === '0') {
    return undefined as T
  }

  const body = await res.text()
  if (!body.trim()) {
    return undefined as T
  }

  return JSON.parse(body) as T
}

export const api = {
  prompts: {
    list: async () => {
      const res = await request<PromptListItem[]>('/prompts')
      return res || []
    },
    get: (name: string) => request<PromptTemplate>(`/prompts/${name}`),
    update: (name: string, data: { system_prompt: string; user_prompt: string }) =>
      request<ApiMessageResponse>(`/prompts/${name}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },
  projects: {
    list: async () => {
      const res = await request<ProjectsResponse>('/projects')
      return res.projects || []
    },
    get: (id: string) => request<Project>(`/projects/${id}`),
    create: (file: File, name: string) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', name)
      return request<Project>('/projects', {
        method: 'POST',
        body: formData,
      })
    },
    delete: (id: string) => request<void>(`/projects/${id}`, { method: 'DELETE' }),
  },
  pipeline: {
    run: (projectId: string, options?: PipelineRunOptions) =>
      request<PipelineStartResponse>(`/projects/${projectId}/pipeline`, {
        method: 'POST',
        body: JSON.stringify(options || {}),
      }),
    runStage: (projectId: string, stage: string, chapterIndices?: number[], options?: PipelineRunOptions) =>
      request<PipelineStartResponse>(`/projects/${projectId}/pipeline`, {
        method: 'POST',
        body: JSON.stringify({
          stages: [stage],
          chapter_indices: chapterIndices || undefined,
          ...(options || {}),
        }),
      }),
    status: (projectId: string) =>
      new EventSource(`${API_BASE}/projects/${projectId}/pipeline/status`),
  },
  autoIllustration: {
    start: (projectId: string, data: AutoIllustrationStartRequest) =>
      request<AutoIllustrationStatus>(`/projects/${projectId}/auto-illustration/start`, {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }),
    pause: (projectId: string) =>
      request<AutoIllustrationStatus>(`/projects/${projectId}/auto-illustration/pause`, {
        method: 'POST',
      }),
    resume: (projectId: string) =>
      request<AutoIllustrationStatus>(`/projects/${projectId}/auto-illustration/resume`, {
        method: 'POST',
      }),
    stop: (projectId: string) =>
      request<AutoIllustrationStatus>(`/projects/${projectId}/auto-illustration/stop`, {
        method: 'POST',
      }),
    status: (projectId: string) =>
      request<AutoIllustrationStatus>(`/projects/${projectId}/auto-illustration/status`),
    events: (projectId: string) =>
      new EventSource(`${API_BASE}/projects/${projectId}/auto-illustration/events`),
  },
  chapters: {
    list: async (projectId: string, chapter?: number) => {
      const params = chapter !== undefined ? `?chapter=${chapter}` : ''
      const res = await request<ChaptersResponse>(
        `/projects/${projectId}/chapters${params}`
      )
      return res.chapters || []
    },
    getDetail: (projectId: string, chapterNumber: number) =>
      request<ChapterDetailResponse>(`/projects/${projectId}/chapters/${chapterNumber}`),
  },
  sceneGroups: {
    list: async (projectId: string) => {
      const res = await request<SceneGroupsResponse>(
        `/projects/${projectId}/scene-groups`
      )
      return res.groups || []
    },
    autoDetect: (projectId: string) =>
      request<SceneGroupsResponse>(`/projects/${projectId}/scene-groups/auto-detect`, {
        method: 'POST',
      }),
    update: (projectId: string, groups: SceneGroup[]) =>
      request<SceneGroupsResponse>(`/projects/${projectId}/scene-groups`, {
        method: 'PUT',
        body: JSON.stringify({ groups }),
      }),
    segmentOne: (projectId: string, startChapter?: number, granularity: string = 'medium') =>
      request<SceneSegmentationResponse>(`/projects/${projectId}/scene-groups/segment-one`, {
        method: 'POST',
        body: JSON.stringify({ start_chapter: startChapter, granularity }),
      }),
    add: (projectId: string, group: SceneGroupInput) =>
      request<SceneGroupsResponse>(`/projects/${projectId}/scene-groups/add`, {
        method: 'POST',
        body: JSON.stringify(group),
      }),
  },
  ai: {
    tasks: async (projectId: string) => {
      const res = await request<AiTasksResponse>(`/projects/${projectId}/ai/tasks`)
      return res.tasks || []
    },
    attachments: async (projectId: string) => {
      const res = await request<AiAttachmentsResponse>(`/projects/${projectId}/ai/attachments`)
      return res.attachments || []
    },
    attachmentContent: (projectId: string, ref: string) =>
      request<ApiRecord>(`/projects/${projectId}/ai/attachment-content`, {
        method: 'POST',
        body: JSON.stringify({ ref }),
      }),
    runs: async (projectId: string, limit = 30) => {
      const res = await request<AiRunsResponse>(`/projects/${projectId}/ai/runs?limit=${limit}`)
      return res.runs || []
    },
    prepare: (projectId: string, data: AiRequestPayload) =>
      request<AiPrepareResponse>(`/projects/${projectId}/ai/prepare`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    run: (projectId: string, data: AiRequestPayload) =>
      request<AiRunResponse>(`/projects/${projectId}/ai/run`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    apply: (projectId: string, runId: string) =>
      request<AiRunResponse>(`/projects/${projectId}/ai/apply`, {
        method: 'POST',
        body: JSON.stringify({ run_id: runId }),
      }),
    deleteRun: (projectId: string, runId: string) =>
      request<ApiMessageResponse>(`/projects/${projectId}/ai/runs/${runId}`, {
        method: 'DELETE',
      }),
  },
  entities: {
    list: async (projectId: string, type?: string) => {
      const res = await request<EntitiesResponse>(
        `/projects/${projectId}/entities${type ? `?type=${type}` : ''}`
      )
      return (res.entities || []).map(normalizeEntity)
    },
    get: (projectId: string, entityId: string) =>
      request<Entity>(`/projects/${projectId}/entities/${entityId}`).then(normalizeEntity),
    update: (projectId: string, entityId: string, data: EntityUpdateRequest) =>
      request<EntityUpdateResponse>(`/projects/${projectId}/entities/${entityId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (projectId: string, entityId: string) =>
      request<EntityDeleteResponse>(`/projects/${projectId}/entities/${entityId}`, {
        method: 'DELETE',
      }),
    bulkDelete: (projectId: string, entityIds: string[]) =>
      request<EntityBulkDeleteResponse>(`/projects/${projectId}/entities/bulk-delete`, {
        method: 'POST',
        body: JSON.stringify({ entity_ids: entityIds }),
      }),
    updateAppearance: (projectId: string, entityId: string, data: AppearanceUpdateRequest) =>
      request<EntityUpdateResponse>(`/projects/${projectId}/entities/${entityId}/appearance`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },
  worldBible: {
    get: (projectId: string) => request<WorldBible>(`/projects/${projectId}/world-bible`),
    update: (projectId: string, worldBible: WorldBible) =>
      request<ApiMessageResponse>(`/projects/${projectId}/world-bible`, {
        method: 'PUT',
        body: JSON.stringify({ world_bible: worldBible }),
      }),
  },
  images: {
    list: async (projectId: string) => {
      const res = await request<ImagesResponse>(
        `/projects/${projectId}/images`
      )
      return (res.images || []).map(normalizeImageItem)
    },
    generate: (projectId: string, options?: GenerateImagesOptions) =>
      request<GenerateImagesResponse>(`/projects/${projectId}/generate`, {
        method: 'POST',
        body: JSON.stringify(options || {}),
      }),
    generateSingle: (projectId: string, entityId: string) =>
      request<GenerateSingleImageResponse>(`/projects/${projectId}/generate/${entityId}`, { method: 'POST' }),
    lock: (projectId: string, entityId: string, locked: boolean) =>
      request<LockImageResponse>(`/projects/${projectId}/images/${entityId}/lock`, {
        method: 'POST',
        body: JSON.stringify({ locked }),
      }),
    delete: (projectId: string, path: string) =>
      request<DeleteImageResponse>(`/projects/${projectId}/images`, {
        method: 'DELETE',
        body: JSON.stringify({ path }),
      }),
  },
  settings: {
    get: () => request<SettingsData>('/settings'),
    update: (data: SettingsData) =>
      request<ApiMessageResponse>('/settings', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    testConnection: (data?: TestConnectionRequest) =>
      request<ApiMessageResponse>('/settings/test-connection', {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }),
  },
}
