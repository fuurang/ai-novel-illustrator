import { X, Image, FileText, BookOpen, Quote } from 'lucide-react'
import { useEffect } from 'react'
import { cn } from '@/lib/utils'

interface EntityDrawerProps {
  entity: {
    id: string
    name: string
    type: 'character' | 'scene' | 'item'
    image_url?: string
    description?: string
    prompt?: string
    attributes?: Record<string, string>
    chapter_appearances?: Array<{
      chapter: number
      appearance_note?: string
      clothing_override?: string
      source_quote?: string
    }>
    chapter_range?: string
  } | null
  open: boolean
  onClose: () => void
}

const typeLabels: Record<string, string> = {
  character: '角色',
  scene: '场景',
  item: '物品',
}

export default function EntityDrawer({ entity, open, onClose }: EntityDrawerProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  if (!entity) return null

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40 transition-opacity duration-200"
          onClick={onClose}
        />
      )}
      <div
        className={cn(
          'fixed top-0 right-0 h-full w-[420px] bg-surface border-l border-border z-50 transition-transform duration-300 ease-out flex flex-col',
          open ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div>
            <h3 className="text-lg font-semibold text-text-primary">{entity.name}</h3>
            <span className="text-xs text-text-muted">{typeLabels[entity.type] || entity.type}</span>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-elevated text-text-secondary transition-colors duration-200"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {entity.image_url && (
            <div className="rounded-xl overflow-hidden border border-border">
              <img
                src={entity.image_url}
                alt={entity.name}
                className="w-full object-cover"
              />
            </div>
          )}

          {!entity.image_url && (
            <div className="aspect-video bg-elevated rounded-xl border border-border flex items-center justify-center">
              <div className="text-center text-text-muted">
                <Image size={32} className="mx-auto mb-2 opacity-50" />
                <span className="text-xs">暂无图片</span>
              </div>
            </div>
          )}

          {entity.description && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <FileText size={14} className="text-text-muted" />
                <span className="text-xs text-text-muted font-medium">描述</span>
              </div>
              <p className="text-sm text-text-secondary leading-relaxed">
                {entity.description}
              </p>
            </div>
          )}

          {entity.attributes && Object.keys(entity.attributes).length > 0 && (
            <div>
              <span className="text-xs text-text-muted font-medium">属性</span>
              <div className="mt-2 space-y-2">
                {Object.entries(entity.attributes).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-start gap-2 text-sm"
                  >
                    <span className="text-text-muted shrink-0">{key}:</span>
                    <span className="text-text-secondary">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {entity.prompt && (
            <div>
              <span className="text-xs text-text-muted font-medium">提示词</span>
              <div className="mt-2 bg-elevated rounded-lg border border-border p-3">
                <p className="text-xs font-mono text-text-secondary leading-relaxed whitespace-pre-wrap">
                  {entity.prompt}
                </p>
              </div>
            </div>
          )}

          {entity.type === 'scene' && entity.chapter_range && (
            <div>
              <span className="text-xs text-text-muted font-medium">出现章节范围</span>
              <div className="mt-2 flex items-center gap-2 text-sm text-text-secondary">
                <BookOpen size={14} className="text-text-muted" />
                第{entity.chapter_range}章
              </div>
            </div>
          )}

          {entity.chapter_appearances && entity.chapter_appearances.length > 0 && (
            <div>
              <span className="text-xs text-text-muted font-medium">章节变化</span>
              <div className="mt-3 relative pl-5">
                <div className="absolute left-[7px] top-1 bottom-1 w-px bg-border" />
                {entity.chapter_appearances.map((appearance, idx) => (
                  <div key={idx} className="relative pb-4 last:pb-0">
                    <div className="absolute left-[-13px] top-1.5 w-3 h-3 rounded-full bg-accent border-2 border-surface" />
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-accent">
                          第{appearance.chapter}章
                        </span>
                      </div>
                      {appearance.appearance_note && (
                        <p className="text-xs text-text-secondary leading-relaxed">
                          {appearance.appearance_note}
                        </p>
                      )}
                      {appearance.clothing_override && (
                        <div className="text-xs text-text-secondary">
                          <span className="text-text-muted">服装：</span>
                          {appearance.clothing_override}
                        </div>
                      )}
                      {appearance.source_quote && (
                        <div className="flex items-start gap-1.5 bg-elevated rounded-md p-2 border border-border">
                          <Quote size={10} className="text-text-muted shrink-0 mt-0.5" />
                          <p className="text-[11px] text-text-muted italic leading-relaxed">
                            {appearance.source_quote}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}


