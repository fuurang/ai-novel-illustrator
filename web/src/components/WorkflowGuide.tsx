import { Bot, BookOpen, ChevronDown, ChevronUp, Compass, Eye, Globe, Layers, Route } from 'lucide-react'
import { cn } from '@/lib/utils'

type TabKey = 'world' | 'ai' | 'content' | 'entities' | 'gallery'

interface WorkflowGuideProps {
  activeTab: TabKey
  hasWorldBible: boolean
  confirmedSceneCount: number
  selectedChapter?: number | null
  collapsed?: boolean
  onSwitchTab: (tab: TabKey) => void
  onStartAiTask: (task: string, instruction: string) => void
  onToggleCollapsed?: () => void
}

const globalWorldInstruction = `这是长篇小说的全局世界观识别。请只提取长期稳定的基底设定，不要把某个局部阶段当成全书唯一世界观。
需要区分：
1. 全局时代与现实基底
2. 长期存在的灾变/力量/怪物规则
3. 后续阶段可能变化的内容
4. 哪些风格绝对不能误判
如果原文同时有现代城市、末日灾变、古书/符文/修炼，请判断为现代末日灾变基底 + 特殊力量体系，而不是古典仙侠。`

const stageWorldInstruction = `请识别当前应该处理的下一个剧情阶段/场景区域。注意这是长篇小说，不要让全局世界观覆盖局部变化。
输出时请说明：
1. 本阶段章节范围
2. 本阶段环境类型
3. 相对全局世界观新增或变化的规则
4. 哪些局部视觉规则覆盖全局规则
5. 哪些全局规则仍然保留
6. 本阶段最容易误判成什么，以及如何避免`

const visualInstruction = `请基于全局世界观和已识别阶段，生成稳定视觉锚定。长篇小说中局部阶段可以变化，但全局身份、时代基底和核心力量体系不能丢。
如果当前阶段进入奇异空间、副本或异界，请把它作为局部视觉覆盖，不要把全书改成单一异世界风格。`

const executionInstruction = `识别出图对象、整理视觉设定或生成绘图指令时，请同时参考全局世界观、当前阶段/场景设定和当前章节原文。
优先级是：当前章节原文 > 当前阶段设定 > 全局世界观。
如果三者冲突，请保留原文证据，并在输出中说明冲突。`

const stepOrder = [
  '关联原文',
  '全局世界观',
  '下一场景',
  '出图对象',
  '视觉设定',
  '绘图指令',
  '生图',
]

export default function WorkflowGuide({
  activeTab,
  hasWorldBible,
  confirmedSceneCount,
  selectedChapter,
  collapsed = false,
  onSwitchTab,
  onStartAiTask,
  onToggleCollapsed,
}: WorkflowGuideProps) {
  const items = [
    {
      key: 'global',
      icon: Globe,
      title: '全局世界观',
      status: hasWorldBible ? '已建立' : '待建立',
      text: '只放长期不变的基底：时代、灾变、核心力量体系、禁用风格。',
      action: hasWorldBible ? '查看/重跑' : '去建立',
      onClick: () => onStartAiTask('world_bible_analyze', globalWorldInstruction),
      done: hasWorldBible,
    },
    {
      key: 'stage',
      icon: Layers,
      title: '阶段/场景世界观',
      status: confirmedSceneCount ? `${confirmedSceneCount} 个已确认` : '待识别',
      text: '长篇跨度靠它承接：城市灾变、逃亡、奇异空间、副本都单独记录。',
      action: '识别下一个',
      onClick: () => onStartAiTask('scene_segmentation', stageWorldInstruction),
      done: confirmedSceneCount > 0,
    },
    {
      key: 'visual',
      icon: Eye,
      title: '视觉锚定',
      status: hasWorldBible ? '可生成' : '先做全局',
      text: '把全局规则和阶段变化转成出图约束，防止现代末日跑成古风。',
      action: '生成锚定',
      onClick: () => onStartAiTask('visual_anchoring', visualInstruction),
      done: false,
    },
    {
      key: 'execute',
      icon: Bot,
      title: '执行 AI 任务',
      status: selectedChapter ? `当前第 ${selectedChapter} 章` : '未选章节',
      text: '出图对象、视觉设定、绘图指令都先生成本次指令，手动确认后再执行。',
      action: '去工作台',
      onClick: () => onStartAiTask('entity_extraction', executionInstruction),
      done: false,
    },
  ]

  if (collapsed) {
    return (
      <div className="bg-surface border-b border-border px-4 py-1.5">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="flex items-center gap-2 min-w-0 text-left text-text-secondary hover:text-text-primary"
          >
            <ChevronDown size={15} className="shrink-0" />
            <Compass size={15} className="text-accent shrink-0" />
            <span className="text-sm font-medium text-text-primary">长篇工作流指引</span>
            <span className="text-xs text-text-muted truncate">
              原文证据优先；全局定基底，阶段管变化，当前章节定细节。
            </span>
          </button>
          {activeTab !== 'ai' && (
            <button
              onClick={() => onSwitchTab('ai')}
              className="hidden sm:inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover shrink-0"
            >
              <BookOpen size={13} />
              去 AI 工作台
            </button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface border-b border-border px-4 py-2">
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <Compass size={16} className="text-accent shrink-0" />
          <div className="min-w-0">
            <div className="text-sm font-semibold text-text-primary">长篇工作流指引</div>
            <div className="text-xs text-text-muted truncate">
              原文证据优先；全局定基底，阶段管变化，当前章节定细节。
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className="hidden xl:flex items-center gap-1.5 text-[11px] text-text-muted">
            {stepOrder.map((step, index) => (
              <span key={step} className="flex items-center gap-1.5">
                <span className="px-2 py-1 rounded bg-elevated">{step}</span>
                {index < stepOrder.length - 1 && <span className="text-border-hover">→</span>}
              </span>
            ))}
          </div>
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs text-text-muted hover:text-text-primary hover:bg-elevated"
          >
            <ChevronUp size={14} />
            收起
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-2">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <div
              key={item.key}
              className="border border-border rounded-lg bg-base px-3 py-2 min-w-0"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Icon size={14} className={cn('shrink-0', item.done ? 'text-success' : 'text-accent')} />
                  <span className="text-sm font-medium text-text-primary truncate">{item.title}</span>
                </div>
                <span className={cn('text-[11px] shrink-0', item.done ? 'text-success' : 'text-text-muted')}>
                  {item.status}
                </span>
              </div>
              <div className="text-xs text-text-muted mt-1 h-[32px] leading-relaxed overflow-hidden">
                {item.text}
              </div>
              <button
                onClick={item.onClick}
                className="mt-1.5 inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent-hover"
              >
                <Route size={12} />
                {item.action}
              </button>
            </div>
          )
        })}
      </div>

      {activeTab !== 'ai' && (
        <button
          onClick={() => onSwitchTab('ai')}
          className="mt-3 inline-flex items-center gap-2 text-xs text-text-secondary hover:text-text-primary"
        >
          <BookOpen size={13} />
          所有大模型操作都在 AI 工作台里先看发送给 API 的指令、再确认执行
        </button>
      )}
    </div>
  )
}
