import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, Bot, CheckCircle, Eye, FileText, Loader2, MessageSquare, Play, RefreshCw, RotateCcw } from 'lucide-react'
import { api } from '@/api/client'

interface AiWorkspaceProps {
  projectId: string
  selectedChapter?: number | null
  initialTask?: string
  initialInstruction?: string
  initialExtractionLevel?: string
  initialSceneGranularity?: string
  onInitialHandled?: () => void
}

const panelClass = 'bg-surface border border-border rounded-xl'
const inputClass =
  'w-full bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent'
const textareaClass =
  'w-full bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent resize-y'

const taskDefaults: Record<string, { needsChapter?: boolean; needsEntity?: boolean; applyable?: boolean }> = {
  entity_extraction: { needsChapter: true },
  scene_segmentation: { applyable: true },
  character_attribute: { needsEntity: true, applyable: true },
  scene_attribute: { needsEntity: true, applyable: true },
  item_attribute: { needsEntity: true, applyable: true },
  character_prompt: { needsEntity: true },
  scene_prompt: { needsEntity: true },
  item_prompt: { needsEntity: true },
  world_bible_analyze: { applyable: true },
  visual_anchoring: { applyable: true },
}

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

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre className="text-xs leading-relaxed whitespace-pre-wrap break-words bg-base border border-border rounded-lg p-3 overflow-auto max-h-[420px]">
      {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
    </pre>
  )
}

export default function AiWorkspace({
  projectId,
  selectedChapter,
  initialTask,
  initialInstruction,
  initialExtractionLevel,
  initialSceneGranularity,
  onInitialHandled,
}: AiWorkspaceProps) {
  const [tasks, setTasks] = useState<any[]>([])
  const [runs, setRuns] = useState<any[]>([])
  const [entities, setEntities] = useState<any[]>([])
  const [attachments, setAttachments] = useState<any[]>([])
  const [attachmentRefs, setAttachmentRefs] = useState<string[]>([])
  const [selectedTask, setSelectedTask] = useState('world_bible_analyze')
  const [chapterNumber, setChapterNumber] = useState<number>(selectedChapter || 1)
  const [entityId, setEntityId] = useState('')
  const [extractionLevel, setExtractionLevel] = useState('balanced')
  const [sceneGranularity, setSceneGranularity] = useState('medium')
  const [extraInstruction, setExtraInstruction] = useState('')
  const [prepared, setPrepared] = useState<any>(null)
  const [editableSystemPrompt, setEditableSystemPrompt] = useState('')
  const [editableUserPrompt, setEditableUserPrompt] = useState('')
  const [currentRun, setCurrentRun] = useState<any>(null)
  const [followupRunId, setFollowupRunId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState('')
  const [applyResult, setApplyResult] = useState(false)

  useEffect(() => {
    if (selectedChapter) setChapterNumber(selectedChapter)
  }, [selectedChapter])

  useEffect(() => {
    if (!projectId) return
    loadBaseData()
  }, [projectId])

  useEffect(() => {
    if (!initialTask && !initialInstruction) return
    if (initialTask) setSelectedTask(initialTask)
    if (initialInstruction) setExtraInstruction(initialInstruction)
    if (initialExtractionLevel) setExtractionLevel(initialExtractionLevel)
    if (initialSceneGranularity) setSceneGranularity(initialSceneGranularity)
    setPrepared(null)
    setCurrentRun(null)
    setEditableSystemPrompt('')
    setEditableUserPrompt('')
    onInitialHandled?.()
  }, [initialTask, initialInstruction, initialExtractionLevel, initialSceneGranularity, onInitialHandled])

  const selectedTaskMeta = useMemo(
    () => tasks.find((task) => task.key === selectedTask),
    [tasks, selectedTask]
  )

  const selectedRules = taskDefaults[selectedTask] || {}

  const filteredEntities = useMemo(() => {
    if (selectedTask.startsWith('character')) return entities.filter((entity) => entity.type === 'character')
    if (selectedTask.startsWith('scene_') || selectedTask === 'scene_prompt') return entities.filter((entity) => entity.type === 'scene')
    if (selectedTask.startsWith('item')) return entities.filter((entity) => entity.type === 'item')
    return entities
  }, [entities, selectedTask])

  useEffect(() => {
    if (!attachments.length) return
    if (selectedTask === 'world_bible_analyze') {
      setAttachmentRefs(attachments.some((item) => item.ref === 'file:input') ? ['file:input'] : [])
    } else if (selectedTask === 'visual_anchoring') {
      setAttachmentRefs(attachments.some((item) => item.ref === 'data:world_bible') ? ['data:world_bible'] : [])
    } else if (selectedTask === 'entity_extraction') {
      const chapterRef = `chapter:${chapterNumber || 1}`
      setAttachmentRefs(attachments.some((item) => item.ref === chapterRef) ? [chapterRef] : [])
    } else if (selectedTask === 'scene_segmentation') {
      setAttachmentRefs([])
    } else if (selectedTask.includes('attribute') || selectedTask.includes('prompt')) {
      setAttachmentRefs(['data:world_bible', 'data:entities'].filter((ref) => attachments.some((item) => item.ref === ref)))
    }
  }, [selectedTask, attachments])

  const buildPayload = () => ({
    task: selectedTask,
    chapter_number: selectedTask === 'scene_segmentation' ? undefined : chapterNumber,
    start_chapter: undefined,
    entity_id: entityId || undefined,
    extraction_level: extractionLevel,
    scene_granularity: sceneGranularity,
    extra_instruction: extraInstruction,
    attachment_refs: attachmentRefs,
    apply_result: applyResult,
    followup_run_id: followupRunId || undefined,
  })

  const loadBaseData = async () => {
    setError('')
    try {
      const [taskList, runList, entityList, attachmentList] = await Promise.all([
        api.ai.tasks(projectId),
        api.ai.runs(projectId),
        api.entities.list(projectId),
        api.ai.attachments(projectId),
      ])
      setTasks(taskList)
      setRuns(runList)
      setEntities(entityList)
      setAttachments(attachmentList)
      if (entityList.length && !entityId) setEntityId(entityList[0].id)
    } catch (e: any) {
      setError(e.message || '加载 AI 工作台失败')
    }
  }

  const toggleAttachment = (ref: string) => {
    setAttachmentRefs((current) =>
      current.includes(ref) ? current.filter((item) => item !== ref) : [...current, ref]
    )
  }

  const handlePrepare = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.ai.prepare(projectId, buildPayload())
      setPrepared(data)
      setEditableSystemPrompt(data.system_prompt || '')
      setEditableUserPrompt(data.user_prompt || '')
      setCurrentRun(null)
    } catch (e: any) {
      setError(e.message || '生成 API 指令失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRun = async () => {
    setRunning(true)
    setError('')
    try {
      let payload: any = buildPayload()
      if (!prepared) {
        const preparedData = await api.ai.prepare(projectId, payload)
        setPrepared(preparedData)
        setEditableSystemPrompt(preparedData.system_prompt || '')
        setEditableUserPrompt(preparedData.user_prompt || '')
        setError('已生成本次发送给 API 的指令，请确认或手动调整后再发送。')
        return
      }
      payload = {
        ...payload,
        system_prompt: editableSystemPrompt,
        user_prompt: editableUserPrompt,
      }
      const data = await api.ai.run(projectId, payload)
      setCurrentRun(data.run)
      setPrepared({
        task: data.run.task,
        context: data.run.context,
        attachments: data.run.attachments,
        system_prompt: data.run.system_prompt,
        user_prompt: data.run.user_prompt,
        execution_sources: data.run.execution_sources,
      })
      setEditableSystemPrompt(data.run.system_prompt || '')
      setEditableUserPrompt(data.run.user_prompt || '')
      setFollowupRunId(null)
      const runList = await api.ai.runs(projectId)
      setRuns(runList)
    } catch (e: any) {
      setError(e.message || 'AI 运行失败')
    } finally {
      setRunning(false)
    }
  }

  const handleApplyCurrent = async () => {
    if (!currentRun?.id) return
    setApplying(true)
    setError('')
    try {
      const data = await api.ai.apply(projectId, currentRun.id)
      setCurrentRun(data.run)
      const runList = await api.ai.runs(projectId)
      setRuns(runList)
    } catch (e: any) {
      setError(e.message || '应用结果失败')
    } finally {
      setApplying(false)
    }
  }

  const handleFollowup = () => {
    if (!currentRun?.id) return
    setFollowupRunId(currentRun.id)
    setSelectedTask(currentRun.task || selectedTask)
    setExtraInstruction('')
    setPrepared(null)
    setCurrentRun(null)
    setEditableSystemPrompt('')
    setEditableUserPrompt('')
  }

  const readableReport = useMemo(() => {
    const parsed = currentRun?.parsed_output
    if (!parsed || typeof parsed !== 'object') return ''

    const candidates = [
      parsed.readable_report,
      parsed.report,
      parsed.summary,
      parsed.analysis_summary,
      parsed.notes,
    ]
    const value = candidates.find((item) => typeof item === 'string' && item.trim())
    return typeof value === 'string' ? value.trim() : ''
  }, [currentRun])

  const visibleEvidence = useMemo(() => {
    const parsed = currentRun?.parsed_output
    if (!parsed || typeof parsed !== 'object') return null
    const keys = [
      'analysis',
      'reasoning',
      'notes',
      'evidence',
      'setting_evidence',
      'visual_evidence',
      'conflicts',
      'uncertainties',
      'revision_suggestions',
      'style_inference_notes',
    ]
    const picked: Record<string, unknown> = {}
    keys.forEach((key) => {
      if (parsed[key] !== undefined && key !== 'readable_report') picked[key] = parsed[key]
    })
    return Object.keys(picked).length ? picked : null
  }, [currentRun])

  return (
    <div className="h-full p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <Bot size={20} className="text-accent" />
            AI 工作台
          </h2>
          <p className="text-sm text-text-muted mt-1">选择要关联的项目文件，确认发送给 API 的指令，并用补充要求继续追问重跑。</p>
        </div>
        <button
          onClick={loadBaseData}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm bg-elevated text-text-secondary hover:text-text-primary"
        >
          <RefreshCw size={15} />
          刷新
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <div className="rounded-lg border border-border bg-base px-3 py-2">
          <div className="text-xs font-medium text-text-primary">1. 选择关联文件</div>
          <div className="text-[11px] text-text-muted mt-1">勾选原始小说、章节或项目数据，后端会自动读取。</div>
        </div>
        <div className="rounded-lg border border-border bg-base px-3 py-2">
          <div className="text-xs font-medium text-text-primary">2. 确认 API 指令</div>
          <div className="text-[11px] text-text-muted mt-1">发送前可以改写任务要求，不需要粘贴原文。</div>
        </div>
        <div className="rounded-lg border border-border bg-base px-3 py-2">
          <div className="text-xs font-medium text-text-primary">3. 执行并继续追问</div>
          <div className="text-[11px] text-text-muted mt-1">优先级：当前原文高于阶段设定，高于全局世界观。</div>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 text-sm text-error bg-error/10 border border-error/30 rounded-lg p-3">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-4 min-h-0 flex-1">
        <div className={`${panelClass} p-4 overflow-y-auto`}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">AI 任务</label>
              <select
                value={selectedTask}
                onChange={(e) => {
                  setSelectedTask(e.target.value)
                  setPrepared(null)
                  setCurrentRun(null)
                  setFollowupRunId(null)
                  setEditableSystemPrompt('')
                  setEditableUserPrompt('')
                  setApplyResult(false)
                }}
                className={inputClass}
              >
                {tasks.map((task) => (
                  <option key={task.key} value={task.key}>
                    {task.label}
                  </option>
                ))}
              </select>
              {selectedTaskMeta && (
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-text-muted">{selectedTaskMeta.description}</p>
                  {selectedTaskMeta.can_apply && (
                    <p className="text-[11px] text-text-muted">支持直接写回项目数据。</p>
                  )}
                </div>
              )}
            </div>

            {selectedRules.needsChapter && (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">章节</label>
                <input
                  type="number"
                  min={1}
                  value={chapterNumber}
                  onChange={(e) => setChapterNumber(Number(e.target.value) || 1)}
                  className={inputClass}
                />
              </div>
            )}

            {selectedTask === 'entity_extraction' && (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">提取档位</label>
                <div className="grid grid-cols-3 gap-1 rounded-lg bg-elevated p-1">
                  {extractionLevels.map((level) => (
                    <button
                      key={level.key}
                      type="button"
                      onClick={() => setExtractionLevel(level.key)}
                      className={`px-2 py-1.5 rounded-md text-xs transition-colors ${
                        extractionLevel === level.key
                          ? 'bg-accent text-white'
                          : 'text-text-muted hover:text-text-primary'
                      }`}
                    >
                      {level.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {selectedTask === 'scene_segmentation' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">分场景粒度</label>
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
                  <p className="mt-1.5 text-[11px] text-text-muted">
                    {sceneGranularityLevels.find((level) => level.key === sceneGranularity)?.desc}
                  </p>
                  <p className="mt-1 text-[11px] text-text-muted">
                    系统会从当前起点连续关联后续章节，由 AI 判断第一个场景自然结束在哪一章。
                  </p>
                </div>
              </div>
            )}

            {selectedRules.needsEntity && (
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">出图对象</label>
                <select
                  value={entityId}
                  onChange={(e) => setEntityId(e.target.value)}
                  className={inputClass}
                >
                  {filteredEntities.map((entity) => (
                    <option key={entity.id} value={entity.id}>
                      {(entity.name || '未命名出图对象')} ({entity.type})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {followupRunId && (
              <div className="rounded-lg border border-accent/30 bg-accent/10 px-3 py-2 text-xs text-text-secondary">
                正在基于上一轮结果继续追问：{followupRunId}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">关联文件</label>
              <div className="max-h-48 overflow-y-auto rounded-lg border border-border bg-base p-2 space-y-1">
                {attachments.length === 0 ? (
                  <div className="text-xs text-text-muted px-2 py-3">暂无可关联文件</div>
                ) : (
                  attachments.map((attachment) => (
                    <label
                      key={attachment.ref}
                      className="flex items-start gap-2 px-2 py-1.5 rounded-md hover:bg-elevated cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={attachmentRefs.includes(attachment.ref)}
                        onChange={() => toggleAttachment(attachment.ref)}
                        className="mt-0.5 accent-orange-500"
                      />
                      <span className="min-w-0">
                        <span className="flex items-center gap-1.5 text-sm text-text-secondary">
                          <FileText size={13} className="shrink-0" />
                          <span className="truncate">{attachment.label}</span>
                        </span>
                        {attachment.description && (
                          <span className="block text-[11px] text-text-muted truncate">{attachment.description}</span>
                        )}
                      </span>
                    </label>
                  ))
                )}
              </div>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => setAttachmentRefs(attachments.map((item) => item.ref))}
                  className="text-xs text-accent hover:text-accent-hover"
                >
                  全选
                </button>
                <button
                  onClick={() => setAttachmentRefs([])}
                  className="text-xs text-text-muted hover:text-text-secondary"
                >
                  清空
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">追问 / 微调要求</label>
              <textarea
                value={extraInstruction}
                onChange={(e) => setExtraInstruction(e.target.value)}
                rows={5}
                className={textareaClass}
                placeholder="这里只写你要调整的方向即可。原始小说、章节、世界观、出图对象和绘图指令都在上方勾选关联文件，不需要粘贴原文。"
              />
            </div>

            {selectedTaskMeta?.can_apply && (
              <label className="flex items-center gap-2 text-sm text-text-secondary">
                <input
                  type="checkbox"
                  checked={applyResult}
                  onChange={(e) => setApplyResult(e.target.checked)}
                  className="accent-orange-500"
                />
                运行后直接应用到项目数据
              </label>
            )}

            <div className="flex gap-2">
              <button
                onClick={handlePrepare}
                disabled={loading || running}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-elevated text-text-secondary hover:text-text-primary disabled:opacity-50"
              >
                {loading ? <Loader2 size={15} className="animate-spin" /> : <Eye size={15} />}
                生成 API 指令
              </button>
              <button
                onClick={handleRun}
                disabled={loading || running || !prepared}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-accent text-white hover:bg-accent/90 disabled:opacity-50"
              >
                {running ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
                发送给 AI
              </button>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-border">
            <h3 className="text-sm font-semibold text-text-primary mb-3">最近记录</h3>
            <div className="space-y-2">
              {runs.length === 0 ? (
                <div className="text-xs text-text-muted">暂无 AI 调用记录</div>
              ) : (
                runs.map((run) => (
                  <button
                    key={run.id}
                    onClick={() => {
                      setCurrentRun(run)
                      setPrepared({
                        task: run.task,
                        context: run.context,
                        attachments: run.attachments,
                        system_prompt: run.system_prompt,
                        user_prompt: run.user_prompt,
                        execution_sources: run.execution_sources,
                      })
                      setSelectedTask(run.task)
                      setExtraInstruction(run.extra_instruction || '')
                      setFollowupRunId(run.followup_run_id || null)
                      setEditableSystemPrompt(run.system_prompt || '')
                      setEditableUserPrompt(run.user_prompt || '')
                      setAttachmentRefs((run.attachments || []).map((item: any) => item.ref).filter(Boolean))
                    }}
                    className="w-full text-left p-3 rounded-lg border border-border bg-base hover:border-border-hover transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm text-text-primary truncate">{run.task}</span>
                      {run.applied && <CheckCircle size={14} className="text-success shrink-0" />}
                    </div>
                    <div className="text-xs text-text-muted mt-1">{run.created_at}</div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 2xl:grid-cols-2 gap-4 min-h-0">
          <div className={`${panelClass} p-4 overflow-y-auto`}>
            <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
              <MessageSquare size={15} className="text-accent" />
              发送前确认
            </h3>
            {!prepared ? (
              <div className="text-sm text-text-muted">先点击“生成 API 指令”，确认或手动调整后再发送给 AI。项目文件会由后端读取，不需要复制正文。</div>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="text-xs text-text-muted mb-1.5">任务参数</div>
                  <JsonBlock value={prepared.context} />
                </div>
                {prepared.attachments?.length > 0 && (
                  <div>
                    <div className="text-xs text-text-muted mb-1.5">已关联文件</div>
                    <JsonBlock value={prepared.attachments.map((item: any) => ({
                      ref: item.ref,
                      label: item.label,
                      status: item.has_content ? '已关联，发送 API 时自动附带' : '已关联',
                    }))} />
                  </div>
                )}
                <div>
                  <div className="text-xs text-text-muted mb-1.5">发送给 API 的系统指令</div>
                  <textarea
                    value={editableSystemPrompt}
                    onChange={(e) => setEditableSystemPrompt(e.target.value)}
                    rows={8}
                    className={textareaClass}
                  />
                </div>
                <div>
                  <div className="text-xs text-text-muted mb-1.5">发送给 API 的用户指令</div>
                  <textarea
                    value={editableUserPrompt}
                    onChange={(e) => setEditableUserPrompt(e.target.value)}
                    rows={18}
                    className={textareaClass}
                  />
                  <div className="mt-1.5 text-[11px] text-text-muted">
                    这里显示的是引用版指令，不展开原文。发送给 AI 时，后端会自动把关联文件和章节正文附加到 API 请求里。
                  </div>
                </div>
                {prepared.execution_sources?.length > 0 && (
                  <details className="rounded-lg border border-border bg-base">
                    <summary className="cursor-pointer px-3 py-2 text-xs text-text-muted hover:text-text-secondary">
                      技术详情：本次会自动附加的关联内容
                    </summary>
                    <div className="p-3 border-t border-border">
                      <JsonBlock value={prepared.execution_sources} />
                    </div>
                  </details>
                )}
              </div>
            )}
          </div>

          <div className={`${panelClass} p-4 overflow-y-auto`}>
            <h3 className="text-sm font-semibold text-text-primary mb-3">模型输出</h3>
            {!currentRun ? (
              <div className="text-sm text-text-muted">运行后这里会显示模型原始输出和解析结果。</div>
            ) : (
              <div className="space-y-4">
                <button
                  onClick={handleFollowup}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-elevated text-text-secondary hover:text-text-primary"
                >
                  <RotateCcw size={15} />
                  基于此结果继续追问 / 微调
                </button>
                {currentRun.applied && (
                  <div className="flex items-start gap-2 text-sm text-success bg-success/10 border border-success/30 rounded-lg p-3">
                    <CheckCircle size={16} className="shrink-0 mt-0.5" />
                    <span>{currentRun.applied.message}</span>
                  </div>
                )}
                {!currentRun.applied && selectedTaskMeta?.can_apply && (
                  <button
                    onClick={handleApplyCurrent}
                    disabled={applying}
                    className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-accent text-white hover:bg-accent/90 disabled:opacity-50"
                  >
                    {applying ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle size={15} />}
                    应用当前结果到项目
                  </button>
                )}
                {readableReport ? (
                  <div>
                    <div className="text-xs text-text-muted mb-1.5">阅读版说明</div>
                    <div className="text-sm leading-relaxed whitespace-pre-wrap break-words bg-base border border-border rounded-lg p-3 text-text-secondary">
                      {readableReport}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-text-muted bg-base border border-border rounded-lg p-3">
                    本次结果没有提供阅读版说明。可以基于此结果继续追问，让 AI 补充 readable_report，并说明依据、冲突和调整建议。
                  </div>
                )}
                {visibleEvidence && (
                  <div>
                    <div className="text-xs text-text-muted mb-1.5">结构化依据 / 可调整点</div>
                    <JsonBlock value={visibleEvidence} />
                  </div>
                )}
                <details className="rounded-lg border border-border bg-base">
                  <summary className="cursor-pointer px-3 py-2 text-xs text-text-muted hover:text-text-secondary">
                    技术详情：原始输出 / 解析 JSON
                  </summary>
                  <div className="space-y-3 p-3 border-t border-border">
                    <div>
                      <div className="text-xs text-text-muted mb-1.5">原始输出</div>
                      <JsonBlock value={currentRun.raw_output} />
                    </div>
                    <div>
                      <div className="text-xs text-text-muted mb-1.5">解析结果</div>
                      <JsonBlock value={currentRun.parsed_output} />
                    </div>
                  </div>
                </details>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
