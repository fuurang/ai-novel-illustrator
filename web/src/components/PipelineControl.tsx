import { Play, Loader2, Circle, ChevronDown, ChevronUp, MapPin, RefreshCw, AlertCircle } from 'lucide-react'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useProjectStore } from '@/stores/projectStore'
import { useState, useEffect } from 'react'
import { api } from '@/api/client'
import { cn } from '@/lib/utils'

const stages = [
  { key: 'preprocess', label: '文本预处理', desc: '拆分章节、清洗文本', needChapter: false },
  { key: 'world_bible', label: '世界观构建', desc: '分析前几章，建立视觉锚定', needChapter: false },
  { key: 'extract', label: '实体提取', desc: '提取角色/场景/物品', needChapter: true },
  { key: 'merge', label: '实体消歧', desc: '合并同名/别名实体', needChapter: false },
  { key: 'attribute', label: '属性构建', desc: '深度提取实体视觉属性', needChapter: true },
  { key: 'prompt', label: '提示词生成', desc: '生成中文提示词', needChapter: true },
]

interface PipelineControlProps {
  compact?: boolean
}

export default function PipelineControl({ compact = false }: PipelineControlProps) {
  const { runningStage, stageProgress, stageMessage, runStage } = usePipelineStore()
  const { currentProject } = useProjectStore()
  const [sceneGroups, setSceneGroups] = useState<any[]>([])
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)
  const [showGroupPicker, setShowGroupPicker] = useState(false)
  const [detectingGroups, setDetectingGroups] = useState(false)

  useEffect(() => {
    if (!currentProject) return
    api.sceneGroups.list(currentProject.id).then((data) => {
      setSceneGroups(data)
    }).catch(() => {})
  }, [currentProject])

  const handleAutoDetectGroups = async () => {
    if (!currentProject || detectingGroups) return
    setDetectingGroups(true)
    try {
      const res = await api.sceneGroups.autoDetect(currentProject.id)
      setSceneGroups(res.groups || [])
    } catch {
    } finally {
      setDetectingGroups(false)
    }
  }

  const handleRun = (stageKey: string, needChapter: boolean) => {
    if (!currentProject || runningStage) return
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
    runStage(currentProject.id, stageKey, chapterIndices)
  }

  return (
    <div className="px-4 py-3 border-b border-border">
      <div className="flex items-center gap-4">
        {/* 标题 */}
        <div className="flex items-center gap-2 shrink-0">
          <h3 className="font-semibold text-text-primary text-sm">流水线</h3>
        </div>

        {/* 场景选择 */}
        <div className="relative shrink-0">
          <button
            onClick={() => setShowGroupPicker(!showGroupPicker)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-all duration-200",
              !selectedGroup 
                ? "bg-warning/10 text-warning hover:bg-warning/20 border border-dashed border-warning/30"
                : "text-text-secondary hover:text-text-primary hover:bg-elevated"
            )}
          >
            <MapPin size={12} />
            <span className="truncate max-w-[140px]">
              {selectedGroup 
                ? sceneGroups.find((g) => g.id === selectedGroup)?.name || '场景' 
                : sceneGroups.length === 0 
                  ? '先点击识别场景 →' 
                  : '请选择场景'}
            </span>
            {showGroupPicker ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          {showGroupPicker && (
            <div className="absolute top-full left-0 mt-1 w-64 bg-surface border border-border rounded-lg shadow-xl z-50">
              <div className="p-2 border-b border-border">
                <button
                  onClick={handleAutoDetectGroups}
                  disabled={detectingGroups}
                  className="flex items-center gap-1.5 w-full px-2 py-1.5 text-xs rounded bg-accent/10 text-accent hover:bg-accent/20 transition-colors disabled:opacity-30"
                >
                  {detectingGroups ? <Loader2 size={10} className="animate-spin" /> : <RefreshCw size={10} />}
                  自动识别场景
                </button>
              </div>
              <div className="p-2 max-h-48 overflow-y-auto">
                {sceneGroups.length === 0 ? (
                  <div className="text-xs text-text-muted py-2 text-center">
                    暂无场景分组
                  </div>
                ) : (
                  sceneGroups.map((group) => (
                    <button
                      key={group.id}
                      onClick={() => {
                        setSelectedGroup(selectedGroup === group.id ? null : group.id)
                        setShowGroupPicker(false)
                      }}
                      className={cn(
                        'w-full text-left px-2 py-1.5 rounded-md transition-colors duration-200 text-xs',
                        selectedGroup === group.id
                          ? 'bg-accent/10 text-accent'
                          : 'text-text-secondary hover:bg-elevated hover:text-text-primary'
                      )}
                    >
                      <div className="font-medium truncate">{group.name}</div>
                      <div className="text-[10px] text-text-muted opacity-75">
                        {group.chapter_range || `${group.chapters?.length || 0} 章`}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* 分隔线 */}
        <div className="w-px h-6 bg-border" />

        {/* 流水线步骤 */}
        <div className="flex items-center gap-2 flex-1 overflow-x-auto">
          {stages.map((s) => {
            const isRunning = runningStage === s.key
            const needsSelection = s.needChapter && !selectedGroup
            const buttonDisabled = !!runningStage || needsSelection
            
            return (
              <div key={s.key} className="relative group">
                <button
                  onClick={() => handleRun(s.key, s.needChapter)}
                  disabled={buttonDisabled}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 disabled:cursor-not-allowed whitespace-nowrap",
                    isRunning
                      ? "bg-accent text-white"
                      : needsSelection
                      ? "text-text-muted/50 cursor-not-allowed border border-dashed border-border"
                      : "text-text-secondary hover:bg-elevated hover:text-text-primary"
                  )}
                >
                  {isRunning ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : needsSelection ? (
                    <AlertCircle size={12} className="text-warning" />
                  ) : (
                    <Circle size={12} />
                  )}
                  <span>{s.label}</span>
                </button>
                
                {/* 提示信息 */}
                {needsSelection && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1.5 bg-surface border border-border rounded-md shadow-lg z-50 min-w-[180px] opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
                    <div className="text-[10px] font-medium text-text-secondary mb-0.5">
                      ⚠️ 无法执行
                    </div>
                    <div className="text-[10px] text-text-muted">
                      请先在左侧选择【场景区域】
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* 运行状态 */}
        {runningStage && (
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-32 h-1.5 bg-elevated rounded-full overflow-hidden">
              <div
                className="h-full bg-accent rounded-full transition-all duration-300 ease-out"
                style={{ width: `${stageProgress}%` }}
              />
            </div>
            <span className="text-xs text-text-muted">{stageProgress}%</span>
          </div>
        )}
      </div>
    </div>
  )
}
