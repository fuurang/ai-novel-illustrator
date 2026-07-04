import { useState, useEffect, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import {
  BookOpen,
  Bot,
  ChevronLeft,
  ChevronRight,
  Grid2X2,
  Grid3X3,
  ImageIcon,
  List,
  Lock,
  PanelLeftClose,
  PanelLeftOpen,
  RefreshCw,
  Trash2,
  Users,
  Globe,
  X,
} from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import { api } from '@/api/client'
import PipelineControl from '@/components/PipelineControl'
import EntityCard from '@/components/EntityCard'
import type { EntityViewMode } from '@/components/EntityCard'
import EntityDrawer from '@/components/EntityDrawer'
import Gallery from '@/components/Gallery'
import WorldBibleView from '@/components/WorldBibleView'
import AiWorkspace from '@/components/AiWorkspace'
import WorkflowGuide from '@/components/WorkflowGuide'
import { cn } from '@/lib/utils'
import { entityInScene } from '@/lib/entityFilters'
import { savedGalleryImagesFromEntities } from '@/lib/galleryImages'

type TabKey = 'world' | 'ai' | 'content' | 'entities' | 'gallery'

const tabs: { key: TabKey; label: string; icon: typeof BookOpen }[] = [
  { key: 'world', label: '世界观', icon: Globe },
  { key: 'ai', label: 'AI工作台', icon: Bot },
  { key: 'content', label: '章节内容', icon: BookOpen },
  { key: 'entities', label: '出图对象', icon: Users },
  { key: 'gallery', label: '图集', icon: ImageIcon },
]

const entityTypes = [
  { key: 'all', label: '全部' },
  { key: 'character', label: '角色' },
  { key: 'scene', label: '场景' },
  { key: 'item', label: '物品' },
]

const entityViewModes: { key: EntityViewMode; label: string; icon: typeof Grid2X2 }[] = [
  { key: 'small', label: '小卡片', icon: Grid3X3 },
  { key: 'large', label: '大卡片', icon: Grid2X2 },
  { key: 'details', label: '详细信息', icon: List },
]

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
  const [generatingEntityIds, setGeneratingEntityIds] = useState<Set<string>>(new Set())
  const [lockingEntityIds, setLockingEntityIds] = useState<Set<string>>(new Set())
  const [previewImage, setPreviewImage] = useState<{ url: string; name: string; entity: any } | null>(null)

  const [chapters, setChapters] = useState<any[]>([])
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null)
  const [chapterDetail, setChapterDetail] = useState<any>(null)
  const [chapterLoading, setChapterLoading] = useState(false)
  const [sceneGroups, setSceneGroups] = useState<any[]>([])
  const [selectedSceneFromPipeline, setSelectedSceneFromPipeline] = useState<any | null>(null)
  const [aiLaunch, setAiLaunch] = useState<{ task: string; instruction: string; extractionLevel?: string; sceneGranularity?: string; sceneId?: string } | null>(null)
  const [guideCollapsed, setGuideCollapsed] = useState(false)
  const [chapterListCollapsed, setChapterListCollapsed] = useState(false)
  const [entityViewMode, setEntityViewMode] = useState<EntityViewMode>('large')
  const [selectedEntityIds, setSelectedEntityIds] = useState<Set<string>>(new Set())

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
    if (!id) return
    const loadSceneGroups = async () => {
      try {
        const groups = await api.sceneGroups.list(id)
        setSceneGroups(groups)
      } catch {
        setSceneGroups([])
      }
    }
    loadSceneGroups()
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

  const selectedScene = useMemo(
    () => selectedSceneFromPipeline
      ? sceneGroups.find((group) => String(group.id) === String(selectedSceneFromPipeline.id)) || selectedSceneFromPipeline
      : null,
    [sceneGroups, selectedSceneFromPipeline]
  )

  const visibleEntities = useMemo(
    () => entities.filter((entity) => {
      if (entityType !== 'all' && entity.type !== entityType) return false
      if (selectedScene && !entityInScene(entity, selectedScene)) return false
      return true
    }),
    [entities, entityType, selectedScene]
  )

  useEffect(() => {
    if (!id) return
    setDataLoading(true)
    const loadData = async () => {
      try {
        if (activeTab === 'world') {
          await loadWorldBible()
        } else if (activeTab === 'entities') {
          const data = await api.entities.list(id)
          setEntities(data)
        } else if (activeTab === 'gallery') {
          const data = await api.entities.list(id)
          setEntities(data)
          setImages(savedGalleryImagesFromEntities(data))
        }
      } catch {
      } finally {
        setDataLoading(false)
      }
    }
    loadData()
  }, [id, activeTab, entityType])

  useEffect(() => {
    setSelectedEntityIds((current) => {
      if (!current.size) return current
      const visibleIds = new Set(visibleEntities.map((entity) => entity.id))
      const next = new Set([...current].filter((entityId) => visibleIds.has(entityId)))
      return next.size === current.size ? current : next
    })
  }, [visibleEntities])

  const withImageVersion = (entity: any, imageVersion?: number) => {
    if (!imageVersion || !entity?.image_url) return entity
    const appendVersion = (url?: string) => {
      if (!url) return url
      return `${url}${url.includes('?') ? '&' : '?'}v=${imageVersion}`
    }
    return {
      ...entity,
      image_url: appendVersion(entity.image_url),
      locked_image_url: appendVersion(entity.locked_image_url),
    }
  }

  const refreshEntity = async (entityId: string, imageVersion?: number) => {
    if (!id) return null
    const detail = withImageVersion(await api.entities.get(id, entityId), imageVersion)
    setEntities((current) => {
      const nextEntities = current.map((entity) => (entity.id === entityId ? detail : entity))
      if (activeTab === 'gallery') setImages(savedGalleryImagesFromEntities(nextEntities))
      return nextEntities
    })
    setSelectedEntity((current: any) => (current?.id === entityId ? detail : current))
    setPreviewImage((current) =>
      current?.entity?.id === entityId && detail.image_url
        ? { url: detail.image_url, name: detail.name || current.name, entity: detail }
        : current
    )
    return detail
  }

  const refreshEntities = async (imageVersion?: number, refreshedEntityIds?: Set<string>) => {
    if (!id) return
    const data = await api.entities.list(id)
    const nextEntities = data.map((entity: any) =>
        !refreshedEntityIds || refreshedEntityIds.has(entity.id)
          ? withImageVersion(entity, imageVersion)
          : entity
    )
    setEntities(nextEntities)
    if (activeTab === 'gallery') setImages(savedGalleryImagesFromEntities(nextEntities))
  }

  const handleEntityInspect = async (entity: any) => {
    if (!id) return
    try {
      const detail = await api.entities.get(id, entity.id)
      setSelectedEntity(detail)
    } catch {
      setSelectedEntity(entity)
    }
    setDrawerOpen(true)
  }

  const handleEntityView = async (entity: any) => {
    if (entity.image_url) {
      setPreviewImage({
        url: entity.image_url,
        name: entity.name || '出图对象',
        entity,
      })
      return
    }
    await handleEntityInspect(entity)
  }

  const handleEntityGenerate = async (entity: any) => {
    if (!id || generatingEntityIds.has(entity.id)) return
    if (entity.image_locked) {
      window.alert('这张图已经保存，先取消保存后再重抽。')
      return
    }

    setGeneratingEntityIds((current) => new Set(current).add(entity.id))
    setEntities((current) =>
      current.map((item) =>
        item.id === entity.id ? { ...item, image_status: 'generating' } : item
      )
    )

    try {
      await api.images.generateSingle(id, entity.id)
      await refreshEntity(entity.id, Date.now())
      if (activeTab === 'gallery') {
        await refreshEntities()
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '图片生成失败')
      setEntities((current) =>
        current.map((item) =>
          item.id === entity.id ? { ...item, image_status: 'error' } : item
        )
      )
    } finally {
      setGeneratingEntityIds((current) => {
        const next = new Set(current)
        next.delete(entity.id)
        return next
      })
    }
  }

  const handleGenerateUnlocked = async () => {
    if (!id || generatingEntityIds.size > 0) return
    const targetIds = visibleEntities
      .filter((entity) => !entity.image_locked)
      .map((entity) => entity.id)

    if (targetIds.length === 0) {
      window.alert('当前筛选下没有可重抽的未保存对象。')
      return
    }

    setGeneratingEntityIds(new Set(targetIds))
    setEntities((current) =>
      current.map((entity) =>
        targetIds.includes(entity.id) ? { ...entity, image_status: 'generating' } : entity
      )
    )

    try {
      await api.images.generate(id, { entity_ids: targetIds, skip_locked: true })
      await refreshEntities(Date.now(), new Set(targetIds))
      if (activeTab === 'gallery') {
        await refreshEntities()
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '图片生成失败')
      setEntities((current) =>
        current.map((entity) =>
          targetIds.includes(entity.id) ? { ...entity, image_status: 'error' } : entity
        )
      )
    } finally {
      setGeneratingEntityIds(new Set())
    }
  }

  const handleEntityLock = async (entity: any, locked: boolean) => {
    if (!id || lockingEntityIds.has(entity.id)) return

    setLockingEntityIds((current) => new Set(current).add(entity.id))
    try {
      await api.images.lock(id, entity.id, locked)
      const detail = await refreshEntity(entity.id)
      await refreshEntities()
      if (detail?.image_url && previewImage?.entity?.id === entity.id) {
        setPreviewImage({ url: detail.image_url, name: detail.name || entity.name, entity: detail })
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '图片保存状态更新失败')
    } finally {
      setLockingEntityIds((current) => {
        const next = new Set(current)
        next.delete(entity.id)
        return next
      })
    }
  }

  const handleGalleryImageDelete = async (image: any) => {
    if (!id) return
    const imageRef = image.path || image.url
    if (!imageRef) return

    try {
      await api.images.delete(id, imageRef)
      await refreshEntities()
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '图片删除失败')
      throw error
    }
  }

  const handleEntityDelete = async (entity: any) => {
    if (!id || !entity?.id) return
    if (generatingEntityIds.has(entity.id)) {
      window.alert('这个对象正在生成图片，完成后再删除。')
      return
    }
    const name = entity.name || '未命名出图对象'
    const confirmed = window.confirm(`确定删除“${name}”吗？\n\n会删除这个出图对象和对应绘图指令，但不会删除已经生成的图片文件。`)
    if (!confirmed) return

    try {
      await api.entities.delete(id, entity.id)
      setEntities((current) => current.filter((item) => item.id !== entity.id))
      setSelectedEntityIds((current) => {
        const next = new Set(current)
        next.delete(entity.id)
        return next
      })
      setSelectedEntity((current: any) => (current?.id === entity.id ? null : current))
      if (selectedEntity?.id === entity.id) setDrawerOpen(false)
      setPreviewImage((current) => (current?.entity?.id === entity.id ? null : current))
      if (activeTab === 'gallery') {
        await refreshEntities()
      }
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '删除出图对象失败')
    }
  }

  const toggleEntitySelection = (entityId: string, checked: boolean) => {
    setSelectedEntityIds((current) => {
      const next = new Set(current)
      if (checked) {
        next.add(entityId)
      } else {
        next.delete(entityId)
      }
      return next
    })
  }

  const setAllVisibleEntitySelection = (checked: boolean) => {
    setSelectedEntityIds((current) => {
      const next = new Set(current)
      visibleEntities.forEach((entity) => {
        if (checked) {
          next.add(entity.id)
        } else {
          next.delete(entity.id)
        }
      })
      return next
    })
  }

  const handleBulkEntityDelete = async () => {
    if (!id || selectedEntityIds.size === 0) return
    const selectedIds = [...selectedEntityIds]
    const generatingIds = selectedIds.filter((entityId) => generatingEntityIds.has(entityId))
    if (generatingIds.length > 0) {
      window.alert(`有 ${generatingIds.length} 个对象正在生成图片，完成后再删除。`)
      return
    }

    const selectedNames = visibleEntities
      .filter((entity) => selectedEntityIds.has(entity.id))
      .slice(0, 5)
      .map((entity) => entity.name || '未命名出图对象')
      .join('、')
    const targetLabel = selectedIds.length > 5
      ? `${selectedNames} 等 ${selectedIds.length} 个`
      : `${selectedNames || `${selectedIds.length} 个`}`
    const confirmed = window.confirm(
      `确定批量删除这些出图对象吗？\n${targetLabel}\n\n会删除对应绘图指令，但不会删除已经生成的图片文件。`
    )
    if (!confirmed) return

    try {
      const result = await api.entities.bulkDelete(id, selectedIds)
      const deletedIds = new Set(result.deleted_entity_ids || selectedIds)
      setEntities((current) => current.filter((entity) => !deletedIds.has(entity.id)))
      setSelectedEntityIds(new Set())
      setSelectedEntity((current: any) => (current && deletedIds.has(current.id) ? null : current))
      if (selectedEntity && deletedIds.has(selectedEntity.id)) setDrawerOpen(false)
      setPreviewImage((current) => (current?.entity?.id && deletedIds.has(current.entity.id) ? null : current))
      if (activeTab === 'gallery') await refreshEntities()
    } catch (error) {
      window.alert(error instanceof Error ? error.message : '批量删除出图对象失败')
    }
  }

  const chapterText = chapterDetail?.chapter?.text || chapterDetail?.content || chapterDetail?.text || ''
  const chapterTitle = chapterDetail?.chapter?.title || chapterDetail?.title || ''
  const confirmedSceneCount = sceneGroups.filter((group) => group.source === 'ai' || group.source === 'manual').length

  const startAiTask = (task: string, instruction: string) => {
    setAiLaunch({ task, instruction })
    setActiveTab('ai')
  }

  const handleAutoWorkflowComplete = async () => {
    if (!id) return
    const entityList = await api.entities.list(id)
    const version = Date.now()
    const nextEntities = entityList.map((entity: any) => withImageVersion(entity, version))
    setEntities(nextEntities)
    setImages(savedGalleryImagesFromEntities(nextEntities))
    setActiveTab('entities')
  }

  const unlockedEntityCount = visibleEntities.filter((entity) => !entity.image_locked).length
  const lockedEntityCount = visibleEntities.length - unlockedEntityCount
  const isBatchGenerating = generatingEntityIds.size > 0
  const selectedEntityCount = selectedEntityIds.size
  const allVisibleEntitiesSelected = visibleEntities.length > 0 && visibleEntities.every((entity) => selectedEntityIds.has(entity.id))
  const previewableEntities = visibleEntities.filter((entity) => entity.image_url)
  const previewIndex = previewImage
    ? previewableEntities.findIndex((entity) => entity.id === previewImage.entity?.id)
    : -1
  const canSwitchPreview = previewableEntities.length > 1 && previewIndex >= 0

  const showAdjacentPreview = (direction: -1 | 1) => {
    if (!canSwitchPreview) return
    const nextIndex = (previewIndex + direction + previewableEntities.length) % previewableEntities.length
    const nextEntity = previewableEntities[nextIndex]
    setPreviewImage({
      url: nextEntity.image_url,
      name: nextEntity.name || '出图对象',
      entity: nextEntity,
    })
  }

  useEffect(() => {
    if (activeTab === 'ai') {
      setGuideCollapsed(true)
      setChapterListCollapsed(true)
    }
  }, [activeTab])

  useEffect(() => {
    if (!previewImage) return
    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === 'Escape') {
        setPreviewImage(null)
      } else if (event.key === 'ArrowLeft') {
        showAdjacentPreview(-1)
      } else if (event.key === 'ArrowRight') {
        showAdjacentPreview(1)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [previewImage, canSwitchPreview, previewIndex, previewableEntities.length])

  return (
    <div className="flex flex-col h-full">
      {/* 顶部：流水线控制 */}
      <div className="shrink-0 bg-surface border-b border-border">
        <PipelineControl
          onAutoWorkflowComplete={handleAutoWorkflowComplete}
          onSelectedSceneChange={setSelectedSceneFromPipeline}
          onOpenAiWorkspace={(options) => {
            if (options?.task) {
              setAiLaunch({
                task: options.task,
                instruction: '',
                extractionLevel: options.extractionLevel,
                sceneGranularity: options.sceneGranularity,
                sceneId: options.sceneId,
              })
            }
            setActiveTab('ai')
          }}
        />
      </div>

      <WorkflowGuide
        activeTab={activeTab}
        hasWorldBible={!!worldBible}
        confirmedSceneCount={confirmedSceneCount}
        selectedChapter={selectedChapter}
        collapsed={guideCollapsed}
        onSwitchTab={setActiveTab}
        onStartAiTask={startAiTask}
        onToggleCollapsed={() => setGuideCollapsed((value) => !value)}
      />
      
      {/* 下方三栏布局 */}
      <div className="flex flex-1 min-h-0">
        {/* 左侧：章节列表 */}
        {chapterListCollapsed ? (
          <div className="w-10 shrink-0 bg-surface border-r border-border flex flex-col items-center py-2">
            <button
              type="button"
              title="展开章节列表"
              onClick={() => setChapterListCollapsed(false)}
              className="p-2 rounded-md text-text-muted hover:text-text-primary hover:bg-elevated"
            >
              <PanelLeftOpen size={16} />
            </button>
            <div className="mt-3 text-[11px] text-text-muted [writing-mode:vertical-rl] tracking-widest">
              章节
            </div>
            {selectedChapter && (
              <div className="mt-3 text-xs text-accent font-mono">{selectedChapter}</div>
            )}
          </div>
        ) : (
          <div className="w-[280px] shrink-0 bg-surface border-r border-border flex flex-col">
            <div className="p-4 border-b border-border shrink-0">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <h1 className="text-base font-semibold text-text-primary truncate">
                    {currentProject?.name || '项目详情'}
                  </h1>
                  <p className="text-xs text-text-muted mt-1 truncate">{currentProject?.novel_name}</p>
                </div>
                <button
                  type="button"
                  title="收起章节列表"
                  onClick={() => setChapterListCollapsed(true)}
                  className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-elevated shrink-0"
                >
                  <PanelLeftClose size={16} />
                </button>
              </div>
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
        )}

        {/* 中间：主内容 */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center justify-between gap-3 bg-surface border-b border-border px-4 py-1.5 shrink-0">
            <div className="flex items-center gap-1 min-w-0">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    'flex items-center gap-2 px-3.5 py-1.5 rounded-md text-sm transition-all duration-200',
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
            <div className="flex items-center gap-1 shrink-0">
              <button
                type="button"
                onClick={() => setChapterListCollapsed((value) => !value)}
                className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-text-muted hover:text-text-primary hover:bg-elevated"
              >
                {chapterListCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
                章节
              </button>
              <button
                type="button"
                onClick={() => setGuideCollapsed((value) => !value)}
                className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-text-muted hover:text-text-primary hover:bg-elevated"
              >
                {guideCollapsed ? '展开指引' : '收起指引'}
              </button>
            </div>
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

          <div className={cn('h-full', activeTab === 'ai' ? 'block' : 'hidden')}>
            <AiWorkspace
              projectId={id || ''}
              selectedChapter={selectedChapter}
              initialTask={aiLaunch?.task}
              initialInstruction={aiLaunch?.instruction}
              initialExtractionLevel={aiLaunch?.extractionLevel}
              initialSceneGranularity={aiLaunch?.sceneGranularity}
              initialSceneId={aiLaunch?.sceneId}
              onInitialHandled={() => setAiLaunch(null)}
            />
          </div>

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
              <div className="p-4 h-full flex flex-col">
                <div className="flex items-center justify-between gap-3 mb-3 shrink-0">
                  <div>
                    <h2 className="text-sm font-semibold text-text-primary">出图对象</h2>
                    <p className="text-xs text-text-muted mt-0.5">
                      点击卡片查看图片，生成和保存需要点右侧按钮。
                      {lockedEntityCount > 0 && ` 已保存 ${lockedEntityCount} 个。`}
                      {selectedEntityCount > 0 && ` 已选择 ${selectedEntityCount} 个。`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => setAllVisibleEntitySelection(!allVisibleEntitiesSelected)}
                      className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-text-secondary hover:text-text-primary hover:bg-elevated"
                    >
                      <input
                        type="checkbox"
                        checked={allVisibleEntitiesSelected}
                        readOnly
                        className="h-3.5 w-3.5 accent-orange-500"
                      />
                      {allVisibleEntitiesSelected ? '取消全选' : '全选当前'}
                    </button>
                    <button
                      type="button"
                      disabled={selectedEntityCount === 0}
                      onClick={handleBulkEntityDelete}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs transition-colors',
                        selectedEntityCount === 0
                          ? 'cursor-not-allowed border-border bg-elevated/50 text-text-muted'
                          : 'border-error/40 bg-error/10 text-error hover:bg-error/15'
                      )}
                    >
                      <Trash2 size={14} />
                      删除选中
                    </button>
                    <button
                      type="button"
                      title="只重抽当前筛选下未保存的对象"
                      disabled={isBatchGenerating || unlockedEntityCount === 0}
                      onClick={handleGenerateUnlocked}
                      className={cn(
                        'inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs transition-colors',
                        isBatchGenerating || unlockedEntityCount === 0
                          ? 'cursor-not-allowed bg-elevated/50 text-text-muted'
                          : 'bg-elevated text-text-secondary hover:text-text-primary hover:bg-surface'
                      )}
                    >
                      {isBatchGenerating ? (
                        <RefreshCw size={14} className="animate-spin" />
                      ) : (
                        <RefreshCw size={14} />
                      )}
                      重抽未保存
                    </button>
                    <div className="flex items-center gap-1 rounded-lg bg-elevated p-1">
                      {entityViewModes.map((mode) => {
                        const Icon = mode.icon
                        return (
                          <button
                            key={mode.key}
                            type="button"
                            title={mode.label}
                            onClick={() => setEntityViewMode(mode.key)}
                            className={cn(
                              'inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs transition-colors',
                              entityViewMode === mode.key
                                ? 'bg-surface text-text-primary shadow-sm'
                                : 'text-text-muted hover:text-text-primary'
                            )}
                          >
                            <Icon size={14} />
                            <span>{mode.label}</span>
                          </button>
                        )
                      })}
                    </div>
                    <div className="flex items-center gap-2">
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
                  </div>
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
                ) : visibleEntities.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-text-muted">
                    <Users size={48} className="mb-4 opacity-30" />
                    <p className="text-sm">暂无出图对象</p>
                    <p className="text-xs mt-1">
                      {selectedScene ? '当前场景下暂无匹配对象。' : '请先到 AI 工作台识别角色、场景和物品。'}
                    </p>
                  </div>
                ) : (
                  entityViewMode === 'details' ? (
                    <div className="flex-1 overflow-y-auto rounded-lg border border-border bg-surface">
                      <div className="sticky top-0 z-10 grid grid-cols-[32px_minmax(180px,1.1fr)_88px_88px_minmax(220px,1.5fr)_112px_172px] gap-3 border-b border-border bg-elevated px-3 py-2 text-xs font-medium text-text-muted">
                        <div></div>
                        <div>名称</div>
                        <div>类型</div>
                        <div>章节</div>
                        <div>绘图指令预览</div>
                        <div>状态</div>
                        <div>操作</div>
                      </div>
                      {visibleEntities.map((entity) => (
                        <EntityCard
                          key={entity.id}
                          viewMode={entityViewMode}
                          entity={{
                            ...entity,
                            image_status: generatingEntityIds.has(entity.id)
                              ? 'generating'
                              : entity.image_status,
                          }}
                          selected={selectedEntityIds.has(entity.id)}
                          onSelectChange={(checked) => toggleEntitySelection(entity.id, checked)}
                          onClick={() => handleEntityView(entity)}
                          onGenerate={() => handleEntityGenerate(entity)}
                          onToggleLock={(locked) => handleEntityLock(entity, locked)}
                          onInspect={() => handleEntityInspect(entity)}
                          onDelete={() => handleEntityDelete(entity)}
                        />
                      ))}
                    </div>
                  ) : (
                    <div
                      className={cn(
                        'grid flex-1 overflow-y-auto content-start',
                        entityViewMode === 'small'
                          ? 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-7 gap-3'
                          : 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5'
                      )}
                    >
                      {visibleEntities.map((entity) => (
                        <EntityCard
                          key={entity.id}
                          viewMode={entityViewMode}
                          entity={{
                            ...entity,
                            image_status: generatingEntityIds.has(entity.id)
                              ? 'generating'
                              : entity.image_status,
                          }}
                          selected={selectedEntityIds.has(entity.id)}
                          onSelectChange={(checked) => toggleEntitySelection(entity.id, checked)}
                          onClick={() => handleEntityView(entity)}
                          onGenerate={() => handleEntityGenerate(entity)}
                          onToggleLock={(locked) => handleEntityLock(entity, locked)}
                          onInspect={() => handleEntityInspect(entity)}
                          onDelete={() => handleEntityDelete(entity)}
                        />
                      ))}
                    </div>
                  )
                )}
              </div>
            )}

            {activeTab === 'gallery' && (
              <div className="p-6 h-full">
                <Gallery images={images} loading={dataLoading} onDelete={handleGalleryImageDelete} />
              </div>
            )}
          </div>
        </div>

      </div>

      {previewImage && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85 p-5"
          onClick={() => setPreviewImage(null)}
        >
          <div
            className="relative flex max-h-full max-w-[min(1100px,96vw)] flex-col gap-3"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-3 text-white">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{previewImage.name}</div>
                {canSwitchPreview && (
                  <div className="mt-1 text-xs text-white/60">
                    {previewIndex + 1} / {previewableEntities.length}
                  </div>
                )}
                {previewImage.entity?.image_locked && (
                  <div className="mt-1 inline-flex items-center gap-1 text-xs text-success">
                    <Lock size={12} />
                    已保存，重抽未保存时会跳过
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  title={previewImage.entity?.image_locked ? '取消保存' : '保存这张图'}
                  onClick={() => handleEntityLock(previewImage.entity, !previewImage.entity?.image_locked)}
                  className="inline-flex items-center gap-1.5 rounded-md bg-white/10 px-3 py-1.5 text-xs text-white hover:bg-white/15"
                >
                  <Lock size={14} />
                  {previewImage.entity?.image_locked ? '取消保存' : '保存'}
                </button>
                <button
                  type="button"
                  title="重抽"
                  disabled={previewImage.entity?.image_locked || generatingEntityIds.has(previewImage.entity?.id)}
                  onClick={() => handleEntityGenerate(previewImage.entity)}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-md bg-white/10 px-3 py-1.5 text-xs text-white hover:bg-white/15',
                    (previewImage.entity?.image_locked || generatingEntityIds.has(previewImage.entity?.id)) &&
                      'cursor-not-allowed opacity-50'
                  )}
                >
                  <RefreshCw
                    size={14}
                    className={generatingEntityIds.has(previewImage.entity?.id) ? 'animate-spin' : ''}
                  />
                  重抽
                </button>
                <button
                  type="button"
                  title="关闭"
                  onClick={() => setPreviewImage(null)}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-white/10 text-white hover:bg-white/15"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
            <div className="flex min-h-0 items-center justify-center overflow-hidden rounded-lg border border-white/15 bg-black">
              {canSwitchPreview && (
                <button
                  type="button"
                  title="上一张"
                  onClick={(event) => {
                    event.stopPropagation()
                    showAdjacentPreview(-1)
                  }}
                  className="absolute left-3 top-1/2 z-10 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
                >
                  <ChevronLeft size={24} />
                </button>
              )}
              <img
                src={previewImage.url}
                alt={previewImage.name}
                className="max-h-[82vh] max-w-[96vw] object-contain"
              />
              {canSwitchPreview && (
                <button
                  type="button"
                  title="下一张"
                  onClick={(event) => {
                    event.stopPropagation()
                    showAdjacentPreview(1)
                  }}
                  className="absolute right-3 top-1/2 z-10 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
                >
                  <ChevronRight size={24} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <EntityDrawer
        entity={selectedEntity}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onDelete={selectedEntity ? () => handleEntityDelete(selectedEntity) : undefined}
      />
    </div>
  )
}
