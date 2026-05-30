import { useNavigate, useLocation } from 'react-router-dom'
import { Plus, Settings, BookOpen, Loader2, Sun, Moon, MessageCircle, X, Code2 } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import { useTheme } from '@/hooks/useTheme'
import { useState } from 'react'
import UploadModal from './UploadModal'

export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { projects, currentProject, selectProject, createProject, loading } = useProjectStore()
  const { isDark, toggleTheme } = useTheme()
  const [uploadOpen, setUploadOpen] = useState(false)
  const [qqModalOpen, setQqModalOpen] = useState(false)

  const handleSelect = async (id: string) => {
    await selectProject(id)
    navigate(`/project/${id}`)
  }

  const handleCreate = async (file: File, name: string) => {
    await createProject(file, name)
    setUploadOpen(false)
  }

  return (
    <aside className="w-[240px] h-full bg-surface border-r border-border flex flex-col shrink-0">
      <div className="h-[56px] flex items-center px-4 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
            <BookOpen size={18} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-text-primary">AI 拆书生图</span>
        </div>
      </div>

      <div className="p-3">
        <button
          onClick={() => setUploadOpen(true)}
          className="w-full flex items-center justify-center gap-2 bg-accent text-white rounded-lg px-3 py-2 text-sm font-medium hover:bg-accent-hover transition-colors duration-200"
        >
          <Plus size={16} />
          新建项目
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3">
        <div className="text-xs text-text-muted px-2 mb-2">项目列表</div>
        {loading && projects.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={20} className="text-text-muted animate-spin" />
          </div>
        ) : projects.length === 0 ? (
          <div className="text-xs text-text-muted text-center py-8">
            暂无项目
          </div>
        ) : (
          <div className="space-y-1">
            {projects.map((project) => {
              const isActive = currentProject?.id === project.id || location.pathname.includes(project.id)
              return (
                <button
                  key={project.id}
                  onClick={() => handleSelect(project.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all duration-200 truncate ${
                    isActive
                      ? 'bg-elevated text-text-primary'
                      : 'text-text-secondary hover:bg-elevated hover:text-text-primary'
                  }`}
                >
                  <div className="truncate">{project.name}</div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        project.status === 'completed'
                          ? 'bg-success'
                          : project.status === 'running'
                          ? 'bg-warning animate-pulse'
                          : project.status === 'error'
                          ? 'bg-error'
                          : 'bg-text-muted'
                      }`}
                    />
                    <span className="text-xs text-text-muted">{project.novel_name}</span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>

      <div className="p-3 border-t border-border space-y-1">
        <button
          onClick={() => navigate('/prompts')}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
            location.pathname === '/prompts'
              ? 'bg-elevated text-text-primary'
              : 'text-text-secondary hover:bg-elevated hover:text-text-primary'
          }`}
        >
          <Code2 size={16} />
          提示词管理
        </button>
        <button
          onClick={() => navigate('/settings')}
          className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
            location.pathname === '/settings'
              ? 'bg-elevated text-text-primary'
              : 'text-text-secondary hover:bg-elevated hover:text-text-primary'
          }`}
        >
          <Settings size={16} />
          设置
        </button>
        <button
          onClick={toggleTheme}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-elevated hover:text-text-primary transition-colors duration-200"
        >
          {isDark ? <Sun size={16} /> : <Moon size={16} />}
          {isDark ? '亮色模式' : '暗色模式'}
        </button>
        <button
          onClick={() => setQqModalOpen(true)}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-elevated hover:text-text-primary transition-colors duration-200"
        >
          <MessageCircle size={16} />
          QQ交流群
        </button>
      </div>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleCreate}
        loading={loading}
      />

      {qqModalOpen && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setQqModalOpen(false)}>
          <div className="bg-surface rounded-xl p-6 max-w-md w-[90vw]" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">QQ 交流群</h3>
              <button
                onClick={() => setQqModalOpen(false)}
                className="p-1.5 rounded-lg hover:bg-elevated text-text-secondary"
              >
                <X size={18} />
              </button>
            </div>
            <img
              src="/qq-group.jpg"
              alt="QQ 群二维码"
              className="w-full rounded-lg mb-4"
            />
            <p className="text-sm text-text-muted text-center">
              群号：297144575
            </p>
            <a
              href="https://qm.qq.com/q/297144575"
              target="_blank"
              rel="noopener noreferrer"
              className="block mt-4 w-full bg-accent text-white rounded-lg py-2.5 text-center text-sm font-medium hover:bg-accent-hover transition-colors duration-200"
            >
              点击加入群聊
            </a>
          </div>
        </div>
      )}
    </aside>
  )
}
