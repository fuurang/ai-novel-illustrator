import { useNavigate } from 'react-router-dom'
import { Upload, BookOpen, Users, MapPin, Box, ArrowRight, Clock } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import { useState, useEffect } from 'react'
import StatCard from '@/components/StatCard'
import PipelineControl from '@/components/PipelineControl'
import UploadModal from '@/components/UploadModal'

export default function Home() {
  const navigate = useNavigate()
  const { projects, currentProject, fetchProjects, selectProject, createProject, loading } = useProjectStore()
  const [uploadOpen, setUploadOpen] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  if (currentProject) {
    return (
      <div className="p-6 space-y-6 max-w-5xl">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">{currentProject.name}</h1>
          <p className="text-sm text-text-muted mt-1">{currentProject.novel_name}</p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <StatCard
            icon={Users}
            value={currentProject.stats?.characters ?? 0}
            label="角色"
            color="text-blue-400"
          />
          <StatCard
            icon={MapPin}
            value={currentProject.stats?.scenes ?? 0}
            label="场景"
            color="text-emerald-400"
          />
          <StatCard
            icon={Box}
            value={currentProject.stats?.items ?? 0}
            label="物品"
            color="text-amber-400"
          />
        </div>

        <PipelineControl />

        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="text-base font-semibold text-text-primary mb-4">快速操作</h3>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => navigate(`/project/${currentProject.id}`)}
              className="flex items-center gap-3 p-3 rounded-lg border border-border hover:border-border-hover hover:bg-elevated transition-all duration-200 text-left"
            >
              <div className="p-2 rounded-lg bg-accent/10 text-accent">
                <BookOpen size={18} />
              </div>
              <div>
                <div className="text-sm text-text-primary">查看详情</div>
                <div className="text-xs text-text-muted">浏览实体与世界观数据</div>
              </div>
            </button>
            <button
              onClick={() => navigate(`/project/${currentProject.id}?tab=gallery`)}
              className="flex items-center gap-3 p-3 rounded-lg border border-border hover:border-border-hover hover:bg-elevated transition-all duration-200 text-left"
            >
              <div className="p-2 rounded-lg bg-emerald-400/10 text-emerald-400">
                <MapPin size={18} />
              </div>
              <div>
                <div className="text-sm text-text-primary">查看图集</div>
                <div className="text-xs text-text-muted">浏览生成的图片</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex flex-col items-center justify-center py-16">
        <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-5">
          <BookOpen size={32} className="text-accent" />
        </div>
        <h1 className="text-2xl font-semibold text-text-primary mb-2">AI 拆书生图</h1>
        <p className="text-sm text-text-muted mb-8 text-center max-w-md">
          上传小说文件，自动拆解角色、场景与物品，生成精美的插画图集
        </p>
        <button
          onClick={() => setUploadOpen(true)}
          className="flex items-center gap-2 bg-accent text-white rounded-lg px-6 py-2.5 text-sm font-medium hover:bg-accent-hover transition-colors duration-200"
        >
          <Upload size={16} />
          上传小说开始
        </button>
      </div>

      {projects.length > 0 && (
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-text-primary">最近项目</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {projects.slice(0, 6).map((project) => (
              <button
                key={project.id}
                onClick={async () => {
                  await selectProject(project.id)
                  navigate(`/project/${project.id}`)
                }}
                className="flex items-center justify-between p-4 bg-surface border border-border rounded-xl hover:border-border-hover hover:bg-elevated transition-all duration-200 text-left group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 rounded-lg bg-elevated shrink-0">
                    <BookOpen size={18} className="text-text-secondary" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-text-primary truncate">{project.name}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Clock size={12} className="text-text-muted" />
                      <span className="text-xs text-text-muted">{project.created_at}</span>
                    </div>
                  </div>
                </div>
                <ArrowRight size={16} className="text-text-muted group-hover:text-text-secondary transition-colors duration-200 shrink-0" />
              </button>
            ))}
          </div>
        </div>
      )}

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={async (file, name) => {
          await createProject(file, name)
          setUploadOpen(false)
        }}
        loading={loading}
      />
    </div>
  )
}
