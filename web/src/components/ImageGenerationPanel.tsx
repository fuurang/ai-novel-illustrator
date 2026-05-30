import { Play, Loader2, Circle } from 'lucide-react'
import { usePipelineStore } from '@/stores/pipelineStore'
import { useProjectStore } from '@/stores/projectStore'
import { api } from '@/api/client'
import { cn } from '@/lib/utils'

const imageStages = [
  { key: 'face_anchor', label: '面部锚定图', desc: '生成角色正面特写', needChapter: false },
  { key: 'character_image', label: '角色全身图', desc: '基于锚定图生成全身图', needChapter: false },
  { key: 'scene_image', label: '场景图', desc: '生成场景背景图', needChapter: false },
  { key: 'item_image', label: '物品图', desc: '生成物品插图', needChapter: false },
]

export default function ImageGenerationPanel() {
  const { runningStage, stageProgress, stageMessage, runStage } = usePipelineStore()
  const { currentProject } = useProjectStore()

  const handleRun = (stageKey: string, needChapter: boolean) => {
    if (!currentProject || runningStage) return
    runStage(currentProject.id, stageKey, undefined)
  }

  return (
    <div className="p-4">
      <h3 className="font-semibold text-text-primary text-base mb-4">图片生成</h3>

      <div className="space-y-3">
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
                  <><Loader2 size={12} className="animate-spin" />生成中</>
                ) : (
                  <><Play size={12} />生成</>
                )}
              </button>
            </div>
          )
        })}
      </div>

      {runningStage && (
        <div className="mt-4 rounded-lg bg-accent/5 border border-accent/20 p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-accent font-medium">
              {stageMessage || `正在执行: ${runningStage}`}
            </span>
            <span className="text-xs text-text-muted">{stageProgress}%</span>
          </div>
          <div className="h-1 bg-elevated rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
              style={{ width: `${stageProgress}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
