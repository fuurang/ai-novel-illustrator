import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { BookOpen, Users, ImageIcon, User, MapPin, Box, Globe } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import { api } from '@/api/client'
import PipelineControl from '@/components/PipelineControl'
import EntityCard from '@/components/EntityCard'
import EntityDrawer from '@/components/EntityDrawer'
import Gallery from '@/components/Gallery'
import WorldBibleView from '@/components/WorldBibleView'
import ImageGenerationPanel from '@/components/ImageGenerationPanel'
import { cn } from '@/lib/utils'

type TabKey = 'world' | 'content' | 'entities' | 'gallery'

const tabs: { key: TabKey; label: string; icon: typeof BookOpen }[] = [
  { key: 'world', label: '世界观', icon: Globe },
  { key: 'content', label: '章节内容', icon: BookOpen },
  { key: 'entities', label: '实体', icon: Users },
  { key: 'gallery', label: '图集', icon: ImageIcon },
]

const entityTypes = [
  { key: 'all', label: '全部' },
  { key: 'character', label: '角色' },
  { key: 'scene', label: '场景' },
  { key: 'item', label: '物品' },
]

const typeConfig: Record<string, { label: string; icon: typeof User; color: string; bg: string }> = {
  character: { label: '角色', icon: User, color: 'text-blue-400', bg: 'bg-blue-400/10' },
  scene: { label: '场景', icon: MapPin, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  item: { label: '物品', icon: Box, color: 'text-amber-400', bg: 'bg-amber-400/10' },
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const { selectProject, currentProject } = useProjectStore()

  const [activeTab, setActiveTab] = useState<TabKey>('world')
  const [entityType, setEntityType] = useState('all')
  const [entities, setEntities] = useState<any[]>([])
  const [images, setImages] = useState<any[]>([])
  const [worldBible, setWorldBible] = useState<any>(null)
  const [selectedEntity, setSelectedEntity] = useState<any>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [dataLoading, setDataLoading] = useState(false)

  const [chapters, setChapters] = useState<any[]>([])
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null)
  const [chapterDetail, setChapterDetail] = useState<any>(null)
  const [chapterLoading, setChapterLoading] = useState(false)

  useEffect(() => {
    if (id) selectProject(id)
  }, [id, selectProject])

  useEffect(() => {
    if (!id) return
    const loadChapters = async () => {
      try {
        const data = await api.chapters.list(id)
        setChapters(data)
        if (data.length > 0 && selectedChapter === null) {
          setSelectedChapter(data[0].chapter_number ?? data[0].index ?? 0)
        }
      } catch {}
    }
    loadChapters()
  }, [id])

  useEffect(() => {
    if (selectedChapter === null || !id) return
    const loadDetail = async () => {
      setChapterLoading(true)
      try {
        const data = await api.chapters.getDetail(id, selectedChapter)
        setChapterDetail(data)
      } catch {
        setChapterDetail(null)
      } finally {
        setChapterLoading(false)
      }
    }
    loadDetail()
  }, [id, selectedChapter])

  const loadWorldBible = async () => {
    if (!id) return
    try {
      const data = await api.worldBible.get(id)
      setWorldBible(data)
    } catch {}
  }

  useEffect(() => {
    if (!id) return
    setDataLoading(true)
    const loadData = async () => {
      try {
        if (activeTab === 'world') {
          await loadWorldBible()
        } else if (activeTab === 'entities') {
          const type = entityType === 'all' ? undefined : entityType
          const data = await api.entities.list(id, type)
          setEntities(data)
        } else if (activeTab === 'gallery') {
          const data = await api.images.list(id)
          setImages(data)
        }
      } catch {
      } finally {
        setDataLoading(false)
      }
    }
    loadData()
  }, [id, activeTab, entityType])

  const handleEntityClick = async (entity: any) => {
    if (!id) return
    try {
      const detail = await api.entities.get(id, entity.id)
      setSelectedEntity(detail)
    } catch {
      setSelectedEntity(entity)
    }
    setDrawerOpen(true)
  }

  const truncateText = (text: string, maxLen: number) => {
    if (!text) return ''
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text
  }

  const chapterText = chapterDetail?.chapter?.text || chapterDetail?.content || chapterDetail?.text || ''
  const chapterTitle = chapterDetail?.chapter?.title || chapterDetail?.title || ''
  const chapterEntities = chapterDetail?.entities || []
  const chapterImages = chapterDetail?.images || []

  return (
    <div className="flex flex-col h-full">
      {/* 顶部：流水线控制 */}
      <div className="shrink-0 bg-surface border-b border-border">
        <PipelineControl />
      </div>
      
      {/* 下方三栏布局 */}
      <div className="flex flex-1 min-h-0">
        {/* 左侧：章节列表 */}
        <div className="w-[280px] shrink-0 bg-surface border-r border-border flex flex-col">
          <div className="p-4 border-b border-border shrink-0">
            <h1 className="text-base font-semibold text-text-primary truncate">
              {currentProject?.name || '项目详情'}
            </h1>
            <p className="text-xs text-text-muted mt-1 truncate">{currentProject?.novel_name}</p>
          </div>

          <div className="flex-1 overflow-y-auto min-h-0 p-2">
            <div className="text-xs text-text-muted px-2 mb-2">章节列表</div>
            {chapters.length === 0 ? (
              <div className="px-2 py-4 text-center text-text-muted text-xs">暂无章节数据</div>
            ) : (
              chapters.map((ch) => {
                const num = ch.chapter_number ?? ch.index ?? 0
                const isSelected = selectedChapter === num
                return (
                  <button
                    key={num}
                    onClick={() => setSelectedChapter(num)}
                    className={cn(
                      'w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 transition-colors duration-150 mb-0.5',
                      isSelected
                        ? 'bg-accent/10 text-accent'
                        : 'text-text-secondary hover:bg-elevated hover:text-text-primary'
                    )}
                  >
                    <span className="text-xs font-mono w-6 shrink-0 text-right">{num}</span>
                    <span className="text-sm truncate flex-1">{ch.title || `第${num}章`}</span>
                  </button>
                )
              })
            )}
          </div>
        </div>

        {/* 中间：主内容 */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center gap-1 bg-surface border-b border-border px-4 py-2 shrink-0">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-all duration-200',
                    activeTab === tab.key
                      ? 'bg-elevated text-text-primary font-medium'
                      : 'text-text-muted hover:text-text-secondary'
                  )}
                >
                  <Icon size={15} />
                  {tab.label}
                </button>
              )
            })}
          </div>

          <div className="flex-1 overflow-y-auto">
          {activeTab === 'world' && (
            <div className="p-6">
              <WorldBibleView 
                data={worldBible} 
                loading={dataLoading} 
                projectId={id || ''} 
                onUpdate={loadWorldBible} 
              />
            </div>
          )}

          {activeTab === 'content' && (
            chapterLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              </div>
            ) : !chapterDetail ? (
              <div className="flex items-center justify-center h-full text-text-muted text-sm">
                选择左侧章节查看内容
              </div>
            ) : (
              <div className="h-full flex flex-col">
                <div className="px-6 py-4 border-b border-border bg-elevated/30">
                  <h2 className="text-lg font-semibold text-text-primary">
                    {chapterTitle ? chapterTitle : `第${selectedChapter}章`}
                  </h2>
                </div>
                <div className="flex-1 p-6 overflow-y-auto">
                  <div className="bg-surface border border-border rounded-xl h-full flex flex-col">
                    <div className="px-4 py-3 bg-elevated/50 border-b border-border shrink-0">
                      <span className="text-sm font-medium text-text-primary">章节内容预览</span>
                    </div>
                    <div className="flex-1 p-6 overflow-y-auto">
                      <p className="text-base text-text-secondary leading-relaxed whitespace-pre-wrap">
                        {chapterText || '暂无章节内容'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )
          )}

            {activeTab === 'entities' && (
              <div className="p-6 h-full flex flex-col">
                <div className="flex items-center gap-2 mb-4 shrink-0">
                  {entityTypes.map((type) => (
                    <button
                      key={type.key}
                      onClick={() => setEntityType(type.key)}
                      className={cn(
                        'px-3 py-1.5 rounded-lg text-xs transition-all duration-200',
                        entityType === type.key
                          ? 'bg-accent text-white font-medium'
                          : 'bg-elevated text-text-secondary hover:text-text-primary'
                      )}
                    >
                      {type.label}
                    </button>
                  ))}
                </div>

                {dataLoading ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 flex-1 overflow-y-auto content-start">
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) => (
                      <div key={i} className="bg-surface border border-border rounded-xl animate-pulse">
                        <div className="aspect-square bg-elevated" />
                        <div className="p-3 space-y-2">
                          <div className="h-4 bg-elevated rounded w-2/3" />
                          <div className="h-3 bg-elevated rounded w-1/2" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : entities.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-text-muted">
                    <Users size={48} className="mb-4 opacity-30" />
                    <p className="text-sm">暂无实体数据</p>
                    <p className="text-xs mt-1">运行流水线后将自动抽取实体</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 flex-1 overflow-y-auto content-start">
                    {entities.map((entity) => (
                      <EntityCard
                        key={entity.id}
                        entity={entity}
                        onClick={() => handleEntityClick(entity)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'gallery' && (
              <div className="p-6 h-full">
                <Gallery images={images} loading={dataLoading} />
              </div>
            )}
          </div>
        </div>

        {/* 右侧：图片生成 */}
        <div className="w-[320px] shrink-0 bg-surface border-l border-border overflow-y-auto">
          {/* 简单的图片生成区域，使用 PipelineControl 中的图片生成部分 */}
          <ImageGenerationPanel />
        </div>
      </div>

      <EntityDrawer
        entity={selectedEntity}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}
