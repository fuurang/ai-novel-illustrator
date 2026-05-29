import { Play, CheckCircle, Loader2, Circle, ChevronDown, ChevronUp, BookOpen } from 'lucide-react'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useProjectStore } from '@/stores/projectStore'
import { useState, useEffect } from 'react'
import { api } from '@/api/client'

const stages = [
  { key: 'preprocess', label: '文本预处理', desc: '拆分章节、清洗文本', needChapter: false },
  { key: 'world_bible', label: '世界观构建', desc: '分析前几章，建立视觉锚定', needChapter: false },
  { key: 'extract', label: '实体提取', desc: '提取角色/场景/物品', needChapter: true },
  { key: 'merge', label: '实体消歧', desc: '合并同名/别名实体', needChapter: false },
  { key: 'attribute', label: '属性构建', desc: '深度提取实体视觉属性', needChapter: true },
  { key: 'prompt', label: '提示词生成', desc: '生成中文+英文提示词', needChapter: true },
]

const imageStages = [
  { key: 'face_anchor', label: '面部锚定图', desc: '生成角色正面特写', needChapter: false },
  { key: 'character_image', label: '角色全身图', desc: '基于锚定图生成全身图', needChapter: false },
  { key: 'scene_image', label: '场景图', desc: '生成场景背景图', needChapter: false },
  { key: 'item_image', label: '物品图', desc: '生成物品插图', needChapter: false },
]

export default function PipelineControl() {
  const { runningStage, stageProgress, stageMessage, runStage } = usePipelineStore()
  const { currentProject } = useProjectStore()
  const [chapters, setChapters] = useState<any[]>([])
  const [selectedChapters, setSelectedChapters] = useState<Set<number>>(new Set())
  const [showChapterPicker, setShowChapterPicker] = useState(false)
  const [showImageStages, setShowImageStages] = useState(false)

  useEffect(() => {
    if (!currentProject) return
    api.chapters.list(currentProject.id).then((data) => {
      setChapters(data)
    }).catch(() => {})
  }, [currentProject])

  const toggleChapter = (idx: number) => {
    setSelectedChapters((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }

  const selectAll = () => {
    setSelectedChapters(new Set(chapters.map((c) => c.index ?? c.chapter_number ?? 0)))
  }

  const selectNone = () => {
    setSelectedChapters(new Set())
  }

  const selectRange = (start: number, end: number) => {
    const next = new Set(selectedChapters)
    for (let i = start; i <= end; i++) {
      next.add(i)
    }
    setSelectedChapters(next)
  }

  const handleRun = (stageKey: string, needChapter: boolean) => {
    if (!currentProject || runningStage) return
    const chapterIndices = needChapter && selectedChapters.size > 0
      ? Array.from(selectedChapters).sort((a, b) => a - b)
      : undefined
    runStage(currentProject.id, stageKey, chapterIndices)
  }

  const getChapterIdx = (ch: any) => ch.index ?? ch.chapter_number ?? 0

  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base font-semibold text-text-primary">流水线</h3>
        {chapters.length > 0 && (
          <span className="text-xs text-text-muted">
            共 {chapters.length} 章
          </span>
        )}
      </div>

      {chapters.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowChapterPicker(!showChapterPicker)}
            className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200 w-full"
          >
            <BookOpen size={14} />
            <span>
              章节选择{selectedChapters.size > 0 ? `（已选 ${selectedChapters.size} 章）` : '（未选择则分析全部）'}
            </span>
            {showChapterPicker ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showChapterPicker && (
            <div className="mt-3 border border-border rounded-lg p-3">
              <div className="flex items-center gap-2 mb-3">
                <button
                  onClick={selectAll}
                  className="text-xs px-2 py-1 rounded bg-elevated text-text-secondary hover:text-text-primary transition-colors"
                >
                  全选
                </button>
                <button
                  onClick={selectNone}
                  className="text-xs px-2 py-1 rounded bg-elevated text-text-secondary hover:text-text-primary transition-colors"
                >
                  清空
                </button>
                <span className="text-xs text-text-muted ml-auto">
                  点击选择，仅对"实体提取/属性构建/提示词生成"生效
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
                {chapters.map((ch) => {
                  const idx = getChapterIdx(ch)
                  const isSelected = selectedChapters.has(idx)
                  const isAnalyzed = ch.analyzed
                  return (
                    <button
                      key={idx}
                      onClick={() => toggleChapter(idx)}
                      className={`text-xs px-2 py-1 rounded transition-colors duration-200 ${
                        isSelected
                          ? 'bg-accent text-white'
                          : isAnalyzed
                          ? 'bg-success/10 text-success border border-success/30'
                          : 'bg-elevated text-text-secondary hover:text-text-primary'
                      }`}
                      title={ch.title || ch.name || `第${idx}章`}
                    >
                      {idx}
                      {isAnalyzed && '✓'}
                    </button>
                  )
                })}
              </div>
              {selectedChapters.size > 0 && (
                <div className="mt-2 text-xs text-text-muted">
                  已选: {Array.from(selectedChapters).sort((a, b) => a - b).map((i) => `第${i}章`).join('、')}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="space-y-2">
        {stages.map((s) => {
          const isRunning = runningStage === s.key
          return (
            <div
              key={s.key}
              className="flex items-center justify-between p-3 rounded-lg border border-border hover:border-border-hover transition-colors duration-200"
            >
              <div className="flex items-center gap-3 min-w-0">
                {isRunning ? (
                  <Loader2 size={16} className="text-accent animate-spin shrink-0" />
                ) : (
                  <Circle size={16} className="text-text-muted shrink-0" />
                )}
                <div className="min-w-0">
                  <div className="text-sm text-text-primary font-medium">{s.label}</div>
                  <div className="text-xs text-text-muted">{s.desc}</div>
                </div>
              </div>
              <button
                onClick={() => handleRun(s.key, s.needChapter)}
                disabled={!!runningStage}
                className="flex items-center gap-1.5 bg-accent/10 text-accent rounded-lg px-3 py-1.5 text-xs font-medium hover:bg-accent/20 transition-colors duration-200 disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
              >
                {isRunning ? (
                  <>
                    <Loader2 size={12} className="animate-spin" />
                    运行中
                  </>
                ) : (
                  <>
                    <Play size={12} />
                    执行
                  </>
                )}
              </button>
            </div>
          )
        })}
      </div>

      {runningStage && (
        <div className="mt-4 p-3 rounded-lg bg-accent/5 border border-accent/20">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-accent font-medium">
              {stageMessage || `正在执行: ${runningStage}`}
            </span>
            <span className="text-xs text-text-muted">{stageProgress}%</span>
          </div>
          <div className="h-1.5 bg-elevated rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
              style={{ width: `${stageProgress}%` }}
            />
          </div>
        </div>
      )}

      <div className="mt-4 border-t border-border pt-4">
        <button
          onClick={() => setShowImageStages(!showImageStages)}
          className="flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary transition-colors duration-200 w-full"
        >
          {showImageStages ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          图片生成
        </button>

        {showImageStages && (
          <div className="mt-3 space-y-2">
            {imageStages.map((s) => {
              const isRunning = runningStage === s.key
              return (
                <div
                  key={s.key}
                  className="flex items-center justify-between p-3 rounded-lg border border-border hover:border-border-hover transition-colors duration-200"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {isRunning ? (
                      <Loader2 size={16} className="text-emerald-400 animate-spin shrink-0" />
                    ) : (
                      <Circle size={16} className="text-text-muted shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className="text-sm text-text-primary font-medium">{s.label}</div>
                      <div className="text-xs text-text-muted">{s.desc}</div>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRun(s.key, false)}
                    disabled={!!runningStage}
                    className="flex items-center gap-1.5 bg-emerald-400/10 text-emerald-400 rounded-lg px-3 py-1.5 text-xs font-medium hover:bg-emerald-400/20 transition-colors duration-200 disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
                  >
                    {isRunning ? (
                      <>
                        <Loader2 size={12} className="animate-spin" />
                        生成中
                      </>
                    ) : (
                      <>
                        <Play size={12} />
                        生成
                      </>
                    )}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
