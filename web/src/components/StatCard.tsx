import { type LucideIcon } from 'lucide-react'

interface StatCardProps {
  icon: LucideIcon
  value: number | string
  label: string
  color?: string
}

export default function StatCard({ icon: Icon, value, label, color = 'text-accent' }: StatCardProps) {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 transition-all duration-200 hover:border-border-hover">
      <div className="flex items-center gap-3">
        <div className={`${color} p-2.5 rounded-lg bg-elevated`}>
          <Icon size={20} />
        </div>
        <div>
          <div className="text-2xl font-semibold text-text-primary">{value}</div>
          <div className="text-xs text-text-muted">{label}</div>
        </div>
      </div>
    </div>
  )
}
