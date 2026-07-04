export type ApiRecord = Record<string, unknown>

export type ProjectStatus = 'idle' | 'running' | 'completed' | 'error'

export interface ProjectStats extends ApiRecord {
  characters: number
  scenes: number
  items: number
  images: number
}

export interface Project extends ApiRecord {
  id: string
  name: string
  novel_name: string
  status: ProjectStatus
  created_at: string
  stats: ProjectStats
}

export type EntityType = 'character' | 'scene' | 'item' | 'creature' | (string & {})

export interface SourceQuote extends ApiRecord {
  chapter?: number
  text?: string
  location?: string
}

export interface ChapterAppearance extends ApiRecord {
  chapter?: number
  context?: string
  appearance_note?: string
  clothing_override?: string
  source_quote?: string
}

export interface Entity extends ApiRecord {
  id: string
  project_id?: string
  name: string
  aliases?: string[]
  type: EntityType
  world_binding?: ApiRecord
  attributes?: ApiRecord
  source_quotes?: Array<SourceQuote | number>
  source_chapters?: Array<number | string>
  first_appearance_chapter?: number | null
  chapter_appearances?: Array<ChapterAppearance | number>
  chapter_range?: string
  chapter_images?: Record<string, string>
  created_at?: string
  image_url?: string | null
  image_status?: string | boolean
  image_locked?: boolean
  locked_image_path?: string
  locked_image_url?: string | null
  drawing_prompt?: string
  negative_prompt?: string
  prompt_id?: string
  prompt_created_at?: string
}

export interface Chapter extends ApiRecord {
  id?: string
  index?: number
  number?: number
  chapter_number?: number
  title?: string
  text?: string
  summary?: string
  analyzed?: boolean
  entity_ids?: string[]
  image_ids?: string[]
}

export type SceneGroupSource = 'ai' | 'manual' | string

export interface SceneGroup extends ApiRecord {
  id: string
  name: string
  chapter_range: string
  chapters: number[]
  description: string
  source?: SceneGroupSource
  confidence?: number
  reasoning?: string
  granularity?: string
  internal_read_rounds?: number
}

export interface SceneGroupInput {
  id: string
  name: string
  chapter_range: string
  chapters: number[]
  description: string
  confidence?: number
  reasoning?: string
  source?: SceneGroupSource
}

export interface ImageItem extends ApiRecord {
  id?: string
  path?: string
  url?: string
  name?: string
  filename?: string
  category?: string
  entity_id?: string | null
  chapters?: number[]
  chapter?: number
}

export interface PipelineStatus extends ApiRecord {
  is_running: boolean
  current_stage?: string
  current_stage_key?: string
  progress: number
  stages_completed?: string[]
  error?: string | null
}

export interface PipelineRunOptions extends ApiRecord {
  stages?: string[]
  enable_image?: boolean
  chapter_range?: string
  chapter_indices?: number[]
  extraction_level?: string
}

export interface GenerateImagesOptions extends ApiRecord {
  entity_ids?: string[]
  chapter?: number
  skip_locked?: boolean
}

export interface ImageGenerationResult extends ApiRecord {
  characters?: unknown[]
  scenes?: unknown[]
  items?: unknown[]
  errors?: string[]
}

export interface AutoIllustrationStartRequest extends ApiRecord {
  scene_granularity?: string
  extraction_level?: string
  skip_locked?: boolean
  start_chapter?: number
  max_chapters?: number
}

export type AutoIllustrationStatusValue =
  | 'idle'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'stopped'

export type AutoIllustrationPhase =
  | 'segment'
  | 'extract'
  | 'attribute'
  | 'prompt'
  | 'image'
  | 'skip'
  | 'done'

export interface AutoIllustrationFailedStep extends ApiRecord {
  id?: string
  phase?: string
  step?: string
  message?: string
  attempts?: number
  skipped?: boolean
  scene_name?: string
  entity_name?: string
  created_at?: string
}

export interface AutoIllustrationStatus extends ApiRecord {
  status: AutoIllustrationStatusValue
  scene_granularity: string
  extraction_level: string
  skip_locked?: boolean
  current_scene_id?: string
  current_scene_name?: string
  current_phase: AutoIllustrationPhase
  current_chapter: number
  last_completed_chapter: number
  total_chapters: number
  completed_scene_ids: string[]
  skipped_scene_ids: string[]
  failed_steps: AutoIllustrationFailedStep[]
  retry_counts?: Record<string, number>
  pause_requested?: boolean
  stop_requested?: boolean
  message: string
  progress: number
  updated_at?: string
}

export interface PromptListItem extends ApiRecord {
  name: string
  description: string
  has_system: boolean
  has_user: boolean
}

export interface PromptTemplate extends ApiRecord {
  name: string
  system_prompt: string
  user_prompt: string
  description: string
}

export interface ProjectsResponse {
  projects: Project[]
}

export interface ChaptersResponse {
  chapters: Chapter[]
  total: number
}

export interface ChapterDetailResponse extends ApiRecord {
  chapter: Chapter
  entities: Entity[]
  images: ImageItem[]
}

export interface SceneGroupsResponse extends ApiRecord {
  groups: SceneGroup[]
  total: number
  message?: string
}

export interface SceneSegmentationResponse extends ApiRecord {
  scene: SceneGroup | null
  analysis?: ApiRecord
  message?: string
  start_chapter?: number
  next_start_chapter?: number
}

export interface EntitiesResponse {
  entities: Entity[]
  total: number
}

export interface EntityUpdateRequest extends ApiRecord {
  name?: string
  attributes?: ApiRecord
  aliases?: string[]
}

export interface EntityUpdateResponse extends ApiRecord {
  message?: string
  entity: Entity
}

export interface EntityDeleteResponse extends ApiRecord {
  message?: string
  entity_id?: string
  deleted_prompt_count?: number
}

export interface EntityBulkDeleteResponse extends ApiRecord {
  message?: string
  deleted_count: number
  deleted_entity_ids: string[]
  deleted_prompt_count: number
  missing_entity_ids: string[]
}

export interface AppearanceUpdateRequest extends ApiRecord {
  chapter: number
  appearance_note?: string
  clothing_override?: string
}

export interface ImagesResponse {
  images: ImageItem[]
  total: number
}

export interface GenerateImagesResponse extends ApiRecord {
  message?: string
  project_id?: string
  chapter?: number | null
  result?: ImageGenerationResult | string | null
}

export interface GenerateSingleImageResponse extends ApiRecord {
  entity_id: string
  image_path?: unknown
  image_url?: string | null
  chapter?: number | null
}

export interface LockImageResponse extends ApiRecord {
  entity_id: string
  image_locked: boolean
  locked_image_path?: string
  locked_image_url?: string | null
  image_url?: string | null
}

export interface DeleteImageResponse extends ApiRecord {
  message?: string
  path?: string
  unlocked_entities?: string[]
  cleaned_chapter_refs?: number
}

export interface PipelineStartResponse extends ApiRecord {
  message?: string
  project_id: string
}

export interface AiTasksResponse {
  tasks: AiTask[]
}

export interface AiAttachmentsResponse {
  attachments: AiAttachment[]
}

export interface AiRunsResponse {
  runs: AiRun[]
}

export type AiRequestPayload = ApiRecord

export interface AiTask extends ApiRecord {
  key: string
  label?: string
  description?: string
  needs?: string[]
}

export interface AiAttachment extends ApiRecord {
  ref: string
  kind: string
  label?: string
  description?: string
  summary?: string
  preview?: string
}

export interface AiRun extends ApiRecord {
  id: string
  task?: string
  context?: ApiRecord
  attachments?: AiAttachment[]
  system_prompt?: string
  user_prompt?: string
  execution_sources?: unknown
  parsed_output?: ApiRecord
}

export interface AiPrepareResponse extends ApiRecord {
  task: string
  context?: ApiRecord
  attachments: AiAttachment[]
  system_prompt: string
  user_prompt: string
  execution_sources?: unknown
}

export interface AiRunResponse extends ApiRecord {
  run: AiRun
}

export type WorldBible = ApiRecord

export interface SettingsLlm {
  api_key?: string
  base_url?: string
  model?: string
  extraction_model?: string
  prompt_model?: string
  vision_model?: string
  provider?: string
}

export interface SettingsImageChatgpt2api {
  base_url?: string
  api_key?: string
  model?: string
}

export interface SettingsImage {
  enabled?: boolean
  backend?: string
  chatgpt2api?: SettingsImageChatgpt2api
}

export interface SettingsOutput {
  dir?: string
}

export interface SettingsData {
  llm?: SettingsLlm
  image?: SettingsImage
  output?: SettingsOutput
  world_bible?: ApiRecord
  extraction?: ApiRecord
  prompt?: ApiRecord
  face_consistency?: ApiRecord
}

export interface TestConnectionRequest {
  provider?: string
  api_key?: string
  base_url?: string
  model?: string
}

export interface ApiMessageResponse extends ApiRecord {
  message?: string
  detail?: string
  success?: boolean
}
