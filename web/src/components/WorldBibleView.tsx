import { BookOpen, Edit2, Save, X, FileText, Sparkles, Braces, AlertCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { api } from '@/api/client'

interface WorldBibleViewProps {
  data: any
  loading?: boolean
  projectId: string
  onUpdate?: () => void
}

const sectionCard = 'bg-surface border border-border rounded-xl'
const inputClass =
  'w-full bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent'
const textareaClass =
  'w-full bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent resize-y'

function createEmptyWorldBible(projectId: string) {
  return {
    id: '',
    project_id: projectId,
    novel_title: '',
    user_worldview_text: '',
    world_framework: {
      genre: '',
      sub_genre: '',
      era_setting: '',
      technology_level: '',
      power_system: '',
      social_structure: '',
      geography_overview: '',
      key_concepts: [],
      tone_and_mood: '',
    },
    visual_anchoring: {
      art_style: '',
      art_style_en: '',
      color_palette: {
        primary: '',
        secondary: '',
        accent: '',
        mood: '',
        specific_colors: [],
      },
      lighting_style: '',
      texture_style: '',
      atmosphere_keywords: [],
      atmosphere_keywords_en: [],
      forbidden_elements: [],
    },
    character_visual_rules: {
      face_style: '',
      face_style_en: '',
      body_proportion: '',
      clothing_system: '',
      clothing_materials: '',
      hair_style_rules: '',
      accessory_rules: '',
    },
    scene_visual_rules: {
      architecture_style: '',
      landscape_style: '',
      interior_style: '',
      weather_patterns: '',
    },
    item_visual_rules: {
      weapon_style: '',
      material_system: '',
      craftsmanship: '',
    },
  }
}

function splitLines(value: string): string[] {
  return value
    .split(/\r?\n|,|，|;/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function joinLines(value: unknown): string {
  if (Array.isArray(value)) return value.join('\n')
  if (typeof value === 'string') return value
  return ''
}

function setNestedValue(target: any, path: string[], value: any) {
  let current = target
  for (let i = 0; i < path.length - 1; i += 1) {
    if (!current[path[i]] || typeof current[path[i]] !== 'object') current[path[i]] = {}
    current = current[path[i]]
  }
  current[path[path.length - 1]] = value
}

function getNestedValue(source: any, path: string[]) {
  return path.reduce((current, key) => (current ? current[key] : undefined), source)
}

function SummaryBlock({
  title,
  description,
  values,
}: {
  title: string
  description?: string
  values: Array<{ label: string; value?: string | string[] }>
}) {
  const filtered = values.filter((item) => {
    if (Array.isArray(item.value)) return item.value.length > 0
    return Boolean(item.value)
  })

  if (filtered.length === 0) return null

  return (
    <div className={sectionCard}>
      <div className="p-5">
        <h3 className="text-base font-semibold text-text-primary">{title}</h3>
        {description && <p className="text-sm text-text-muted mt-1">{description}</p>}
        <div className="mt-4 space-y-4">
          {filtered.map((item) => (
            <div key={item.label}>
              <div className="text-sm font-medium text-text-primary mb-1">{item.label}</div>
              {Array.isArray(item.value) ? (
                <div className="flex flex-wrap gap-1.5">
                  {item.value.map((token) => (
                    <span
                      key={`${item.label}-${token}`}
                      className="text-xs px-2 py-0.5 rounded-full bg-elevated text-text-secondary"
                    >
                      {token}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">{item.value}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  multiline,
  rows = 3,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  multiline?: boolean
  rows?: number
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-text-secondary mb-1.5">{label}</label>
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={textareaClass}
          rows={rows}
          placeholder={placeholder}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={inputClass}
          placeholder={placeholder}
        />
      )}
    </div>
  )
}

export default function WorldBibleView({ data, loading, projectId, onUpdate }: WorldBibleViewProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editData, setEditData] = useState<any>(createEmptyWorldBible(projectId))
  const [jsonText, setJsonText] = useState('')
  const [jsonError, setJsonError] = useState('')

  useEffect(() => {
    const next = data ? JSON.parse(JSON.stringify(data)) : createEmptyWorldBible(projectId)
    setEditData(next)
    setJsonText(JSON.stringify(next, null, 2))
    setJsonError('')
  }, [data, projectId])

  const worldviewText = editData?.user_worldview_text || ''

  const updateField = (path: string[], value: any) => {
    setEditData((prev: any) => {
      const next = JSON.parse(JSON.stringify(prev || createEmptyWorldBible(projectId)))
      setNestedValue(next, path, value)
      setJsonText(JSON.stringify(next, null, 2))
      return next
    })
  }

  const updateArrayText = (path: string[], value: string) => {
    updateField(path, splitLines(value))
  }

  const handleJsonChange = (value: string) => {
    setJsonText(value)
    try {
      const parsed = JSON.parse(value)
      setEditData(parsed)
      setJsonError('')
    } catch (error) {
      setJsonError(error instanceof Error ? error.message : 'JSON 解析失败')
    }
  }

  const handleCancel = () => {
    const next = data ? JSON.parse(JSON.stringify(data)) : createEmptyWorldBible(projectId)
    setEditData(next)
    setJsonText(JSON.stringify(next, null, 2))
    setJsonError('')
    setIsEditing(false)
  }

  const handleSave = async () => {
    if (jsonError) return
    setSaving(true)
    try {
      const payload = {
        ...editData,
        project_id: editData?.project_id || projectId,
      }
      await api.worldBible.update(projectId, payload)
      setIsEditing(false)
      onUpdate?.()
    } catch (error) {
      console.error('保存世界观失败:', error)
    } finally {
      setSaving(false)
    }
  }

  const summaryCards = useMemo(
    () => [
      {
        title: '世界观框架',
        description: '用于约束题材、时代、社会结构和基本设定。',
        values: [
          { label: '主类型', value: getNestedValue(editData, ['world_framework', 'genre']) },
          { label: '子类型', value: getNestedValue(editData, ['world_framework', 'sub_genre']) },
          { label: '时代背景', value: getNestedValue(editData, ['world_framework', 'era_setting']) },
          { label: '技术水平', value: getNestedValue(editData, ['world_framework', 'technology_level']) },
          { label: '力量体系', value: getNestedValue(editData, ['world_framework', 'power_system']) },
          { label: '社会结构', value: getNestedValue(editData, ['world_framework', 'social_structure']) },
          { label: '地理概览', value: getNestedValue(editData, ['world_framework', 'geography_overview']) },
          { label: '核心概念', value: getNestedValue(editData, ['world_framework', 'key_concepts']) },
          { label: '整体基调', value: getNestedValue(editData, ['world_framework', 'tone_and_mood']) },
        ],
      },
      {
        title: '视觉锚定',
        description: '这些约束会直接影响后续绘图指令生成。',
        values: [
          { label: '画风方向', value: getNestedValue(editData, ['visual_anchoring', 'art_style']) },
          { label: '英文风格', value: getNestedValue(editData, ['visual_anchoring', 'art_style_en']) },
          { label: '主色调', value: getNestedValue(editData, ['visual_anchoring', 'color_palette', 'primary']) },
          { label: '辅助色', value: getNestedValue(editData, ['visual_anchoring', 'color_palette', 'secondary']) },
          { label: '点缀色', value: getNestedValue(editData, ['visual_anchoring', 'color_palette', 'accent']) },
          { label: '情绪色彩', value: getNestedValue(editData, ['visual_anchoring', 'color_palette', 'mood']) },
          { label: '具体颜色', value: getNestedValue(editData, ['visual_anchoring', 'color_palette', 'specific_colors']) },
          { label: '光照逻辑', value: getNestedValue(editData, ['visual_anchoring', 'lighting_style']) },
          { label: '材质表达', value: getNestedValue(editData, ['visual_anchoring', 'texture_style']) },
          { label: '氛围关键词', value: getNestedValue(editData, ['visual_anchoring', 'atmosphere_keywords']) },
          { label: '禁用元素', value: getNestedValue(editData, ['visual_anchoring', 'forbidden_elements']) },
        ],
      },
      {
        title: '角色视觉规则',
        values: [
          { label: '面部方向', value: getNestedValue(editData, ['character_visual_rules', 'face_style']) },
          { label: '身材比例', value: getNestedValue(editData, ['character_visual_rules', 'body_proportion']) },
          { label: '服装体系', value: getNestedValue(editData, ['character_visual_rules', 'clothing_system']) },
          { label: '服装材质', value: getNestedValue(editData, ['character_visual_rules', 'clothing_materials']) },
          { label: '发型规则', value: getNestedValue(editData, ['character_visual_rules', 'hair_style_rules']) },
          { label: '配饰规则', value: getNestedValue(editData, ['character_visual_rules', 'accessory_rules']) },
        ],
      },
      {
        title: '场景与物品规则',
        values: [
          { label: '建筑风格', value: getNestedValue(editData, ['scene_visual_rules', 'architecture_style']) },
          { label: '景观风格', value: getNestedValue(editData, ['scene_visual_rules', 'landscape_style']) },
          { label: '室内风格', value: getNestedValue(editData, ['scene_visual_rules', 'interior_style']) },
          { label: '天气模式', value: getNestedValue(editData, ['scene_visual_rules', 'weather_patterns']) },
          { label: '武器/器物方向', value: getNestedValue(editData, ['item_visual_rules', 'weapon_style']) },
          { label: '材质系统', value: getNestedValue(editData, ['item_visual_rules', 'material_system']) },
          { label: '工艺细节', value: getNestedValue(editData, ['item_visual_rules', 'craftsmanship']) },
        ],
      },
    ],
    [editData]
  )

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={`${sectionCard} p-5 animate-pulse`}>
            <div className="h-5 bg-elevated rounded w-28 mb-4" />
            <div className="space-y-3">
              <div className="h-4 bg-elevated rounded w-4/5" />
              <div className="h-4 bg-elevated rounded w-3/5" />
              <div className="h-4 bg-elevated rounded w-2/3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (isEditing) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between sticky top-0 bg-base z-10 py-2">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">编辑世界观</h2>
            <p className="text-sm text-text-muted mt-1">支持直接写整段设定，结构字段会作为辅助约束保留。</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCancel}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary hover:bg-elevated rounded-md transition-colors"
            >
              <X size={14} />
              取消
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !!jsonError}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-accent text-white rounded-md hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              <Save size={14} />
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>

        <div className={`${sectionCard} p-5`}>
          <div className="flex items-center gap-2 mb-3">
            <FileText size={18} className="text-accent" />
            <h3 className="text-base font-semibold text-text-primary">手工世界观设定</h3>
          </div>
          <p className="text-sm text-text-muted mb-4">
            这里可以直接输入长段文字。后续角色、场景、物品提示词会一并参考这段补充设定。
          </p>
          <textarea
            value={worldviewText}
            onChange={(e) => updateField(['user_worldview_text'], e.target.value)}
            className={textareaClass}
            rows={14}
            placeholder="例如：这是一个偏现实的现代豪门商战世界，画面需要影视剧质感，服装以高定西装、礼服、都市通勤穿搭为主，避免古风、二次元、赛博朋克、夸张奇幻特效……"
          />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className={`${sectionCard} p-5 space-y-4`}>
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-accent" />
              <h3 className="text-base font-semibold text-text-primary">结构化世界观</h3>
            </div>
            <Field
              label="小说标题"
              value={getNestedValue(editData, ['novel_title']) || ''}
              onChange={(value) => updateField(['novel_title'], value)}
              placeholder="可选"
            />
            <Field
              label="主类型"
              value={getNestedValue(editData, ['world_framework', 'genre']) || ''}
              onChange={(value) => updateField(['world_framework', 'genre'], value)}
              placeholder="都市 / 玄幻 / 历史 / 科幻..."
            />
            <Field
              label="子类型"
              value={getNestedValue(editData, ['world_framework', 'sub_genre']) || ''}
              onChange={(value) => updateField(['world_framework', 'sub_genre'], value)}
              placeholder="豪门商战 / 校园成长 / 末日生存..."
            />
            <Field
              label="时代背景"
              value={getNestedValue(editData, ['world_framework', 'era_setting']) || ''}
              onChange={(value) => updateField(['world_framework', 'era_setting'], value)}
              placeholder="现代 / 近未来 / 架空古代..."
            />
            <Field
              label="技术水平"
              value={getNestedValue(editData, ['world_framework', 'technology_level']) || ''}
              onChange={(value) => updateField(['world_framework', 'technology_level'], value)}
              placeholder="现实都市 / 工业时代 / 高科技社会..."
            />
            <Field
              label="力量体系"
              value={getNestedValue(editData, ['world_framework', 'power_system']) || ''}
              onChange={(value) => updateField(['world_framework', 'power_system'], value)}
              placeholder="没有超自然就直接写“无超自然力量体系”"
            />
            <Field
              label="社会结构"
              value={getNestedValue(editData, ['world_framework', 'social_structure']) || ''}
              onChange={(value) => updateField(['world_framework', 'social_structure'], value)}
              multiline
              rows={4}
            />
            <Field
              label="地理概览"
              value={getNestedValue(editData, ['world_framework', 'geography_overview']) || ''}
              onChange={(value) => updateField(['world_framework', 'geography_overview'], value)}
              multiline
              rows={4}
            />
            <Field
              label="核心概念"
              value={joinLines(getNestedValue(editData, ['world_framework', 'key_concepts']))}
              onChange={(value) => updateArrayText(['world_framework', 'key_concepts'], value)}
              multiline
              rows={4}
              placeholder="每行一个，或逗号分隔"
            />
            <Field
              label="整体基调"
              value={getNestedValue(editData, ['world_framework', 'tone_and_mood']) || ''}
              onChange={(value) => updateField(['world_framework', 'tone_and_mood'], value)}
              multiline
              rows={3}
            />
          </div>

          <div className={`${sectionCard} p-5 space-y-4`}>
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-accent" />
              <h3 className="text-base font-semibold text-text-primary">视觉约束</h3>
            </div>
            <Field
              label="画风方向"
              value={getNestedValue(editData, ['visual_anchoring', 'art_style']) || ''}
              onChange={(value) => updateField(['visual_anchoring', 'art_style'], value)}
              placeholder="偏写实影视感 / 克制国风插画 / 近未来工业设计..."
            />
            <Field
              label="英文画风"
              value={getNestedValue(editData, ['visual_anchoring', 'art_style_en']) || ''}
              onChange={(value) => updateField(['visual_anchoring', 'art_style_en'], value)}
            />
            <Field
              label="主色调"
              value={getNestedValue(editData, ['visual_anchoring', 'color_palette', 'primary']) || ''}
              onChange={(value) => updateField(['visual_anchoring', 'color_palette', 'primary'], value)}
            />
            <Field
              label="辅助色"
              value={getNestedValue(editData, ['visual_anchoring', 'color_palette', 'secondary']) || ''}
              onChange={(value) => updateField(['visual_anchoring', 'color_palette', 'secondary'], value)}
            />
            <Field
              label="点缀色"
              value={getNestedValue(editData, ['visual_anchoring', 'color_palette', 'accent']) || ''}
              onChange={(value) => updateField(['visual_anchoring', 'color_palette', 'accent'], value)}
            />
            <Field
              label="情绪色彩"
              value={getNestedValue(editData, ['visual_anchoring', 'color_palette', 'mood']) || ''}
              onChange={(value) => updateField(['visual_anchoring', 'color_palette', 'mood'], value)}
            />
            <Field
              label="具体颜色"
              value={joinLines(getNestedValue(editData, ['visual_anchoring', 'color_palette', 'specific_colors']))}
              onChange={(value) => updateArrayText(['visual_anchoring', 'color_palette', 'specific_colors'], value)}
              multiline
              rows={4}
              placeholder="可写色名、色值，每行一个"
            />
            <Field
              label="光照逻辑"
              value={getNestedValue(editData, ['visual_anchoring', 'lighting_style']) || ''}
              onChange={(value) => updateField(['visual_anchoring', 'lighting_style'], value)}
            />
            <Field
              label="材质表达"
              value={getNestedValue(editData, ['visual_anchoring', 'texture_style']) || ''}
              onChange={(value) => updateField(['visual_anchoring', 'texture_style'], value)}
            />
            <Field
              label="氛围关键词"
              value={joinLines(getNestedValue(editData, ['visual_anchoring', 'atmosphere_keywords']))}
              onChange={(value) => updateArrayText(['visual_anchoring', 'atmosphere_keywords'], value)}
              multiline
              rows={4}
            />
            <Field
              label="禁用元素"
              value={joinLines(getNestedValue(editData, ['visual_anchoring', 'forbidden_elements']))}
              onChange={(value) => updateArrayText(['visual_anchoring', 'forbidden_elements'], value)}
              multiline
              rows={4}
              placeholder="例如：古风发冠、霓虹赛博灯牌、夸张魔法阵..."
            />
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className={`${sectionCard} p-5 space-y-4`}>
            <h3 className="text-base font-semibold text-text-primary">角色规则</h3>
            <Field
              label="面部方向"
              value={getNestedValue(editData, ['character_visual_rules', 'face_style']) || ''}
              onChange={(value) => updateField(['character_visual_rules', 'face_style'], value)}
            />
            <Field
              label="英文面部方向"
              value={getNestedValue(editData, ['character_visual_rules', 'face_style_en']) || ''}
              onChange={(value) => updateField(['character_visual_rules', 'face_style_en'], value)}
            />
            <Field
              label="身材比例"
              value={getNestedValue(editData, ['character_visual_rules', 'body_proportion']) || ''}
              onChange={(value) => updateField(['character_visual_rules', 'body_proportion'], value)}
            />
            <Field
              label="服装体系"
              value={getNestedValue(editData, ['character_visual_rules', 'clothing_system']) || ''}
              onChange={(value) => updateField(['character_visual_rules', 'clothing_system'], value)}
              multiline
              rows={4}
            />
            <Field
              label="服装材质"
              value={getNestedValue(editData, ['character_visual_rules', 'clothing_materials']) || ''}
              onChange={(value) => updateField(['character_visual_rules', 'clothing_materials'], value)}
            />
            <Field
              label="发型规则"
              value={getNestedValue(editData, ['character_visual_rules', 'hair_style_rules']) || ''}
              onChange={(value) => updateField(['character_visual_rules', 'hair_style_rules'], value)}
            />
            <Field
              label="配饰规则"
              value={getNestedValue(editData, ['character_visual_rules', 'accessory_rules']) || ''}
              onChange={(value) => updateField(['character_visual_rules', 'accessory_rules'], value)}
            />
          </div>

          <div className={`${sectionCard} p-5 space-y-4`}>
            <h3 className="text-base font-semibold text-text-primary">场景规则</h3>
            <Field
              label="建筑风格"
              value={getNestedValue(editData, ['scene_visual_rules', 'architecture_style']) || ''}
              onChange={(value) => updateField(['scene_visual_rules', 'architecture_style'], value)}
            />
            <Field
              label="景观风格"
              value={getNestedValue(editData, ['scene_visual_rules', 'landscape_style']) || ''}
              onChange={(value) => updateField(['scene_visual_rules', 'landscape_style'], value)}
            />
            <Field
              label="室内风格"
              value={getNestedValue(editData, ['scene_visual_rules', 'interior_style']) || ''}
              onChange={(value) => updateField(['scene_visual_rules', 'interior_style'], value)}
            />
            <Field
              label="天气模式"
              value={getNestedValue(editData, ['scene_visual_rules', 'weather_patterns']) || ''}
              onChange={(value) => updateField(['scene_visual_rules', 'weather_patterns'], value)}
              multiline
              rows={4}
            />
          </div>

          <div className={`${sectionCard} p-5 space-y-4`}>
            <h3 className="text-base font-semibold text-text-primary">物品规则</h3>
            <Field
              label="武器/器物方向"
              value={getNestedValue(editData, ['item_visual_rules', 'weapon_style']) || ''}
              onChange={(value) => updateField(['item_visual_rules', 'weapon_style'], value)}
            />
            <Field
              label="材质系统"
              value={getNestedValue(editData, ['item_visual_rules', 'material_system']) || ''}
              onChange={(value) => updateField(['item_visual_rules', 'material_system'], value)}
            />
            <Field
              label="工艺细节"
              value={getNestedValue(editData, ['item_visual_rules', 'craftsmanship']) || ''}
              onChange={(value) => updateField(['item_visual_rules', 'craftsmanship'], value)}
              multiline
              rows={4}
            />
          </div>
        </div>

        <div className={`${sectionCard} p-5`}>
          <div className="flex items-center gap-2 mb-3">
            <Braces size={18} className="text-accent" />
            <h3 className="text-base font-semibold text-text-primary">高级 JSON 编辑</h3>
          </div>
          <p className="text-sm text-text-muted mb-4">
            用于直接调整完整世界观数据结构。上面的表单会同步到这里。
          </p>
          <textarea
            value={jsonText}
            onChange={(e) => handleJsonChange(e.target.value)}
            className="w-full min-h-[420px] bg-base border border-border rounded-lg px-3 py-3 text-sm text-text-primary font-mono focus:outline-none focus:border-accent resize-y"
            spellCheck={false}
          />
          {jsonError && (
            <div className="mt-3 flex items-start gap-2 text-sm text-red-400">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>JSON 有误，当前不能保存：{jsonError}</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  const hasAnyData = Boolean(
    worldviewText ||
      Object.values(editData?.world_framework || {}).some((value) =>
        Array.isArray(value) ? value.length > 0 : Boolean(value)
      ) ||
      Object.values(editData?.visual_anchoring || {}).some((value) =>
        Array.isArray(value) ? value.length > 0 : typeof value === 'object' ? Object.values(value || {}).some(Boolean) : Boolean(value)
      )
  )

  if (!hasAnyData) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-text-muted">
        <BookOpen size={48} className="mb-4 opacity-30" />
        <p className="text-sm">暂无世界观数据</p>
        <p className="text-xs mt-1">可以先跑流水线自动识别，也可以直接点右上角手工填写。</p>
        <button
          onClick={() => setIsEditing(true)}
          className="mt-5 flex items-center gap-2 px-4 py-2 rounded-lg bg-accent text-white hover:bg-accent/90 transition-colors"
        >
          <Edit2 size={15} />
          新建世界观
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">世界观设定</h2>
          <p className="text-sm text-text-muted mt-1">自动识别结果和手工补充会一起参与后续绘图指令生成。</p>
        </div>
        <button
          onClick={() => setIsEditing(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary hover:bg-elevated rounded-md transition-colors"
        >
          <Edit2 size={14} />
          编辑
        </button>
      </div>

      {worldviewText && (
        <div className={sectionCard}>
          <div className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <FileText size={18} className="text-accent" />
              <h3 className="text-base font-semibold text-text-primary">手工世界观设定</h3>
            </div>
            <p className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">{worldviewText}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {summaryCards.map((card) => (
          <SummaryBlock
            key={card.title}
            title={card.title}
            description={card.description}
            values={card.values}
          />
        ))}
      </div>
    </div>
  )
}
