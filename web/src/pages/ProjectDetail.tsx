import { useState, useEffect } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Globe, Users, ImageIcon } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import { api } from '@/api/client'
import WorldBibleView from '@/components/WorldBibleView'
import EntityCard from '@/components/EntityCard'
import EntityDrawer from '@/components/EntityDrawer'
import Gallery from '@/components/Gallery'

type TabKey = 'world' | 'entities' | 'gallery'

const tabs: { key: TabKey; label: string; icon: typeof Globe }[] = [
  { key: 'world', label: '世界观', icon: Globe },
  { key: 'entities', label: '实体', icon: Users },
  { key: 'gallery', label: '图集', icon: ImageIcon },
]

const entityTypes = [
  { key: 'all', label: '全部' },
  { key: 'character', label: '角色' },
  { key: 'scene', label: '场景' },
  { key: 'item', label: '物品' },
]

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const { selectProject, currentProject } = useProjectStore()

  const initialTab = searchParams.get('tab') === 'gallery' ? 'gallery' : 'world'
  const [activeTab, setActiveTab] = useState<TabKey>(initialTab)
  const [entityType, setEntityType] = useState('all')
  const [worldBible, setWorldBible] = useState<any>(null)
  const [entities, setEntities] = useState<any[]>([])
  const [images, setImages] = useState<any[]>([])
  const [selectedEntity, setSelectedEntity] = useState<any>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [dataLoading, setDataLoading] = useState(false)

  useEffect(() => {
    if (id) selectProject(id)
  }, [id, selectProject])

  useEffect(() => {
    if (!id) return
    setDataLoading(true)

    const loadData = async () => {
      try {
        if (activeTab === 'world') {
          const data = await api.worldBible.get(id)
          setWorldBible(data)
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

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">
          {currentProject?.name || '项目详情'}
        </h1>
        <p className="text-sm text-text-muted mt-1">{currentProject?.novel_name}</p>
      </div>

      <div className="flex items-center gap-1 bg-surface border border-border rounded-lg p-1 w-fit">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-all duration-200 ${
                activeTab === tab.key
                  ? 'bg-elevated text-text-primary font-medium'
                  : 'text-text-muted hover:text-text-secondary'
              }`}
            >
              <Icon size={15} />
              {tab.label}
            </button>
          )
        })}
      </div>

      <div>
        {activeTab === 'world' && (
          <WorldBibleView data={worldBible} loading={dataLoading} />
        )}

        {activeTab === 'entities' && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              {entityTypes.map((type) => (
                <button
                  key={type.key}
                  onClick={() => setEntityType(type.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs transition-all duration-200 ${
                    entityType === type.key
                      ? 'bg-accent text-white font-medium'
                      : 'bg-elevated text-text-secondary hover:text-text-primary'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>

            {dataLoading ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
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
              <div className="flex flex-col items-center justify-center py-20 text-text-muted">
                <Users size={48} className="mb-4 opacity-30" />
                <p className="text-sm">暂无实体数据</p>
                <p className="text-xs mt-1">运行流水线后将自动抽取实体</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
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
          <Gallery images={images} loading={dataLoading} />
        )}
      </div>

      <EntityDrawer
        entity={selectedEntity}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}
