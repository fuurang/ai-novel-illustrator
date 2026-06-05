import { Play, Loader2, Circle, MapPin, RefreshCw, ChevronDown, ChevronUp, Check, X, Wand2 } from 'lucide-react'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useProjectStore } from '@/stores/projectStore'
import { useState, useEffect } from 'react'
import { api } from '@/api/client'

const stages = [
  { key: 'preprocess', label: '整理原文', desc: '拆分章节、清洗文本', needChapter: false },
  { key: 'world_bible', label: '世界观构建', desc: '分析前几章，建立视觉锚定', needChapter: false },
  { key: 'extract', label: '识别出图对象', desc: '提取角色/场景/物品', needChapter: true },
  { key: 'merge', label: '合并重复对象', desc: '合并同名/别名对象', needChapter: false },
  { key: 'attribute', label: '整理视觉设定', desc: '补全稳定外观和阶段变化', needChapter: true },
  { key: 'prompt', label: '生成绘图指令', desc: '生成可发给生图 API 的指令', needChapter: true },
]

const extractionLevels = [
  { key: 'all', label: '全部' },
  { key: 'balanced', label: '适中' },
  { key: 'key', label: '关键' },
]

const sceneGranularityLevels = [
  { key: 'fine', label: '细', desc: '小地图/小事件，边界变化稍明显就切换' },
  { key: 'medium', label: '中', desc: '按主要剧情阶段切换' },
  { key: 'coarse', label: '粗', desc: '大地图/副本/长行动线尽量合并' },
]

interface SceneSuggestion {
  id: string
  name: string
  chapter_range: string
  chapters: number[]
  description: string
  confidence?: number
  reasoning?: string
}

const isConfirmedScene = (group: any) => group?.source === 'ai' || group?.source === 'manual'

const sceneEndChapter = (group: any) => {
  if (Array.isArray(group?.chapters) && group.chapters.length > 0) {
    return Math.max(...group.chapters.map((chapter: any) => Number(chapter) || 0))
  }
  const range = String(group?.chapter_range || '')
  const match = range.match(/(\d+)\s*-\s*(\d+)/)
  if (match) return Number(match[2]) || 0
  const single = range.match(/(\d+)/)
  return single ? Number(single[1]) || 0 : 0
}

const sceneStartChapter = (group: any) => {
  if (Array.isArray(group?.chapters) && group.chapters.length > 0) {
    return Math.min(...group.chapters.map((chapter: any) => Number(chapter) || 0))
  }
  const range = String(group?.chapter_range || '')
  const match = range.match(/(\d+)\s*-\s*(\d+)/)
  if (match) return Number(match[1]) || 0
  const single = range.match(/(\d+)/)
  return single ? Number(single[1]) || 0 : 0
}

const nextContiguousSceneStart = (groups: any[]) => {
  let cursor = 1
  const sorted = [...groups].sort((a, b) => sceneStartChapter(a) - sceneStartChapter(b))
  for (const group of sorted) {
    const start = sceneStartChapter(group)
    const end = sceneEndChapter(group)
    if (start <= cursor && cursor <= end) {
      cursor = end + 1
    } else if (start > cursor) {
      break
    }
  }
  return cursor
}

interface PipelineControlProps {
  onOpenAiWorkspace?: (options?: { task?: string; extractionLevel?: string; sceneGranularity?: string; sceneId?: string }) => void
  onAutoWorkflowComplete?: () => Promise<void> | void
  onSelectedSceneChange?: (scene: any | null) => void
}

const parseChapterRange = (value: string) => {
  const chapters: number[] = []
  String(value || '').split(',').forEach((part) => {
    const trimmed = part.trim()
    if (!trimmed) return
    const range = trimmed.match(/^(\d+)\s*-\s*(\d+)$/)
    if (range) {
      const start = Number(range[1])
      const end = Number(range[2])
      for (let chapter = start; chapter <= end; chapter += 1) chapters.push(chapter)
      return
    }
    const single = Number(trimmed)
    if (Number.isFinite(single)) chapters.push(single)
  })
  return chapters
}

const entityChapterNumbers = (entity: any) => {
  const chapters = new Set<number>()
  const add = (value: any) => {
    const num = Number(value)
    if (Number.isFinite(num) && num > 0) chapters.add(num)
  }

  ;(entity.source_quotes || []).forEach((item: any) => {
    add(typeof item === 'number' ? item : item?.chapter)
  })
  ;(entity.chapter_appearances || []).forEach((item: any) => {
    add(typeof item === 'number' ? item : item?.chapter)
  })
  ;(entity.source_chapters || []).forEach(add)
  add(entity.first_appearance_chapter)
  parseChapterRange(entity.chapter_range || '').forEach(add)

  return chapters
}

const entityInScene = (entity: any, scene: any) => {
  const sceneChapters = new Set(
    (scene?.chapters || []).map((chapter: any) => Number(chapter)).filter((chapter: number) => Number.isFinite(chapter))
  )
  if (!sceneChapters.size) {
    parseChapterRange(scene?.chapter_range || '').forEach((chapter) => sceneChapters.add(chapter))
  }
  if (!sceneChapters.size) return true
  const chapters = entityChapterNumbers(entity)
  if (!chapters.size) return false
  return [...chapters].some((chapter) => sceneChapters.has(chapter))
}

const hasVisualAttributes = (entity: any) => {
  const attrs = entity?.attributes
  if (!attrs || typeof attrs !== 'object') return false
  return JSON.stringify(attrs).replace(/[{}[\]":,\s]/g, '').length > 8
}

const taskPrefixForEntity = (entity: any) => {
  if (entity.type === 'scene') return 'scene'
  if (entity.type === 'item') return 'item'
  return 'character'
}

type AutoWorkflowPhase = 'extract' | 'attribute' | 'prompt' | 'image' | 'done'
type AutoWorkflowStatus = 'running' | 'paused' | 'failed' | 'completed'

interface AutoWorkflowCheckpoint {
  projectId: string
  sceneId: string
  sceneName?: string
  extractionLevel: string
  status: AutoWorkflowStatus
  phase: AutoWorkflowPhase
  progress: number
  message: string
  attributeDoneIds: string[]
  promptDoneIds: string[]
  imageRequestedIds: string[]
  updatedAt: number
  error?: string
}

const phaseLabels: Record<AutoWorkflowPhase, string> = {
  extract: '识别出图对象',
  attribute: '整理视觉设定',
  prompt: '生成绘图指令',
  image: '生成图片',
  done: '完成',
}

const workflowStorageKey = (projectId: string, sceneId: string) =>
  `ai-illustrator:auto-workflow:${projectId}:${sceneId}`

const loadWorkflowCheckpoint = (projectId?: string, sceneId?: string | null): AutoWorkflowCheckpoint | null => {
  if (!projectId || !sceneId || typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(workflowStorageKey(projectId, sceneId))
    if (!raw) return null
    const checkpoint = JSON.parse(raw) as AutoWorkflowCheckpoint
    if (checkpoint.projectId !== projectId || String(checkpoint.sceneId) !== String(sceneId)) return null
    return {
      ...checkpoint,
      attributeDoneIds: checkpoint.attributeDoneIds || [],
      promptDoneIds: checkpoint.promptDoneIds || [],
      imageRequestedIds: checkpoint.imageRequestedIds || [],
    }
  } catch {
    return null
  }
}

const saveWorkflowCheckpoint = (checkpoint: AutoWorkflowCheckpoint) => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(workflowStorageKey(checkpoint.projectId, checkpoint.sceneId), JSON.stringify(checkpoint))
}

const clearWorkflowCheckpoint = (projectId?: string, sceneId?: string | null) => {
  if (!projectId || !sceneId || typeof window === 'undefined') return
  window.localStorage.removeItem(workflowStorageKey(projectId, sceneId))
}

export default function PipelineControl({ onOpenAiWorkspace, onAutoWorkflowComplete, onSelectedSceneChange }: PipelineControlProps) {
  const { runningStage, stageProgress, stageMessage, runStage, setStageMessage } = usePipelineStore()
  const { currentProject } = useProjectStore()
  const [sceneGroups, setSceneGroups] = useState<any[]>([])
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)
  const [showGroupPicker, setShowGroupPicker] = useState(false)
  const [detectingGroups, setDetectingGroups] = useState(false)
  const [extractionLevel, setExtractionLevel] = useState('balanced')
  const [sceneGranularity, setSceneGranularity] = useState('medium')

  // 智能场景识别相关
  const [showSceneSegmentation, setShowSceneSegmentation] = useState(false)
  const [segmenting, setSegmenting] = useState(false)
  const [currentSuggestion, setCurrentSuggestion] = useState<SceneSuggestion | null>(null)
  const [segmentationError, setSegmentationError] = useState<string | null>(null)
  const [autoRunning, setAutoRunning] = useState(false)
  const [autoProgress, setAutoProgress] = useState(0)
  const [autoMessage, setAutoMessage] = useState('')
  const [autoCheckpoint, setAutoCheckpoint] = useState<AutoWorkflowCheckpoint | null>(null)

  useEffect(() => {
    if (!currentProject) return
    loadSceneGroups()
  }, [currentProject])

  useEffect(() => {
    if (autoRunning) return
    if (!currentProject || !selectedGroup) {
      setAutoCheckpoint(null)
      setAutoMessage('')
      setAutoProgress(0)
      return
    }

    const checkpoint = loadWorkflowCheckpoint(currentProject.id, selectedGroup)
    setAutoCheckpoint(checkpoint)
    if (checkpoint && checkpoint.status !== 'completed') {
      setAutoProgress(checkpoint.progress || 0)
      setAutoMessage(`发现上次流程停在：${phaseLabels[checkpoint.phase]}，可继续`)
    }
  }, [currentProject?.id, selectedGroup, autoRunning])

  const loadSceneGroups = async () => {
    if (!currentProject) return
    try {
      const groups = await api.sceneGroups.list(currentProject.id)
      setSceneGroups(groups)
    } catch (e) {
      console.error('加载场景分组失败', e)
    }
  }

  const handleAutoDetectGroups = async () => {
    if (!currentProject || detectingGroups) return
    setDetectingGroups(true)
    try {
      const result = await api.sceneGroups.autoDetect(currentProject.id)
      if (result.groups) {
        setSceneGroups(result.groups)
      }
    } catch (e) {
      console.error('自动检测场景失败', e)
    } finally {
      setDetectingGroups(false)
    }
  }

  // 智能分段识别一个场景
  const handleSegmentOneScene = async () => {
    if (!currentProject || segmenting) return
    setSegmenting(true)
    setSegmentationError(null)

    try {
      const result = await api.sceneGroups.segmentOne(currentProject.id, undefined, sceneGranularity)
      if (result.scene) {
        setCurrentSuggestion(result.scene)
      } else {
        setSegmentationError(result.message || '未识别到场景')
      }
    } catch (e: any) {
      setSegmentationError(e.message || '识别场景失败')
    } finally {
      setSegmenting(false)
    }
  }

  // 确认当前建议的场景
  const handleConfirmScene = async () => {
    if (!currentProject || !currentSuggestion) return

    try {
      const result = await api.sceneGroups.add(currentProject.id, currentSuggestion)
      setSceneGroups(result.groups)
      setCurrentSuggestion(null)
    } catch (e) {
      console.error('添加场景失败', e)
    }
  }

  // 跳过/修改当前建议的场景
  const handleSkipScene = () => {
    setCurrentSuggestion(null)
  }

  const confirmedSceneGroups = sceneGroups.filter(isConfirmedScene)
  const nextSceneStartChapter = nextContiguousSceneStart(confirmedSceneGroups)
  const selectedScene = selectedGroup
    ? sceneGroups.find((group) => String(group.id) === String(selectedGroup))
    : null
  const hasPendingAutoCheckpoint = Boolean(autoCheckpoint && autoCheckpoint.status !== 'completed')

  useEffect(() => {
    onSelectedSceneChange?.(selectedScene || null)
  }, [selectedScene, onSelectedSceneChange])

  const runAiAndApply = async (payload: any) => {
    const result = await api.ai.run(currentProject!.id, {
      ...payload,
      apply_result: true,
    })
    return result.run
  }

  const writeAutoCheckpoint = (patch: Partial<AutoWorkflowCheckpoint>) => {
    if (!currentProject || !selectedGroup) return null
    const previous = loadWorkflowCheckpoint(currentProject.id, selectedGroup) || autoCheckpoint
    const next: AutoWorkflowCheckpoint = {
      projectId: currentProject.id,
      sceneId: selectedGroup,
      sceneName: selectedScene?.name,
      extractionLevel,
      status: 'running',
      phase: 'extract',
      progress: 0,
      message: '',
      attributeDoneIds: [],
      promptDoneIds: [],
      imageRequestedIds: [],
      ...(previous || {}),
      ...patch,
      updatedAt: Date.now(),
    }
    saveWorkflowCheckpoint(next)
    setAutoCheckpoint(next)
    return next
  }

  const handleClearAutoCheckpoint = () => {
    if (!currentProject || !selectedGroup) return
    clearWorkflowCheckpoint(currentProject.id, selectedGroup)
    setAutoCheckpoint(null)
    setAutoProgress(0)
    setAutoMessage('')
  }

  const handleAutoIllustrateScene = async () => {
    if (!currentProject || !selectedGroup || !selectedScene || autoRunning || runningStage) return

    setAutoRunning(true)
    setAutoProgress(0)
    setAutoMessage('检查当前场景进度')
    setStageMessage('一键出图：正在检查当前场景已完成内容')
    writeAutoCheckpoint({
      status: 'running',
      phase: 'extract',
      progress: 0,
      message: '检查当前场景进度',
      error: undefined,
    })

    const sceneRef = `scene:${selectedGroup}`
    const baseRefs = ['data:world_bible', 'data:scene_groups', 'data:entities']
    const refsWithScene = ['data:world_bible', 'data:scene_groups', sceneRef, 'data:entities', 'data:prompts']

    try {
      const loadSceneEntities = async () => {
        const entityList = await api.entities.list(currentProject.id)
        return entityList.filter((entity: any) => entityInScene(entity, selectedScene))
      }

      let sceneEntities = await loadSceneEntities()
      if (!sceneEntities.length) {
        setAutoMessage('识别出图对象')
        setStageMessage('一键出图：正在识别当前场景出图对象')
        writeAutoCheckpoint({
          status: 'running',
          phase: 'extract',
          progress: 8,
          message: '识别出图对象',
        })
        await runAiAndApply({
          task: 'entity_extraction',
          extraction_level: extractionLevel,
          attachment_refs: ['data:world_bible', 'data:scene_groups', sceneRef, 'data:entities'],
        })
        sceneEntities = await loadSceneEntities()
      }

      setAutoProgress(18)
      setAutoMessage('筛选当前场景对象')
      writeAutoCheckpoint({
        status: 'running',
        phase: 'attribute',
        progress: 18,
        message: '筛选当前场景对象',
      })
      if (!sceneEntities.length) {
        throw new Error('当前场景没有可处理的出图对象，请先确认章节段是否正确。')
      }

      const attributeTargets = sceneEntities.filter((entity: any) => !hasVisualAttributes(entity))
      for (let index = 0; index < attributeTargets.length; index += 1) {
        const entity = attributeTargets[index]
        const progress = 18 + Math.round(((index + 1) / Math.max(attributeTargets.length, 1)) * 30)
        setAutoMessage(`整理视觉设定：${entity.name || entity.id}`)
        setAutoProgress(progress)
        setStageMessage(`一键出图：整理视觉设定 ${index + 1}/${attributeTargets.length}`)
        writeAutoCheckpoint({
          status: 'running',
          phase: 'attribute',
          progress,
          message: `整理视觉设定：${entity.name || entity.id}`,
        })
        const prefix = taskPrefixForEntity(entity)
        await runAiAndApply({
          task: `${prefix}_attribute`,
          entity_id: entity.id,
          attachment_refs: prefix === 'character' ? refsWithScene : [...baseRefs, sceneRef, 'data:prompts'],
        })
        const previous = loadWorkflowCheckpoint(currentProject.id, selectedGroup)
        writeAutoCheckpoint({
          attributeDoneIds: Array.from(new Set([...(previous?.attributeDoneIds || []), entity.id])),
        })
      }

      sceneEntities = await loadSceneEntities()

      const promptTargets = sceneEntities.filter((entity: any) => !entity.drawing_prompt)
      for (let index = 0; index < promptTargets.length; index += 1) {
        const entity = promptTargets[index]
        const progress = 48 + Math.round(((index + 1) / Math.max(promptTargets.length, 1)) * 30)
        setAutoMessage(`生成绘图指令：${entity.name || entity.id}`)
        setAutoProgress(progress)
        setStageMessage(`一键出图：生成绘图指令 ${index + 1}/${promptTargets.length}`)
        writeAutoCheckpoint({
          status: 'running',
          phase: 'prompt',
          progress,
          message: `生成绘图指令：${entity.name || entity.id}`,
        })
        const prefix = taskPrefixForEntity(entity)
        await runAiAndApply({
          task: `${prefix}_prompt`,
          entity_id: entity.id,
          attachment_refs: [...baseRefs, sceneRef],
        })
        const previous = loadWorkflowCheckpoint(currentProject.id, selectedGroup)
        writeAutoCheckpoint({
          promptDoneIds: Array.from(new Set([...(previous?.promptDoneIds || []), entity.id])),
        })
      }

      setAutoProgress(82)
      setAutoMessage('并发生成图片')
      setStageMessage('一键出图：正在并发生成未保存图片')
      writeAutoCheckpoint({
        status: 'running',
        phase: 'image',
        progress: 82,
        message: '并发生成图片',
      })
      sceneEntities = await loadSceneEntities()
      const imageTargets = sceneEntities
        .filter((entity: any) => !entity.image_locked && entity.drawing_prompt && !entity.image_url)
        .map((entity: any) => entity.id)

      if (imageTargets.length) {
        await api.images.generate(currentProject.id, {
          entity_ids: imageTargets,
          skip_locked: true,
        })
        writeAutoCheckpoint({
          imageRequestedIds: imageTargets,
        })
      }

      setAutoProgress(100)
      setAutoMessage(`完成：处理 ${sceneEntities.length} 个对象，生成 ${imageTargets.length} 张未保存图片`)
      setStageMessage(`一键出图完成：处理 ${sceneEntities.length} 个对象，生成 ${imageTargets.length} 张未保存图片`)
      clearWorkflowCheckpoint(currentProject.id, selectedGroup)
      setAutoCheckpoint(null)
      await onAutoWorkflowComplete?.()
    } catch (error) {
      const message = error instanceof Error ? error.message : '一键出图失败'
      setAutoMessage(message)
      setStageMessage(`一键出图失败：${message}`)
      writeAutoCheckpoint({
        status: 'failed',
        message,
        error: message,
      })
      window.alert(message)
    } finally {
      setAutoRunning(false)
    }
  }

  const handleRun = (stageKey: string, needChapter: boolean) => {
    if (!currentProject || runningStage || autoRunning) return
    if (['world_bible', 'extract', 'attribute', 'prompt'].includes(stageKey)) {
      setStageMessage('这一步需要先到 AI 工作台查看发送给 API 的指令，确认或手动修改后再执行。')
      onOpenAiWorkspace?.(
        stageKey === 'extract'
          ? { task: 'entity_extraction', extractionLevel, sceneId: selectedGroup || undefined }
          : undefined
      )
      return
    }
    let chapterIndices: number[] | undefined
    if (needChapter && selectedGroup) {
      const group = sceneGroups.find((g) => g.id === selectedGroup)
      if (group && group.chapters) {
        chapterIndices = group.chapters
      }
    }
    if (needChapter && !chapterIndices) {
      return
    }
    runStage(
      currentProject.id,
      stageKey,
      chapterIndices,
      stageKey === 'extract' ? { extraction_level: extractionLevel } : undefined
    )
  }

  return (
    <div className="px-4 py-2 border-b border-border bg-surface">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 shrink-0">
          <span className="font-semibold text-text-primary text-sm">创作流程</span>
        </div>

        {/* 场景选择 */}
        <div className="relative shrink-0">
          <button
            onClick={() => setShowGroupPicker(!showGroupPicker)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-elevated rounded-md transition-colors duration-200"
          >
            <MapPin size={14} />
            <span className="truncate max-w-[120px]">
              {selectedGroup
                ? sceneGroups.find((g) => g.id === selectedGroup)?.name || '场景'
                : '选择章节段'}
            </span>
            {showGroupPicker ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showGroupPicker && (
            <div className="absolute top-full left-0 mt-1 w-72 bg-surface border border-border rounded-lg shadow-xl z-50">
              <div className="p-2 border-b border-border flex gap-2">
                <button
                  onClick={handleAutoDetectGroups}
                  disabled={detectingGroups}
                  className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-elevated hover:bg-elevated/80 transition-colors disabled:opacity-30"
                >
                  {detectingGroups ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <RefreshCw size={12} />
                  )}
                  快速检查
                </button>
                <button
                  onClick={() => {
                    setShowGroupPicker(false)
                    setShowSceneSegmentation(true)
                  }}
                  className="flex items-center gap-1 text-xs px-2 py-1 rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
                >
                  <Play size={12} />
                  智能分场景
                </button>
              </div>
              <div className="p-2 max-h-48 overflow-y-auto">
                {confirmedSceneGroups.length === 0 ? (
                  <div className="text-xs text-text-muted py-2 text-center">
                    暂无已确认章节段
                  </div>
                ) : (
                  confirmedSceneGroups.map((group) => (
                    <button
                      key={group.id}
                      onClick={() => {
                        setSelectedGroup(selectedGroup === group.id ? null : group.id)
                        setShowGroupPicker(false)
                      }}
                      className={`w-full text-left p-2 rounded-md transition-colors duration-200 text-xs ${
                        selectedGroup === group.id
                          ? 'bg-accent/10 text-accent'
                          : 'text-text-secondary hover:bg-elevated hover:text-text-primary'
                      }`}
                    >
                      <div className="font-medium truncate">{group.name}</div>
                      <div className="text-[10px] text-text-muted opacity-75">
                        {group.chapter_range || `${group.chapters?.length || 0} 章`}
                      </div>
                      {group.description && (
                        <div className="text-[10px] text-text-muted opacity-60 line-clamp-1 mt-0.5">
                          {group.description}
                        </div>
                      )}
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* 分隔线 */}
        <div className="w-px h-6 bg-border" />

        <div className="flex items-center gap-1 rounded-md bg-elevated p-0.5 shrink-0">
          {extractionLevels.map((level) => (
            <button
              key={level.key}
              onClick={() => setExtractionLevel(level.key)}
              className={`px-2.5 py-1 rounded text-xs transition-colors ${
                extractionLevel === level.key
                  ? 'bg-accent text-white'
                  : 'text-text-muted hover:text-text-primary'
              }`}
            >
              {level.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          title={selectedGroup ? '按顺序识别对象、整理设定、生成指令并出图' : '先选择章节段'}
          disabled={!selectedGroup || autoRunning || !!runningStage}
          onClick={handleAutoIllustrateScene}
          className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            !selectedGroup || autoRunning || !!runningStage
              ? 'cursor-not-allowed bg-elevated/50 text-text-muted'
              : 'bg-accent text-white hover:bg-accent-hover'
          }`}
        >
          {autoRunning ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
          {hasPendingAutoCheckpoint ? '继续一键出图' : '一键出图当前场景'}
        </button>

        {hasPendingAutoCheckpoint && !autoRunning && (
          <button
            type="button"
            title="只清除本场景的一键流程记录，不删除已生成内容"
            onClick={handleClearAutoCheckpoint}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-text-muted hover:bg-elevated hover:text-text-primary transition-colors"
          >
            <X size={12} />
            清除记录
          </button>
        )}

        {/* 流水线步骤 */}
        <div className="flex items-center gap-2 flex-1 overflow-x-auto py-1">
          {stages.map((s) => {
            const isRunning = runningStage === s.key
            const needsSelection = s.needChapter && !selectedGroup

            return (
              <button
                key={s.key}
                onClick={() => handleRun(s.key, s.needChapter)}
                disabled={!!runningStage || needsSelection}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 whitespace-nowrap ${
                  isRunning
                    ? 'bg-accent text-white'
                    : needsSelection
                    ? 'text-text-muted/30 cursor-not-allowed'
                    : 'text-text-secondary hover:bg-elevated hover:text-text-primary'
                }`}
              >
                {isRunning ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Circle size={12} />
                )}
                <span>{s.label}</span>
              </button>
            )
          })}
        </div>

        {/* 运行状态 */}
        {(runningStage || autoRunning) && (
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-32 h-1.5 bg-elevated rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-300 ease-out"
                style={{ width: `${autoRunning ? autoProgress : stageProgress}%` }}
              />
            </div>
            <span className="text-xs text-text-muted">{autoRunning ? autoProgress : stageProgress}%</span>
          </div>
        )}
      </div>

      {autoMessage && (
        <div className={`mt-1 text-xs ${autoRunning ? 'text-accent' : autoProgress === 100 ? 'text-success' : 'text-text-muted'}`}>
          {autoMessage}
        </div>
      )}

      {/* 智能分段弹窗 */}
      {showSceneSegmentation && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
          <div className="bg-surface rounded-xl p-5 w-[500px] max-w-[90vw] border border-border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-text-primary">智能场景分段</h3>
              <button
                onClick={() => {
                  setShowSceneSegmentation(false)
                  setCurrentSuggestion(null)
                  setSegmentationError(null)
                }}
                className="p-1.5 rounded-md hover:bg-elevated text-text-muted"
              >
                <X size={18} />
              </button>
            </div>

            {/* 已识别的场景 */}
            <div className="mb-4">
              <div className="text-xs text-text-muted mb-2">
                已确认 {confirmedSceneGroups.length} 个场景，下一次将从第 {nextSceneStartChapter} 章开始
              </div>
              {confirmedSceneGroups.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {confirmedSceneGroups.slice(-12).map((g) => (
                    <span
                      key={g.id}
                      className="px-2 py-0.5 bg-elevated rounded text-xs text-text-secondary"
                    >
                      {g.chapter_range}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="mb-4 rounded-lg border border-border bg-base p-3">
              <div className="text-xs font-medium text-text-primary mb-2">分场景粒度</div>
              <div className="grid grid-cols-3 gap-1 rounded-lg bg-elevated p-1">
                {sceneGranularityLevels.map((level) => (
                  <button
                    key={level.key}
                    type="button"
                    onClick={() => setSceneGranularity(level.key)}
                    className={`px-2 py-1.5 rounded-md text-xs transition-colors ${
                      sceneGranularity === level.key
                        ? 'bg-accent text-white'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                    title={level.desc}
                  >
                    {level.label}
                  </button>
                ))}
              </div>
              <div className="mt-2 text-[11px] text-text-muted">
                {sceneGranularityLevels.find((level) => level.key === sceneGranularity)?.desc}
              </div>
              <div className="mt-1 text-[11px] text-text-muted">
                系统会从下一章开始连续关联后续章节，由 AI 判断第一个场景自然结束在哪一章。
              </div>
            </div>

            {/* 当前建议 */}
            {currentSuggestion && (
              <div className="mb-4 p-3 bg-elevated/50 rounded-lg border border-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-text-primary">
                    {currentSuggestion.name}
                  </span>
                  <span className="text-xs text-accent">{currentSuggestion.chapter_range}</span>
                </div>
                <p className="text-xs text-text-secondary mb-2">
                  {currentSuggestion.description}
                </p>
                {currentSuggestion.reasoning && (
                  <p className="text-xs text-text-muted italic">
                    分析：{currentSuggestion.reasoning}
                  </p>
                )}
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={handleConfirmScene}
                    className="flex items-center gap-1 px-3 py-1.5 bg-accent text-white rounded-md text-xs hover:bg-accent/90"
                  >
                    <Check size={12} />
                    确认
                  </button>
                  <button
                    onClick={handleSkipScene}
                    className="flex items-center gap-1 px-3 py-1.5 bg-elevated text-text-secondary rounded-md text-xs hover:bg-elevated/80"
                  >
                    <X size={12} />
                    跳过/修改
                  </button>
                </div>
              </div>
            )}

            {/* 错误提示 */}
            {segmentationError && (
              <div className="mb-4 p-3 bg-error/10 border border-error/30 rounded-lg text-xs text-error">
                {segmentationError}
              </div>
            )}

            <div className="flex justify-end gap-2">
              {!currentSuggestion && (
                <button
                  onClick={() => {
                    setShowSceneSegmentation(false)
                    setCurrentSuggestion(null)
                    setSegmentationError(null)
                    setStageMessage('智能分场景需要先到 AI 工作台查看发送给 API 的指令，确认或手动修改后再执行。')
                    onOpenAiWorkspace?.({
                      task: 'scene_segmentation',
                      sceneGranularity,
                    })
                  }}
                  disabled={segmenting}
                  className="flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-md text-sm hover:bg-accent/90 disabled:opacity-50"
                >
                  {segmenting ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      识别中...
                    </>
                  ) : (
                    <>
                      <Play size={16} />
                      去 AI 工作台生成指令
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
