import { useState, useEffect } from 'react'
import { Save, Wifi, WifiOff, Loader2, Key, Server, FolderOpen } from 'lucide-react'
import { api } from '@/api/client'

interface SettingsData {
  llm: {
    api_key: string
    base_url: string
    model: string
    extraction_model: string
    prompt_model: string
    vision_model: string
  }
  image: {
    enabled: boolean
    backend: string
    chatgpt2api: {
      base_url: string
      api_key: string
      model: string
    }
  }
  output: {
    dir: string
  }
}

const defaultSettings: SettingsData = {
  llm: {
    api_key: '',
    base_url: '',
    model: '',
    extraction_model: '',
    prompt_model: '',
    vision_model: '',
  },
  image: {
    enabled: true,
    backend: 'chatgpt2api',
    chatgpt2api: {
      base_url: 'http://localhost:5000/v1',
      api_key: 'biaooo',
      model: 'gpt-image-2',
    },
  },
  output: {
    dir: './output',
  },
}

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData>(defaultSettings)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null)
  const [testMessage, setTestMessage] = useState('')
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    api.settings
      .get()
      .then((data) => {
        const merged: SettingsData = {
          llm: { ...defaultSettings.llm, ...data.llm },
          image: {
            ...defaultSettings.image,
            ...data.image,
            chatgpt2api: {
              ...defaultSettings.image.chatgpt2api,
              ...(data.image?.chatgpt2api || {}),
            },
          },
          output: { ...defaultSettings.output, ...data.output },
        }
        setSettings(merged)
        setLoaded(true)
      })
      .catch(() => setLoaded(true))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.settings.update(settings)
    } catch {} finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    setTestMessage('')
    try {
      const result = await api.settings.testConnection({
        api_key: settings.llm.api_key,
        base_url: settings.llm.base_url,
        model: settings.llm.model,
      })
      if (result?.success) {
        setTestResult('success')
        setTestMessage(result.message || '连接成功')
      } else {
        setTestResult('error')
        setTestMessage(result?.detail || result?.message || '连接失败')
      }
    } catch (error) {
      setTestResult('error')
      setTestMessage(error instanceof Error ? error.message : '连接失败')
    } finally {
      setTesting(false)
    }
  }

  const updateLlm = (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, llm: { ...prev.llm, [key]: value } }))
  }

  const updateImageChatgpt2api = (key: string, value: string) => {
    setSettings((prev) => ({
      ...prev,
      image: {
        ...prev.image,
        chatgpt2api: { ...prev.image.chatgpt2api, [key]: value },
      },
    }))
  }

  if (!loaded) {
    return (
      <div className="p-6 space-y-6 max-w-2xl">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-surface border border-border rounded-xl p-5 animate-pulse">
            <div className="h-5 bg-elevated rounded w-32 mb-4" />
            <div className="space-y-3">
              <div className="h-10 bg-elevated rounded" />
              <div className="h-10 bg-elevated rounded" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-lg font-semibold text-text-primary">设置</h1>
        <p className="text-sm text-text-muted mt-1">配置 API 连接和输出参数</p>
      </div>

      <div className="bg-surface border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-5">
          <Key size={16} className="text-accent" />
          <h2 className="text-base font-semibold text-text-primary">拆文 LLM 配置</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1.5">API 地址</label>
            <input
              type="text"
              value={settings.llm.base_url}
              onChange={(e) => updateLlm('base_url', e.target.value)}
              placeholder="https://api.openai.com/v1"
              className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent transition-colors duration-200 font-mono"
            />
          </div>
          <div>
            <label className="block text-sm text-text-secondary mb-1.5">API Key</label>
            <input
              type="password"
              value={settings.llm.api_key}
              onChange={(e) => updateLlm('api_key', e.target.value)}
              placeholder="sk-..."
              className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent transition-colors duration-200 font-mono"
            />
          </div>
          <div>
            <label className="block text-sm text-text-secondary mb-1.5">模型名称</label>
            <input
              type="text"
              value={settings.llm.model}
              onChange={(e) => updateLlm('model', e.target.value)}
              placeholder="gpt-4o / deepseek-chat"
              className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent transition-colors duration-200 font-mono"
            />
          </div>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-5">
          <Server size={16} className="text-emerald-400" />
          <h2 className="text-base font-semibold text-text-primary">生图后端配置</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1.5">后端类型</label>
            <select
              value={settings.image.backend}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  image: { ...prev.image, backend: e.target.value },
                }))
              }
              className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary outline-none focus:border-accent transition-colors duration-200"
            >
              <option value="chatgpt2api">OpenAI Images API（推荐）</option>
              <option value="comfyui">ComfyUI</option>
              <option value="sdwebui">Stable Diffusion WebUI</option>
              <option value="dalle">DALL·E API</option>
            </select>
          </div>

          {settings.image.backend === 'chatgpt2api' && (
            <>
              <div>
                <label className="block text-sm text-text-secondary mb-1.5">API 地址</label>
                <input
                  type="text"
                  value={settings.image.chatgpt2api.base_url}
                  onChange={(e) => updateImageChatgpt2api('base_url', e.target.value)}
                  placeholder="https://api.openai.com/v1"
                  className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent transition-colors duration-200 font-mono"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1.5">API Key</label>
                <input
                  type="password"
                  value={settings.image.chatgpt2api.api_key}
                  onChange={(e) => updateImageChatgpt2api('api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent transition-colors duration-200 font-mono"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1.5">生图模型</label>
                <input
                  type="text"
                  value={settings.image.chatgpt2api.model}
                  onChange={(e) => updateImageChatgpt2api('model', e.target.value)}
                  placeholder="gpt-image-2"
                  className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent transition-colors duration-200 font-mono"
                />
              </div>
            </>
          )}
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-5">
          <FolderOpen size={16} className="text-amber-400" />
          <h2 className="text-base font-semibold text-text-primary">输出设置</h2>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-text-secondary mb-1.5">输出目录</label>
            <input
              type="text"
              value={settings.output.dir}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  output: { ...prev.output, dir: e.target.value },
                }))
              }
              placeholder="./output"
              className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent transition-colors duration-200 font-mono"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between pt-2">
        <div className="min-w-0">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex items-center gap-2 border border-border text-text-secondary rounded-lg px-4 py-2 text-sm hover:border-border-hover hover:text-text-primary transition-colors duration-200 disabled:opacity-50"
          >
            {testing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : testResult === 'success' ? (
              <Wifi size={16} className="text-success" />
            ) : testResult === 'error' ? (
              <WifiOff size={16} className="text-error" />
            ) : (
              <Wifi size={16} />
            )}
            {testing ? '测试中...' : testResult === 'success' ? '连接成功' : testResult === 'error' ? '连接失败' : '测试连接'}
          </button>
          {testMessage && (
            <div
              className={`mt-2 max-w-xl truncate text-xs ${
                testResult === 'success' ? 'text-success' : 'text-error'
              }`}
              title={testMessage}
            >
              {testMessage}
            </div>
          )}
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-accent-hover transition-colors duration-200 disabled:opacity-50"
        >
          <Save size={16} />
          {saving ? '保存中...' : '保存设置'}
        </button>
      </div>
    </div>
  )
}
