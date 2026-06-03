import {
  Box,
  Eye,
  Info,
  Loader2,
  Lock,
  MapPin,
  RefreshCw,
  Trash2,
  Unlock,
  User,
} from 'lucide-react'
import type { KeyboardEvent, MouseEvent } from 'react'
import { cn } from '@/lib/utils'

export type EntityViewMode = 'small' | 'large' | 'details'

interface EntityCardProps {
  entity: {
    id: string
    name: string
    type: 'character' | 'scene' | 'item'
    image_url?: string
    locked_image_url?: string
    image_locked?: boolean
    description?: string
    image_status?: 'pending' | 'generating' | 'completed' | 'error'
    first_appearance_chapter?: number
    chapter_range?: string
    drawing_prompt?: string
    negative_prompt?: string
    attributes?: Record<string, any>
  }
  selected?: boolean
  onSelectChange?: (selected: boolean) => void
  onClick?: () => void
  onGenerate?: () => void
  onToggleLock?: (locked: boolean) => void
  onInspect?: () => void
  onDelete?: () => void
  viewMode?: EntityViewMode
}

const typeConfig = {
  character: { label: '角色', icon: User, color: 'text-blue-400', bg: 'bg-blue-400/10' },
  scene: { label: '场景', icon: MapPin, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  item: { label: '物品', icon: Box, color: 'text-amber-400', bg: 'bg-amber-400/10' },
}

const statusColors: Record<string, string> = {
  pending: 'text-text-muted',
  generating: 'text-warning animate-pulse',
  completed: 'text-success',
  error: 'text-error',
}

export default function EntityCard({
  entity,
  selected = false,
  onSelectChange,
  onClick,
  onGenerate,
  onToggleLock,
  onInspect,
  onDelete,
  viewMode = 'large',
}: EntityCardProps) {
  const config = typeConfig[entity.type]
  const Icon = config.icon
  const displayName = entity.name?.trim() || '未命名出图对象'
  const attributeDescription =
    typeof entity.attributes?.visual_description === 'string'
      ? entity.attributes.visual_description
      : entity.type === 'character'
      ? [
          entity.attributes?.appearance?.face,
          entity.attributes?.appearance?.hair,
          entity.attributes?.appearance?.body,
          entity.attributes?.clothing?.default,
          entity.attributes?.personality,
        ]
          .filter((item) => typeof item === 'string' && item.trim() && !item.includes('原文未提及'))
          .join('；')
      : ''
  const displayDescription = entity.description?.trim() || attributeDescription.trim()
  const drawingPrompt = entity.drawing_prompt?.trim()
  const negativePrompt = entity.negative_prompt?.trim()
  const isGenerating = entity.image_status === 'generating'
  const hasPrompt = Boolean(drawingPrompt)
  const hasImage = Boolean(entity.image_url)
  const isLocked = Boolean(entity.image_locked)
  const chapterLabel = entity.chapter_range
    ? `第 ${entity.chapter_range} 章`
    : entity.first_appearance_chapter
    ? `第 ${entity.first_appearance_chapter} 章`
    : ''
  const promptStatus = hasPrompt ? '有绘图指令' : '缺少绘图指令'
  const generateLabel = hasImage ? '重抽' : '生成'

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onClick?.()
    }
  }

  const stopClick = (event: MouseEvent) => {
    event.stopPropagation()
  }

  const handleGenerateClick = (event: MouseEvent) => {
    event.stopPropagation()
    onGenerate?.()
  }

  const handleLockClick = (event: MouseEvent) => {
    event.stopPropagation()
    onToggleLock?.(!isLocked)
  }

  const SelectionCheck = ({ compact = false }: { compact?: boolean }) =>
    onSelectChange ? (
      <label
        className={cn(
          'inline-flex items-center justify-center rounded-md border border-border bg-surface/95 text-text-muted hover:text-text-primary cursor-pointer transition-colors',
          selected && 'border-accent bg-accent/15 text-accent',
          compact ? 'h-7 w-7' : 'h-8 w-8'
        )}
        onClick={stopClick}
        title={selected ? '取消选择' : '选择出图对象'}
      >
        <input
          type="checkbox"
          checked={selected}
          onChange={(event) => onSelectChange(event.target.checked)}
          className="h-3.5 w-3.5 accent-orange-500"
        />
      </label>
    ) : null

  const PromptPreview = ({ compact = false }: { compact?: boolean }) => (
    <div className={cn('relative w-full', compact ? 'mt-1' : 'mt-2')} onClick={stopClick}>
      {!compact && (
        <div className="flex items-center justify-between gap-2 mb-0.5">
          <div className="text-[11px] text-text-muted">绘图指令</div>
        </div>
      )}
      {drawingPrompt ? (
        <div
          className={cn(
            'peer rounded-md border border-success/25 bg-success/5 text-text-secondary cursor-help',
            compact ? 'px-2 py-1 text-[11px] line-clamp-1' : 'px-2 py-2 text-xs line-clamp-2'
          )}
          title={drawingPrompt}
        >
          {drawingPrompt}
        </div>
      ) : (
        <div
          className={cn(
            'rounded-md border border-warning/30 bg-warning/10 text-warning',
            compact ? 'px-2 py-1 text-[11px]' : 'px-2 py-1.5 text-xs'
          )}
        >
          暂无绘图指令
        </div>
      )}
      {drawingPrompt && (
        <div className="pointer-events-none absolute left-0 top-full z-50 mt-2 hidden w-[min(620px,80vw)] rounded-lg border border-border bg-surface p-3 text-xs text-text-secondary shadow-2xl peer-hover:block">
          <div className="max-h-72 overflow-y-auto whitespace-pre-wrap leading-relaxed">
            {drawingPrompt}
          </div>
          {negativePrompt && (
            <div className="mt-3 border-t border-border pt-3">
              <div className="mb-1 text-sm font-medium text-text-primary">反向指令</div>
              <div className="max-h-32 overflow-y-auto whitespace-pre-wrap leading-relaxed text-text-muted">
                {negativePrompt}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )

  const actionButtons = (compact = false) => (
    <div className={cn('flex items-center gap-1', compact && 'justify-end')}>
      {onGenerate && (
        <button
          type="button"
          title={isLocked ? '已保存，取消保存后可重抽' : generateLabel}
          disabled={isGenerating || isLocked}
          onClick={handleGenerateClick}
          className={cn(
            'inline-flex items-center justify-center gap-1 rounded-md border border-border text-xs transition-colors',
            compact ? 'h-7 px-2' : 'h-8 px-2.5',
            isLocked || isGenerating
              ? 'cursor-not-allowed text-text-muted bg-elevated/50'
              : 'text-text-secondary hover:text-text-primary hover:bg-elevated'
          )}
        >
          {isGenerating ? (
            <Loader2 size={compact ? 13 : 14} className="animate-spin" />
          ) : (
            <RefreshCw size={compact ? 13 : 14} />
          )}
          {!compact && <span>{generateLabel}</span>}
        </button>
      )}
      {onToggleLock && hasImage && (
        <button
          type="button"
          title={isLocked ? '取消保存' : '保存这张图'}
          disabled={isGenerating}
          onClick={handleLockClick}
          className={cn(
            'inline-flex items-center justify-center gap-1 rounded-md border text-xs transition-colors',
            compact ? 'h-7 px-2' : 'h-8 px-2.5',
            isLocked
              ? 'border-success/35 bg-success/10 text-success hover:bg-success/15'
              : 'border-border text-text-secondary hover:text-text-primary hover:bg-elevated',
            isGenerating && 'cursor-not-allowed opacity-60'
          )}
        >
          {isLocked ? <Lock size={compact ? 13 : 14} /> : <Unlock size={compact ? 13 : 14} />}
          {!compact && <span>{isLocked ? '已保存' : '保存'}</span>}
        </button>
      )}
      {onInspect && (
        <button
          type="button"
          title="查看详情"
          onClick={(event) => {
            event.stopPropagation()
            onInspect()
          }}
          className={cn(
            'inline-flex items-center justify-center rounded-md text-text-secondary hover:text-text-primary hover:bg-elevated transition-colors',
            compact ? 'h-7 w-7' : 'h-8 w-8'
          )}
        >
          <Info size={compact ? 13 : 14} />
        </button>
      )}
      {onDelete && (
        <button
          type="button"
          title="删除出图对象"
          onClick={(event) => {
            event.stopPropagation()
            onDelete()
          }}
          className={cn(
            'inline-flex items-center justify-center rounded-md text-text-muted hover:text-error hover:bg-error/10 transition-colors',
            compact ? 'h-7 w-7' : 'h-8 w-8'
          )}
        >
          <Trash2 size={compact ? 13 : 14} />
        </button>
      )}
    </div>
  )

  if (viewMode === 'details') {
    return (
      <div
        onClick={onClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        className={cn(
          'grid grid-cols-[32px_minmax(180px,1.1fr)_88px_88px_minmax(220px,1.5fr)_112px_172px] items-center gap-3 border-b border-border px-3 py-2 text-sm cursor-pointer hover:bg-elevated focus:outline-none focus:ring-2 focus:ring-accent/30',
          selected && 'bg-accent/5'
        )}
      >
        <SelectionCheck compact />
        <div className="flex items-center gap-2 min-w-0">
          <div className="relative w-8 h-8 rounded-md bg-elevated border border-border shrink-0 flex items-center justify-center overflow-hidden">
            {entity.image_url ? (
              <img src={entity.image_url} alt={displayName} className="w-full h-full object-cover" />
            ) : (
              <Icon size={16} className="text-text-muted" />
            )}
            {isGenerating && (
              <div className="absolute inset-0 bg-surface/75 flex items-center justify-center">
                <Loader2 size={13} className="animate-spin text-accent" />
              </div>
            )}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 min-w-0">
              <div className="font-medium text-text-primary truncate">{displayName}</div>
              {isLocked && <Lock size={12} className="shrink-0 text-success" />}
            </div>
            {displayDescription && <div className="text-xs text-text-muted truncate">对象说明：{displayDescription}</div>}
          </div>
        </div>
        <span className={`w-fit text-xs px-2 py-0.5 rounded-full ${config.bg} ${config.color}`}>
          {config.label}
        </span>
        <div className="text-xs text-text-muted truncate">{chapterLabel || '-'}</div>
        <PromptPreview compact />
        <div className={cn('text-xs truncate', hasPrompt ? 'text-text-muted' : 'text-warning')}>
          {isLocked ? '已保存' : promptStatus}
        </div>
        {actionButtons(true)}
      </div>
    )
  }

  if (viewMode === 'small') {
    return (
      <div
        onClick={onClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        className={cn(
          'relative h-[128px] bg-surface border border-border rounded-lg p-2 cursor-pointer transition-all duration-200 hover:border-border-hover hover:bg-elevated group focus:outline-none focus:ring-2 focus:ring-accent/40',
          selected && 'border-accent bg-accent/5'
        )}
      >
        <div className="absolute right-2 top-2 z-20">
          <SelectionCheck compact />
        </div>
        <div className="flex items-start gap-2">
          <div className="relative w-10 h-10 rounded-md bg-elevated border border-border overflow-hidden shrink-0 flex items-center justify-center">
            {entity.image_url ? (
              <img src={entity.image_url} alt={displayName} className="w-full h-full object-cover" />
            ) : (
              <Icon size={18} className="text-text-muted" />
            )}
            {isGenerating && (
              <div className="absolute inset-0 bg-surface/75 flex items-center justify-center">
                <Loader2 size={14} className="animate-spin text-accent" />
              </div>
            )}
          </div>
          <div className="min-w-0 flex-1 pr-8">
            <div className="flex items-center gap-1.5 min-w-0">
              <div className="text-sm font-medium text-text-primary truncate">{displayName}</div>
              {isLocked && <Lock size={12} className="shrink-0 text-success" />}
            </div>
            <div className="mt-1 flex items-center gap-1.5">
              <span className={`text-[11px] px-1.5 py-0.5 rounded-full ${config.bg} ${config.color}`}>
                {config.label}
              </span>
              {chapterLabel && <span className="text-[11px] text-text-muted truncate">{chapterLabel}</span>}
            </div>
          </div>
        </div>
        <PromptPreview compact />
        <div className="absolute bottom-2 right-2 left-2 flex items-center justify-between gap-2">
          <div className="inline-flex items-center gap-1 text-[11px] text-text-muted">
            <Eye size={12} />
            <span>点击查看</span>
          </div>
          {actionButtons(true)}
        </div>
      </div>
    )
  }

  return (
    <div
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      className={cn(
        'relative h-[380px] bg-surface border border-border rounded-lg overflow-hidden cursor-pointer transition-all duration-200 hover:border-border-hover hover:bg-elevated group focus:outline-none focus:ring-2 focus:ring-accent/40',
        selected && 'border-accent bg-accent/5'
      )}
    >
      <div className="absolute right-3 top-3 z-20">
        <SelectionCheck />
      </div>
      <div className="h-full flex flex-col">
        <div className="relative h-[180px] bg-elevated border-b border-border overflow-hidden flex items-center justify-center shrink-0">
          {entity.image_url ? (
            <img
              src={entity.image_url}
              alt={displayName}
              className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
            />
          ) : (
            <Icon size={48} className="text-text-muted" />
          )}
          {isGenerating && (
            <div className="absolute inset-0 bg-surface/75 flex flex-col items-center justify-center gap-2">
              <Loader2 size={20} className="animate-spin text-accent" />
              <span className="rounded bg-surface/90 px-2 py-0.5 text-xs text-accent">图片生成中</span>
            </div>
          )}
          <div className="absolute left-3 top-3 flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full ${config.bg} ${config.color}`}>
              {config.label}
            </span>
            {chapterLabel && <span className="text-[11px] text-text-secondary bg-surface/90 px-2 py-0.5 rounded-full">{chapterLabel}</span>}
          </div>
          <div className="absolute right-14 top-3 flex items-center gap-1.5">
            {isLocked && (
              <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2 py-0.5 text-[11px] text-success">
                <Lock size={11} />
                已保存
              </span>
            )}
            <span className="inline-flex items-center gap-1 rounded-full bg-surface/90 px-2 py-0.5 text-[11px] text-text-secondary opacity-0 transition-opacity group-hover:opacity-100">
              <Eye size={11} />
              查看
            </span>
          </div>
        </div>

        <div className="flex-1 min-h-0 p-4 flex flex-col">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="text-base font-medium text-text-primary truncate">{displayName}</div>
            </div>
            {actionButtons(false)}
          </div>
          {displayDescription ? (
            <div className="mt-1 min-h-[36px]">
              <div className="text-[11px] text-text-muted">对象说明</div>
              <div className="text-xs text-text-muted line-clamp-1">{displayDescription}</div>
            </div>
          ) : !hasPrompt ? (
            <div className="text-xs text-warning mt-1 line-clamp-2 min-h-[36px]">缺少描述，建议重新整理视觉设定。</div>
          ) : (
            <div className="text-xs text-text-muted mt-1 line-clamp-2 min-h-[36px]">暂无对象说明，可直接查看下方绘图指令。</div>
          )}
          <div className="min-h-0">
            <PromptPreview />
          </div>
          {entity.image_status && entity.image_status !== 'completed' && entity.image_status !== 'generating' && (
            <div className={`text-[11px] mt-2 flex items-center gap-1 ${statusColors[entity.image_status] || ''}`}>
              {entity.image_status === 'error' ? '图片生成失败' : '待生成图片'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
