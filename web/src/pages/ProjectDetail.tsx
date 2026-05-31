import { useState, useEffect } from 'react'
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
  const [aiLaunch, setAiLaunch] = useState<{ task: string; instruction: string; extractionLevel?: string; sceneGranularity?: string } | null>(null)
  const [guideCollapsed, setGuideCollapsed] = useState(false)
  const [chapterListCollapsed, setChapterListCollapsed] = useState(false)
  const [entityViewMode, setEntityViewMode] = useState<EntityViewMode>('large')

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
    setEntities((current) => current.map((entity) => (entity.id === entityId ? detail : entity)))
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
    const type = entityType === 'all' ? undefined : entityType
    const data = await api.entities.list(id, type)
    setEntities(
      data.map((entity: any) =>
        !refreshedEntityIds || refreshedEntityIds.has(entity.id)
          ? withImageVersion(entity, imageVersion)
          : entity
      )
    )
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
        const data = await api.images.list(id)
        setImages(data)
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
    const targetIds = entities
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
        const data = await api.images.list(id)
        setImages(data)
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

  const chapterText = chapterDetail?.chapter?.text || chapterDetail?.content || chapterDetail?.text || ''
  const chapterTitle = chapterDetail?.chapter?.title || chapterDetail?.title || ''
  const confirmedSceneCount = sceneGroups.filter((group) => group.source === 'ai' || group.source === 'manual').length

  const startAiTask = (task: string, instruction: string) => {
    setAiLaunch({ task, instruction })
    setActiveTab('ai')
  }

  const unlockedEntityCount = entities.filter((entity) => !entity.image_locked).length
  const lockedEntityCount = entities.length - unlockedEntityCount
  const isBatchGenerating = generatingEntityIds.size > 0

  useEffect(() => {
    if (activeTab === 'ai') {
      setGuideCollapsed(true)
      setChapterListCollapsed(true)
    }
  }, [activeTab])

  return (
    <div className="flex flex-col h-full">
      {/* 顶部：流水线控制 */}
      <div className="shrink-0 bg-surface border-b border-border">
        <PipelineControl
          onOpenAiWorkspace={(options) => {
            if (options?.task) {
              setAiLaunch({
                task: options.task,
                instruction: '',
                extractionLevel: options.extractionLevel,
                sceneGranularity: options.sceneGranularity,
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

          {activeTab === 'ai' && (
            <AiWorkspace
              projectId={id || ''}
              selectedChapter={selectedChapter}
              initialTask={aiLaunch?.task}
              initialInstruction={aiLaunch?.instruction}
              initialExtractionLevel={aiLaunch?.extractionLevel}
              initialSceneGranularity={aiLaunch?.sceneGranularity}
              onInitialHandled={() => setAiLaunch(null)}
            />
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
              <div className="p-4 h-full flex flex-col">
                <div className="flex items-center justify-between gap-3 mb-3 shrink-0">
                  <div>
                    <h2 className="text-sm font-semibold text-text-primary">出图对象</h2>
                    <p className="text-xs text-text-muted mt-0.5">
                      点击卡片查看图片，生成和保存需要点右侧按钮。
                      {lockedEntityCount > 0 && ` 已保存 ${lockedEntityCount} 个。`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
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
                ) : entities.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-text-muted">
                    <Users size={48} className="mb-4 opacity-30" />
                    <p className="text-sm">暂无出图对象</p>
                    <p className="text-xs mt-1">请先到 AI 工作台识别角色、场景和物品。</p>
                  </div>
                ) : (
                  entityViewMode === 'details' ? (
                    <div className="flex-1 overflow-y-auto rounded-lg border border-border bg-surface">
                      <div className="sticky top-0 z-10 grid grid-cols-[minmax(180px,1.1fr)_88px_88px_minmax(220px,1.5fr)_112px_172px] gap-3 border-b border-border bg-elevated px-3 py-2 text-xs font-medium text-text-muted">
                        <div>名称</div>
                        <div>类型</div>
                        <div>章节</div>
                        <div>绘图指令预览</div>
                        <div>状态</div>
                        <div>操作</div>
                      </div>
                      {entities.map((entity) => (
                        <EntityCard
                          key={entity.id}
                          viewMode={entityViewMode}
                          entity={{
                            ...entity,
                            image_status: generatingEntityIds.has(entity.id)
                              ? 'generating'
                              : entity.image_status,
                          }}
                          onClick={() => handleEntityView(entity)}
                          onGenerate={() => handleEntityGenerate(entity)}
                          onToggleLock={(locked) => handleEntityLock(entity, locked)}
                          onInspect={() => handleEntityInspect(entity)}
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
                      {entities.map((entity) => (
                        <EntityCard
                          key={entity.id}
                          viewMode={entityViewMode}
                          entity={{
                            ...entity,
                            image_status: generatingEntityIds.has(entity.id)
                              ? 'generating'
                              : entity.image_status,
                          }}
                          onClick={() => handleEntityView(entity)}
                          onGenerate={() => handleEntityGenerate(entity)}
                          onToggleLock={(locked) => handleEntityLock(entity, locked)}
                          onInspect={() => handleEntityInspect(entity)}
                        />
                      ))}
                    </div>
                  )
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
              <img
                src={previewImage.url}
                alt={previewImage.name}
                className="max-h-[82vh] max-w-[96vw] object-contain"
              />
            </div>
          </div>
        </div>
      )}

      <EntityDrawer
        entity={selectedEntity}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}
