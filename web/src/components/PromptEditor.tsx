import { useState, useEffect } from 'react'
import { Settings, Save, RotateCcw, ChevronLeft, ChevronRight, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import { api } from '@/api/client'

interface PromptTemplate {
  name: string
  description: string
  system_prompt: string
  user_prompt: string
}

interface PromptListItem {
  name: string
  description: string
  has_system: boolean
  has_user: boolean
}

export default function PromptEditor() {
  const [prompts, setPrompts] = useState<PromptListItem[]>([])
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null)
  const [currentPrompt, setCurrentPrompt] = useState<PromptTemplate | null>(null)
  const [editingSystem, setEditingSystem] = useState('')
  const [editingUser, setEditingUser] = useState('')
  const [loading, setLoading] = useState(false)
  const [listLoading, setListLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    loadPrompts()
  }, [])

  const loadPrompts = async () => {
    setListLoading(true)
    setLoadError(null)
    try {
      const data = await api.prompts.list()
      setPrompts(data)
      if (data.length > 0 && !selectedPrompt) {
        selectPrompt(data[0].name)
      }
    } catch (e) {
      console.error('Failed to load prompts:', e)
      setLoadError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setListLoading(false)
    }
  }

  const selectPrompt = async (name: string) => {
    setSelectedPrompt(name)
    setLoading(true)
    setSaveStatus('idle')
    try {
      const data = await api.prompts.get(name)
      setCurrentPrompt(data)
      setEditingSystem(data.system_prompt)
      setEditingUser(data.user_prompt)
    } catch (e) {
      console.error('Failed to load prompt:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!selectedPrompt) return
    setSaving(true)
    setSaveStatus('idle')
    try {
      await api.prompts.update(selectedPrompt, {
        system_prompt: editingSystem,
        user_prompt: editingUser,
      })
      setSaveStatus('success')
      await selectPrompt(selectedPrompt)
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch (e) {
      console.error('Failed to save prompt:', e)
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } finally {
      setSaving(false)
    }
  }

  const hasChanges = currentPrompt && (
    editingSystem !== currentPrompt.system_prompt ||
    editingUser !== currentPrompt.user_prompt
  )

  return (
    <div className="flex h-full">
      <div 
        className={`bg-surface border-r border-border flex flex-col transition-all duration-300 ${sidebarOpen ? 'w-72' : 'w-0 overflow-hidden'}`}
      >
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings size={18} className="text-accent" />
            <h2 className="font-semibold text-text-primary">提示词管理</h2>
          </div>
          <button 
            onClick={loadPrompts} 
            disabled={listLoading}
            className="p-1 rounded hover:bg-elevated text-text-muted hover:text-text-primary transition-colors"
            title="刷新"
          >
            {listLoading ? <Loader2 size={14} className="animate-spin" /> : <RotateCcw size={14} />}
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          {listLoading ? (
            <div className="flex flex-col items-center justify-center py-8 gap-2">
              <Loader2 size={24} className="animate-spin text-text-muted" />
              <span className="text-sm text-text-muted">加载中...</span>
            </div>
          ) : loadError ? (
            <div className="flex flex-col items-center justify-center py-8 gap-2">
              <AlertCircle size={24} className="text-error" />
              <span className="text-sm text-text-muted">{loadError}</span>
              <button 
                onClick={loadPrompts} 
                className="text-sm text-accent hover:text-accent-hover transition-colors"
              >
                重试
              </button>
            </div>
          ) : prompts.length === 0 ? (
            <div className="text-sm text-text-muted text-center py-8">
              暂无提示词
            </div>
          ) : (
            prompts.map((prompt) => (
              <button
                key={prompt.name}
                onClick={() => selectPrompt(prompt.name)}
                className={`w-full text-left p-3 rounded-lg mb-2 transition-all duration-200 border ${
                  selectedPrompt === prompt.name
                    ? 'bg-elevated border-accent text-text-primary'
                    : 'bg-transparent border-border text-text-secondary hover:bg-elevated hover:border-border-hover hover:text-text-primary'
                }`}
              >
                <div className="font-medium text-sm truncate">{prompt.description || prompt.name}</div>
                <div className="text-xs text-text-muted mt-1 truncate">{prompt.name}</div>
                <div className="flex gap-2 mt-2">
                  {prompt.has_system && (
                    <span className="px-2 py-0.5 text-xs rounded" style={{background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6'}}>System</span>
                  )}
                  {prompt.has_user && (
                    <span className="px-2 py-0.5 text-xs rounded" style={{background: 'rgba(34, 197, 94, 0.1)', color: '#22c55e'}}>User</span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="self-center -ml-3 z-10 w-6 h-16 bg-surface border-y border-r border-border hover:bg-elevated rounded-r-lg flex items-center justify-center transition-colors"
      >
        {sidebarOpen ? <ChevronLeft size={14} className="text-text-muted" /> : <ChevronRight size={14} className="text-text-muted" />}
      </button>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-4 border-b border-border bg-surface flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-text-primary">{currentPrompt?.description || selectedPrompt || '选择一个提示词'}</h1>
            {currentPrompt && (
              <p className="text-sm text-text-muted mt-1">{currentPrompt.name}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {saveStatus === 'success' && (
              <div className="flex items-center gap-2 text-success text-sm">
                <CheckCircle size={16} />
                <span>已保存</span>
              </div>
            )}
            {saveStatus === 'error' && (
              <div className="flex items-center gap-2 text-error text-sm">
                <AlertCircle size={16} />
                <span>保存失败</span>
              </div>
            )}
            <button
              onClick={handleSave}
              disabled={saving || !hasChanges}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
                hasChanges
                  ? 'bg-accent text-white hover:bg-accent-hover'
                  : 'bg-elevated text-text-muted cursor-not-allowed'
              }`}
            >
              {saving ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>保存中...</span>
                </>
              ) : (
                <>
                  <Save size={16} />
                  <span>保存</span>
                </>
              )}
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-2">
              <Loader2 size={24} className="animate-spin text-text-muted" />
              <span className="text-sm text-text-muted">加载中...</span>
            </div>
          </div>
        ) : !currentPrompt ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-text-muted">
              <Settings size={32} className="opacity-30" />
              <span>请在左侧选择一个提示词进行编辑</span>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-hidden flex flex-col lg:flex-row">
            <div className="flex-1 flex flex-col border-r border-border">
              <div className="p-3 border-b border-border flex items-center gap-2" style={{background: 'rgba(59, 130, 246, 0.1)'}}>
                <div className="w-2 h-2 rounded-full" style={{background: '#3b82f6'}} />
                <span className="font-medium text-sm" style={{color: '#3b82f6'}}>System Prompt</span>
              </div>
              <textarea
                value={editingSystem}
                onChange={(e) => setEditingSystem(e.target.value)}
                className="flex-1 w-full p-4 bg-base text-text-primary font-mono text-sm resize-none outline-none"
                placeholder="系统提示词..."
                spellCheck={false}
              />
            </div>

            <div className="flex-1 flex flex-col">
              <div className="p-3 border-b border-border flex items-center gap-2" style={{background: 'rgba(34, 197, 94, 0.1)'}}>
                <div className="w-2 h-2 rounded-full" style={{background: '#22c55e'}} />
                <span className="font-medium text-sm" style={{color: '#22c55e'}}>User Prompt</span>
              </div>
              <textarea
                value={editingUser}
                onChange={(e) => setEditingUser(e.target.value)}
                className="flex-1 w-full p-4 bg-base text-text-primary font-mono text-sm resize-none outline-none"
                placeholder="用户提示词..."
                spellCheck={false}
              />
            </div>
          </div>
        )}

        <div className="p-4 border-t border-border bg-surface">
          <div className="flex items-start gap-3 text-sm text-text-muted">
            <AlertCircle size={20} className="text-warning shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-text-secondary">提示词使用说明</p>
              <ul className="mt-1 space-y-1 text-xs">
                <li>• 使用 <code className="bg-elevated px-1 py-0.5 rounded border border-border">{'{{ variable }}'}</code> 作为变量占位符</li>
                <li>• 修改提示词后点击「保存」按钮生效</li>
                <li>• 建议先备份原始提示词再进行修改</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
