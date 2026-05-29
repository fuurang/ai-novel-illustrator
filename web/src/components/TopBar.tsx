import { useNavigate, useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'

export default function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { currentProject } = useProjectStore()

  const breadcrumbs = () => {
    const items = [{ label: '工作台', path: '/' }]
    if (location.pathname.startsWith('/project/') && currentProject) {
      items.push({ label: currentProject.name, path: `/project/${currentProject.id}` })
    }
    if (location.pathname === '/settings') {
      items.push({ label: '设置', path: '/settings' })
    }
    return items
  }

  const crumbs = breadcrumbs()

  return (
    <header className="h-[56px] bg-surface border-b border-border flex items-center justify-between px-5 shrink-0">
      <div className="flex items-center gap-1.5">
        {crumbs.map((crumb, idx) => (
          <div key={crumb.path} className="flex items-center gap-1.5">
            {idx > 0 && <ChevronRight size={14} className="text-text-muted" />}
            <button
              onClick={() => navigate(crumb.path)}
              className={`text-sm transition-colors duration-200 ${
                idx === crumbs.length - 1
                  ? 'text-text-primary font-medium'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              {crumb.label}
            </button>
          </div>
        ))}
      </div>
    </header>
  )
}
