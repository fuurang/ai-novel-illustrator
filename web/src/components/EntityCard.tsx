import { User, MapPin, Box } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EntityCardProps {
  entity: {
    id: string
    name: string
    type: 'character' | 'scene' | 'item'
    image_url?: string
    description?: string
    image_status?: 'pending' | 'generating' | 'completed' | 'error'
  }
  onClick?: () => void
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

export default function EntityCard({ entity, onClick }: EntityCardProps) {
  const config = typeConfig[entity.type]
  const Icon = config.icon

  return (
    <div
      onClick={onClick}
      className="bg-surface border border-border rounded-xl overflow-hidden cursor-pointer transition-all duration-200 hover:border-border-hover hover:bg-elevated group"
    >
      <div className="aspect-square bg-elevated relative overflow-hidden">
        {entity.image_url ? (
          <img
            src={entity.image_url}
            alt={entity.name}
            className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Icon size={40} className="text-text-muted" />
          </div>
        )}
        <div className="absolute top-2 left-2">
          <span className={`text-xs px-2 py-0.5 rounded-full ${config.bg} ${config.color}`}>
            {config.label}
          </span>
        </div>
        {entity.image_status && entity.image_status !== 'completed' && (
          <div className="absolute top-2 right-2">
            <span className={`text-xs ${statusColors[entity.image_status] || ''}`}>
              {entity.image_status === 'generating' ? '生成中' : entity.image_status === 'error' ? '失败' : '待生成'}
            </span>
          </div>
        )}
      </div>
      <div className="p-3">
        <div className="text-sm font-medium text-text-primary truncate">{entity.name}</div>
        {entity.description && (
          <div className="text-xs text-text-muted mt-1 line-clamp-2">{entity.description}</div>
        )}
      </div>
    </div>
  )
}
