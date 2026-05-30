import { BookOpen, Edit2, Check, X, Save } from 'lucide-react'
import { useState, useEffect } from 'react'
import { api } from '@/api/client'

interface WorldBibleViewProps {
  data: any
  loading?: boolean
  projectId: string
  onUpdate?: () => void
}

const defaultColors = ['#f97316', '#3b82f6', '#22c55e', '#a855f7', '#ec4899', '#eab308']

function transformToCategories(data: any): { name: string; color: string; items: { name: string; keywords: string[]; description: string }[] }[] {
  if (!data) return []
  if (data.categories) return data.categories

  const categories: { name: string; color: string; items: { name: string; keywords: string[]; description: string }[] }[] = []

  if (data.visual_anchoring) {
    const items: { name: string; keywords: string[]; description: string }[] = []
    const va = data.visual_anchoring
    if (va.art_style) items.push({ name: '画风', keywords: [va.art_style], description: va.art_style })
    if (va.color_system) items.push({ name: '色彩体系', keywords: va.color_system instanceof Array ? va.color_system : [va.color_system], description: '' })
    if (va.lighting_style) items.push({ name: '光影风格', keywords: [va.lighting_style], description: va.lighting_style })
    if (va.material_style) items.push({ name: '材质风格', keywords: [va.material_style], description: va.material_style })
    if (va.atmosphere_keywords) items.push({ name: '氛围关键词', keywords: va.atmosphere_keywords instanceof Array ? va.atmosphere_keywords : [va.atmosphere_keywords], description: '' })
    if (items.length > 0) categories.push({ name: '视觉锚定', color: '#f97316', items })
  }

  if (data.world_framework) {
    const items: { name: string; keywords: string[]; description: string }[] = []
    const wf = data.world_framework
    if (wf.genre) items.push({ name: '类型', keywords: [wf.genre], description: '' })
    if (wf.era) items.push({ name: '时代', keywords: [wf.era], description: '' })
    if (wf.power_system) items.push({ name: '力量体系', keywords: [wf.power_system], description: '' })
    if (wf.geography) items.push({ name: '地理', keywords: [], description: wf.geography })
    if (items.length > 0) categories.push({ name: '世界观框架', color: '#3b82f6', items })
  }

  if (data.character_visual_rules) {
    const items: { name: string; keywords: string[]; description: string }[] = []
    const cr = data.character_visual_rules
    if (cr.face_style) items.push({ name: '面部风格', keywords: [cr.face_style], description: '' })
    if (cr.clothing_system) items.push({ name: '服饰体系', keywords: [cr.clothing_system], description: '' })
    if (cr.hairstyle_rules) items.push({ name: '发型规则', keywords: [cr.hairstyle_rules], description: '' })
    if (items.length > 0) categories.push({ name: '角色视觉规范', color: '#22c55e', items })
  }

  if (data.scene_visual_rules) {
    const items: { name: string; keywords: string[]; description: string }[] = []
    const sr = data.scene_visual_rules
    if (sr.architecture_style) items.push({ name: '建筑风格', keywords: [sr.architecture_style], description: '' })
    if (sr.landscape_style) items.push({ name: '景观风格', keywords: [sr.landscape_style], description: '' })
    if (items.length > 0) categories.push({ name: '场景视觉规范', color: '#a855f7', items })
  }

  if (data.item_visual_rules) {
    const items: { name: string; keywords: string[]; description: string }[] = []
    const ir = data.item_visual_rules
    if (ir.weapon_style) items.push({ name: '武器风格', keywords: [ir.weapon_style], description: '' })
    if (ir.material_system) items.push({ name: '材质体系', keywords: [ir.material_system], description: '' })
    if (items.length > 0) categories.push({ name: '物品视觉规范', color: '#ec4899', items })
  }

  if (categories.length === 0 && typeof data === 'object') {
    const keys = Object.keys(data)
    for (const key of keys) {
      const val = data[key]
      if (typeof val === 'string') {
        categories.push({ name: key, color: defaultColors[categories.length % defaultColors.length], items: [{ name: key, keywords: [], description: val }] })
      } else if (typeof val === 'object' && val !== null) {
        const items = Object.entries(val).map(([k, v]) => ({
          name: k,
          keywords: [],
          description: typeof v === 'string' ? v : JSON.stringify(v),
        }))
        categories.push({ name: key, color: defaultColors[categories.length % defaultColors.length], items })
      }
    }
  }

  return categories
}

export default function WorldBibleView({ data, loading, projectId, onUpdate }: WorldBibleViewProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState<any>(null)
  const [saving, setSaving] = useState(false)
  const [categories, setCategories] = useState<any[]>([])

  useEffect(() => {
    if (data) {
      setEditData(JSON.parse(JSON.stringify(data)))
      setCategories(transformToCategories(data))
    }
  }, [data])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-surface border border-border rounded-xl p-5 animate-pulse">
            <div className="h-5 bg-elevated rounded w-24 mb-4" />
            <div className="space-y-3">
              <div className="h-4 bg-elevated rounded w-3/4" />
              <div className="h-4 bg-elevated rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!categories.length) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-text-muted">
        <BookOpen size={48} className="mb-4 opacity-30" />
        <p className="text-sm">暂无世界观数据</p>
        <p className="text-xs mt-1">运行流水线后将自动生成世界观设定</p>
      </div>
    )
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.worldBible.update(projectId, editData)
      setIsEditing(false)
      onUpdate?.()
    } catch (error) {
      console.error('保存失败:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setEditData(JSON.parse(JSON.stringify(data)))
    setIsEditing(false)
  }

  if (isEditing) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">编辑世界观</h2>
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
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-accent text-white rounded-md hover:bg-accent/90 transition-colors disabled:opacity-50"
            >
              {saving ? <Save size={14} className="animate-spin" /> : <Save size={14} />}
              保存
            </button>
          </div>
        </div>

        <textarea
          value={JSON.stringify(editData, null, 2)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value)
              setEditData(parsed)
            } catch {}
          }}
          className="w-full h-[600px] bg-surface border border-border rounded-xl p-4 text-sm font-mono text-text-primary placeholder-text-muted focus:outline-none focus:border-accent resize-none"
        />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">世界观设定</h2>
        <button
          onClick={() => setIsEditing(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-text-secondary hover:text-text-primary hover:bg-elevated rounded-md transition-colors"
        >
          <Edit2 size={14} />
          编辑
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {categories.map((category, idx) => (
          <div
            key={category.name}
            className="bg-surface border border-border rounded-xl overflow-hidden transition-all duration-200 hover:border-border-hover"
          >
            <div
              className="h-1.5"
              style={{ backgroundColor: category.color || defaultColors[idx % defaultColors.length] }}
            />
            <div className="p-5">
              <h3 className="text-base font-semibold text-text-primary mb-4">{category.name}</h3>
              <div className="space-y-4">
                {category.items.map((item: any) => (
                  <div key={item.name} className="group">
                    <div className="text-sm font-medium text-text-primary mb-1">{item.name}</div>
                    {item.keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {item.keywords.map((kw: string) => (
                          <span
                            key={kw}
                            className="text-xs px-2 py-0.5 rounded-full bg-elevated text-text-secondary"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}
                    {item.description && (
                      <p className="text-xs text-text-muted leading-relaxed">{item.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
