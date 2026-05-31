import { AlertCircle, Image, Loader2, Play, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { api } from '@/api/client'
import { useProjectStore } from '@/stores/projectStore'

export default function ImageGenerationPanel() {
  const { currentProject } = useProjectStore()
  const [generating, setGenerating] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!currentProject || generating) return
    setGenerating(true)
    setMessage('')
    setError('')
    try {
      const result = await api.images.generate(currentProject.id)
      const counts = result?.result
      if (counts && typeof counts === 'object') {
        setMessage(
          `生成完成：角色 ${counts.characters?.length || 0}，场景 ${counts.scenes?.length || 0}，物品 ${counts.items?.length || 0}`
        )
      } else {
        setMessage(result?.message || '图片生成完成')
      }
    } catch (e: any) {
      setError(e.message || '图片生成失败')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="p-4">
      <h3 className="font-semibold text-text-primary text-base mb-4 flex items-center gap-2">
        <Image size={16} className="text-accent" />
        图片生成
      </h3>

      <div className="rounded-lg border border-border bg-base p-3 text-xs text-text-muted leading-relaxed mb-3">
        生图会读取当前项目的出图对象和绘图指令。没有绘图指令时，需要先到 AI 工作台生成角色、场景、物品的绘图指令并写回。
      </div>

      <button
        onClick={handleGenerate}
        disabled={generating || !currentProject}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-accent text-white hover:bg-accent/90 disabled:opacity-50"
      >
        {generating ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
        {generating ? '生成中...' : '生成项目图片'}
      </button>

      <button
        onClick={() => window.location.reload()}
        className="mt-2 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-elevated text-text-secondary hover:text-text-primary"
      >
        <RefreshCw size={14} />
        刷新图集
      </button>

      {message && (
        <div className="mt-3 rounded-lg border border-success/30 bg-success/10 p-3 text-xs text-success">
          {message}
        </div>
      )}

      {error && (
        <div className="mt-3 rounded-lg border border-error/30 bg-error/10 p-3 text-xs text-error flex items-start gap-2">
          <AlertCircle size={14} className="shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
