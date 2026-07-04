import { Play, Loader2, Circle, MapPin, RefreshCw, ChevronDown, ChevronUp, Check, X, Wand2, Pause, Square, AlertTriangle, BookOpen } from 'lucide-react'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useProjectStore } from '@/stores/projectStore'
import { useState, useEffect, useRef } from 'react'
import { api } from '@/api/client'
import type {
  AutoIllustrationFailedStep,
  AutoIllustrationPhase,
  AutoIllustrationStatus,
  AutoIllustrationStatusValue,
  SceneGroup,
} from '@/api/types'
import { entityInScene, hasVisualAttributes, taskPrefixForEntity } from '@/lib/entityFilters'
import { extractionLevels, sceneGranularityLevels } from '@/lib/workflowOptions'

const stages = [
  { key: 'preprocess', label: '整理原文', desc: '拆分章节、清洗文本', needChapter: false },
  { key: 'world_bible', label: '世界观构建', desc: '分析前几章，建立视觉锚定', needChapter: false },
  { key: 'extract', label: '识别出图对象', desc: '提取角色/场景/物品', needChapter: true },
  { key: 'merge', label: '合并重复对象', desc: '合并同名/别名对象', needChapter: false },
  { key: 'attribute', label: '整理视觉设定', desc: '补全稳定外观和阶段变化', needChapter: true },
  { key: 'prompt', label: '生成绘图指令', desc: '生成可发给生图 API 的指令', needChapter: true },
]

type SceneSuggestion = SceneGroup

const isConfirmedScene = (group: any) => !group?.source || group.source === 'ai' || group.source === 'manual'

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

type AutoWorkflowPhase = 'extract' | 'attribute' | 'prompt' | 'image' | 'done'
type AutoWorkflowStatus = 'running' | 'paused' | 'failed' | 'completed'

type BookAutoStatus = AutoIllustrationStatusValue
type BookAutoPhase = AutoIllustrationPhase
type BookAutoFailedStep = AutoIllustrationFailedStep
type BookAutoState = AutoIllustrationStatus

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

const bookAutoPhaseLabels: Record<BookAutoPhase, string> = {
  segment: '智能分场景',
  extract: '识别出图对象',
  attribute: '补全视觉设定',
  prompt: '生成绘图指令',
  image: '生成图片',
  skip: '跳过并记录',
  done: '完成',
}

const bookAutoStatusLabels: Record<BookAutoStatus, string> = {
  idle: '未启动',
  running: '运行中',
  paused: '已暂停',
  completed: '已完成',
  failed: '异常停止',
  stopped: '已停止',
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
  const [showFullAutoDialog, setShowFullAutoDialog] = useState(false)
  const [fullAutoConfig, setFullAutoConfig] = useState({
    scene_granularity: 'medium',
    extraction_level: 'balanced',
    skip_locked: true,
  })
  const [fullAutoStatus, setFullAutoStatus] = useState<BookAutoState | null>(null)
  const [fullAutoBusy, setFullAutoBusy] = useState(false)
  const [showFullAutoFailures, setShowFullAutoFailures] = useState(false)
  const previousFullAutoStatus = useRef<BookAutoStatus | null>(null)
  const fullAutoRunning = fullAutoStatus?.status === 'running'
  const fullAutoPaused = fullAutoStatus?.status === 'paused'
  const fullAutoVisible = Boolean(fullAutoStatus && fullAutoStatus.status !== 'idle')
  const fullAutoFailures = fullAutoStatus?.failed_steps || []

  useEffect(() => {
    if (!currentProject) return
    loadSceneGroups()
  }, [currentProject])

  useEffect(() => {
    if (!currentProject) {
      setFullAutoStatus(null)
      return
    }

    let closed = false
    let source: EventSource | null = null

    const loadStatus = async () => {
      try {
        const status = await api.autoIllustration.status(currentProject.id)
        if (!closed) setFullAutoStatus(status)
      } catch (error) {
        console.error('加载全书自动出图状态失败', error)
      }
    }

    loadStatus()
    try {
      source = api.autoIllustration.events(currentProject.id)
      source.onmessage = (event) => {
        try {
          const status = JSON.parse(event.data)
          if (!closed) setFullAutoStatus(status)
        } catch {}
      }
      source.onerror = () => {
        source?.close()
        source = null
      }
    } catch (error) {
      console.error('连接全书自动出图事件失败', error)
    }

    const timer = window.setInterval(() => {
      if (!source || source.readyState === EventSource.CLOSED) {
        loadStatus()
      }
    }, 5000)

    return () => {
      closed = true
      source?.close()
      window.clearInterval(timer)
    }
  }, [currentProject?.id])

  useEffect(() => {
    const current = fullAutoStatus?.status || null
    const previous = previousFullAutoStatus.current
    if (current === 'completed' && previous !== 'completed') {
      loadSceneGroups()
      onAutoWorkflowComplete?.()
    }
    previousFullAutoStatus.current = current
  }, [fullAutoStatus?.status])

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
    if (!currentProject || segmenting || fullAutoRunning) return
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

  const handleStartFullAuto = async () => {
    if (!currentProject || fullAutoBusy || fullAutoRunning || runningStage || autoRunning) return
    setFullAutoBusy(true)
    try {
      const status = await api.autoIllustration.start(currentProject.id, fullAutoConfig)
      setFullAutoStatus(status)
      setShowFullAutoDialog(false)
      setStageMessage('全书自动出图已启动，后端会持续分场景并出图。')
    } catch (error: any) {
      window.alert(error.message || '启动全书自动出图失败')
    } finally {
      setFullAutoBusy(false)
    }
  }

  const handlePauseFullAuto = async () => {
    if (!currentProject || fullAutoBusy) return
    setFullAutoBusy(true)
    try {
      setFullAutoStatus(await api.autoIllustration.pause(currentProject.id))
    } catch (error: any) {
      window.alert(error.message || '暂停失败')
    } finally {
      setFullAutoBusy(false)
    }
  }

  const handleResumeFullAuto = async () => {
    if (!currentProject || fullAutoBusy || runningStage || autoRunning) return
    setFullAutoBusy(true)
    try {
      setFullAutoStatus(await api.autoIllustration.resume(currentProject.id))
      setStageMessage('全书自动出图已继续运行。')
    } catch (error: any) {
      window.alert(error.message || '继续失败')
    } finally {
      setFullAutoBusy(false)
    }
  }

  const handleStopFullAuto = async () => {
    if (!currentProject || fullAutoBusy) return
    const confirmed = window.confirm('停止后不会删除已生成内容；再次开始会根据已覆盖章节继续。确定停止吗？')
    if (!confirmed) return
    setFullAutoBusy(true)
    try {
      setFullAutoStatus(await api.autoIllustration.stop(currentProject.id))
      setStageMessage('已请求停止全书自动出图。')
    } catch (error: any) {
      window.alert(error.message || '停止失败')
    } finally {
      setFullAutoBusy(false)
    }
  }

  const handleAutoIllustrateScene = async () => {
    if (!currentProject || !selectedGroup || !selectedScene || autoRunning || runningStage || fullAutoRunning) return

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
    if (!currentProject || runningStage || autoRunning || fullAutoRunning) return
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
          disabled={!selectedGroup || autoRunning || !!runningStage || fullAutoRunning}
          onClick={handleAutoIllustrateScene}
          className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            !selectedGroup || autoRunning || !!runningStage || fullAutoRunning
              ? 'cursor-not-allowed bg-elevated/50 text-text-muted'
              : 'bg-accent text-white hover:bg-accent-hover'
          }`}
        >
          {autoRunning ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
          {hasPendingAutoCheckpoint ? '继续一键出图' : '一键出图当前场景'}
        </button>

        <button
          type="button"
          title="后端自动循环：分下一个场景、识别对象、生成指令并出图，直到全书完成或手动暂停"
          disabled={autoRunning || !!runningStage || fullAutoRunning}
          onClick={() => setShowFullAutoDialog(true)}
          className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
            autoRunning || !!runningStage || fullAutoRunning
              ? 'cursor-not-allowed bg-elevated/50 text-text-muted'
              : 'bg-success text-white hover:bg-success/90'
          }`}
        >
          {fullAutoRunning ? <Loader2 size={14} className="animate-spin" /> : <BookOpen size={14} />}
          全书自动出图
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
                disabled={!!runningStage || needsSelection || fullAutoRunning}
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
        {(runningStage || autoRunning || fullAutoRunning) && (
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-32 h-1.5 bg-elevated rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-300 ease-out"
                style={{ width: `${fullAutoRunning ? fullAutoStatus?.progress || 0 : autoRunning ? autoProgress : stageProgress}%` }}
              />
            </div>
            <span className="text-xs text-text-muted">
              {fullAutoRunning ? fullAutoStatus?.progress || 0 : autoRunning ? autoProgress : stageProgress}%
            </span>
          </div>
        )}
      </div>

      {autoMessage && (
        <div className={`mt-1 text-xs ${autoRunning ? 'text-accent' : autoProgress === 100 ? 'text-success' : 'text-text-muted'}`}>
          {autoMessage}
        </div>
      )}

      {/* 智能分段弹窗 */}
      {fullAutoVisible && fullAutoStatus && (
        <div className="mt-2 rounded-lg border border-border bg-base p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className={`rounded px-2 py-0.5 ${
                  fullAutoRunning
                    ? 'bg-accent/10 text-accent'
                    : fullAutoStatus.status === 'completed'
                    ? 'bg-success/10 text-success'
                    : 'bg-elevated text-text-secondary'
                }`}>
                  {bookAutoStatusLabels[fullAutoStatus.status] || fullAutoStatus.status}
                </span>
                <span className="text-text-secondary">
                  {bookAutoPhaseLabels[fullAutoStatus.current_phase] || fullAutoStatus.current_phase}
                </span>
                <span className="text-text-muted">第 {fullAutoStatus.current_chapter || 1} 章起</span>
                <span className="text-text-muted">
                  已完成到第 {fullAutoStatus.last_completed_chapter || 0}/{fullAutoStatus.total_chapters || 0} 章
                </span>
              </div>
              <div className="mt-2 h-1.5 w-full max-w-xl overflow-hidden rounded-full bg-elevated">
                <div
                  className="h-full rounded-full bg-accent transition-all duration-300"
                  style={{ width: `${Math.max(0, Math.min(100, fullAutoStatus.progress || 0))}%` }}
                />
              </div>
              <div className="mt-2 text-xs text-text-secondary line-clamp-2">
                {fullAutoStatus.current_scene_name ? `当前场景：${fullAutoStatus.current_scene_name}。` : ''}
                {fullAutoStatus.message}
              </div>
            </div>

            <div className="flex shrink-0 flex-wrap items-center gap-2">
              {fullAutoRunning && (
                <button
                  type="button"
                  onClick={handlePauseFullAuto}
                  disabled={fullAutoBusy}
                  className="inline-flex items-center gap-1 rounded-md bg-elevated px-2.5 py-1.5 text-xs text-text-secondary hover:text-text-primary disabled:opacity-50"
                >
                  <Pause size={12} />
                  暂停
                </button>
              )}
              {(fullAutoPaused || fullAutoStatus.status === 'failed' || fullAutoStatus.status === 'stopped') && (
                <button
                  type="button"
                  onClick={handleResumeFullAuto}
                  disabled={fullAutoBusy || !!runningStage || autoRunning}
                  className="inline-flex items-center gap-1 rounded-md bg-accent px-2.5 py-1.5 text-xs text-white hover:bg-accent/90 disabled:opacity-50"
                >
                  <Play size={12} />
                  继续
                </button>
              )}
              {fullAutoStatus.status !== 'completed' && fullAutoStatus.status !== 'stopped' && (
                <button
                  type="button"
                  onClick={handleStopFullAuto}
                  disabled={fullAutoBusy}
                  className="inline-flex items-center gap-1 rounded-md bg-error/10 px-2.5 py-1.5 text-xs text-error hover:bg-error/20 disabled:opacity-50"
                >
                  <Square size={12} />
                  停止
                </button>
              )}
              <button
                type="button"
                onClick={() => setShowFullAutoFailures((value) => !value)}
                className="inline-flex items-center gap-1 rounded-md bg-elevated px-2.5 py-1.5 text-xs text-text-secondary hover:text-text-primary"
              >
                <AlertTriangle size={12} />
                失败记录 {fullAutoFailures.length}
              </button>
            </div>
          </div>

          {showFullAutoFailures && (
            <div className="mt-3 max-h-44 overflow-y-auto rounded-md border border-border bg-surface p-2">
              {fullAutoFailures.length === 0 ? (
                <div className="text-xs text-text-muted">暂无失败或跳过记录</div>
              ) : (
                <div className="space-y-2">
                  {fullAutoFailures.slice(0, 20).map((item, index) => (
                    <div key={item.id || index} className="text-xs text-text-secondary">
                      <div className="font-medium text-text-primary">
                        {item.scene_name || '未命名场景'}
                        {item.entity_name ? ` / ${item.entity_name}` : ''}
                      </div>
                      <div className="mt-0.5 text-text-muted">
                        [{item.phase || item.step || 'step'}] {item.message || '失败后已跳过'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {showFullAutoDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
          <div className="bg-surface rounded-xl p-5 w-[520px] max-w-[92vw] border border-border">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold text-text-primary">全书自动出图</h3>
              <button
                type="button"
                onClick={() => setShowFullAutoDialog(false)}
                className="p-1.5 rounded-md hover:bg-elevated text-text-muted"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <div className="mb-2 text-xs font-medium text-text-primary">分场景粒度</div>
                <div className="grid grid-cols-3 gap-1 rounded-lg bg-elevated p-1">
                  {sceneGranularityLevels.map((level) => (
                    <button
                      key={level.key}
                      type="button"
                      onClick={() => setFullAutoConfig((value) => ({ ...value, scene_granularity: level.key }))}
                      className={`rounded-md px-2 py-1.5 text-xs transition-colors ${
                        fullAutoConfig.scene_granularity === level.key
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
                  后端会持续读取后续章节，由 AI 判断第一个自然场景边界。
                </div>
              </div>

              <div>
                <div className="mb-2 text-xs font-medium text-text-primary">出图对象识别档位</div>
                <div className="grid grid-cols-3 gap-1 rounded-lg bg-elevated p-1">
                  {extractionLevels.map((level) => (
                    <button
                      key={level.key}
                      type="button"
                      onClick={() => setFullAutoConfig((value) => ({ ...value, extraction_level: level.key }))}
                      className={`rounded-md px-2 py-1.5 text-xs transition-colors ${
                        fullAutoConfig.extraction_level === level.key
                          ? 'bg-accent text-white'
                          : 'text-text-muted hover:text-text-primary'
                      }`}
                    >
                      {level.label}
                    </button>
                  ))}
                </div>
              </div>

              <label className="flex items-center gap-2 text-xs text-text-secondary">
                <input
                  type="checkbox"
                  checked={fullAutoConfig.skip_locked}
                  onChange={(event) => setFullAutoConfig((value) => ({ ...value, skip_locked: event.target.checked }))}
                  className="h-4 w-4 accent-accent"
                />
                跳过已保存或已锁定图片
              </label>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowFullAutoDialog(false)}
                className="rounded-md bg-elevated px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
              >
                取消
              </button>
              <button
                type="button"
                onClick={handleStartFullAuto}
                disabled={fullAutoBusy || fullAutoRunning || !!runningStage || autoRunning}
                className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm text-white hover:bg-accent/90 disabled:opacity-50"
              >
                {fullAutoBusy ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                启动
              </button>
            </div>
          </div>
        </div>
      )}

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
