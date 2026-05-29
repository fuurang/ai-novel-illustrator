import { useState, useRef } from 'react'
import { Upload, X, FileText } from 'lucide-react'

interface UploadModalProps {
  open: boolean
  onClose: () => void
  onUpload: (file: File, name: string) => void
  loading?: boolean
}

export default function UploadModal({ open, onClose, onUpload, loading }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleSubmit = () => {
    if (!file || !name.trim()) return
    onUpload(file, name.trim())
  }

  const handleClose = () => {
    setFile(null)
    setName('')
    setDragOver(false)
    onClose()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) {
      setFile(dropped)
      if (!name) setName(dropped.name.replace(/\.[^/.]+$/, ''))
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center" onClick={handleClose}>
      <div
        className="bg-surface border border-border rounded-2xl w-[480px] max-w-[90vw] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-lg font-semibold text-text-primary">新建项目</h2>
          <button
            onClick={handleClose}
            className="p-2 rounded-lg hover:bg-elevated text-text-secondary transition-colors duration-200"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-5">
          <div>
            <label className="block text-sm text-text-secondary mb-2">项目名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入项目名称"
              className="w-full bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder-text-muted outline-none focus:border-accent transition-colors duration-200"
            />
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-2">小说文件</label>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
                dragOver
                  ? 'border-accent bg-accent/5'
                  : file
                  ? 'border-success/50 bg-success/5'
                  : 'border-border hover:border-border-hover'
              }`}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".txt,.epub,.pdf,.docx"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) {
                    setFile(f)
                    if (!name) setName(f.name.replace(/\.[^/.]+$/, ''))
                  }
                }}
              />
              {file ? (
                <div className="flex items-center justify-center gap-2">
                  <FileText size={20} className="text-success" />
                  <span className="text-sm text-text-primary">{file.name}</span>
                </div>
              ) : (
                <>
                  <Upload size={32} className="mx-auto mb-3 text-text-muted" />
                  <p className="text-sm text-text-secondary">拖拽文件到此处，或点击选择</p>
                  <p className="text-xs text-text-muted mt-1">支持 TXT、EPUB、PDF、DOCX</p>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 p-5 border-t border-border">
          <button
            onClick={handleClose}
            className="border border-border text-text-secondary rounded-lg px-4 py-2 text-sm hover:border-border-hover hover:text-text-primary transition-colors duration-200"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={!file || !name.trim() || loading}
            className="bg-accent text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-accent-hover transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '创建中...' : '创建项目'}
          </button>
        </div>
      </div>
    </div>
  )
}
