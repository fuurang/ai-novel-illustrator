import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Trash2, X, ZoomIn } from 'lucide-react'

interface GalleryProps {
  images: {
    id: string
    url: string
    path?: string
    name?: string
    entity_name?: string
  }[]
  loading?: boolean
  onDelete?: (image: GalleryProps['images'][number]) => Promise<void> | void
}

export default function Gallery({ images, loading, onDelete }: GalleryProps) {
  const [previewIndex, setPreviewIndex] = useState<number | null>(null)
  const [deletingImageId, setDeletingImageId] = useState<string | null>(null)
  const preview = previewIndex !== null ? images[previewIndex] : null
  const canSwitchPreview = images.length > 1 && previewIndex !== null

  const switchPreview = (direction: -1 | 1) => {
    if (previewIndex === null || images.length === 0) return
    setPreviewIndex((previewIndex + direction + images.length) % images.length)
  }

  const handleDelete = async (image: GalleryProps['images'][number]) => {
    if (!onDelete || deletingImageId) return
    const label = image.name || image.entity_name || '这张图片'
    if (!window.confirm(`确定删除「${label}」吗？删除后文件会从项目目录移除。`)) return

    setDeletingImageId(image.id)
    try {
      await onDelete(image)
      setPreviewIndex((current) => {
        if (current === null) return null
        const deletedIndex = images.findIndex((item) => item.id === image.id)
        if (images.length <= 1) return null
        if (current > deletedIndex) return current - 1
        if (current === deletedIndex) return Math.min(current, images.length - 2)
        return current
      })
    } finally {
      setDeletingImageId(null)
    }
  }

  useEffect(() => {
    if (!preview) return
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setPreviewIndex(null)
      } else if (event.key === 'ArrowLeft') {
        switchPreview(-1)
      } else if (event.key === 'ArrowRight') {
        switchPreview(1)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [preview, previewIndex, images.length])

  if (loading) {
    return (
      <div className="columns-2 md:columns-3 gap-4 space-y-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="bg-surface border border-border rounded-xl animate-pulse break-inside-avoid"
            style={{ height: `${120 + (i % 3) * 60}px` }}
          />
        ))}
      </div>
    )
  }

  if (!images.length) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-text-muted">
        <ZoomIn size={48} className="mb-4 opacity-30" />
        <p className="text-sm">暂无图片</p>
        <p className="text-xs mt-1">保存出图对象中的图片后，将在此展示。</p>
      </div>
    )
  }

  return (
    <>
      <div className="columns-2 md:columns-3 gap-4">
        {images.map((img) => (
          <div
            key={img.id}
            onClick={() => setPreviewIndex(images.findIndex((item) => item.id === img.id))}
            className="mb-4 break-inside-avoid bg-surface border border-border rounded-xl overflow-hidden cursor-pointer group transition-all duration-200 hover:border-border-hover"
          >
            <div className="relative overflow-hidden">
              <img
                src={img.url}
                alt={img.name || img.entity_name || ''}
                className="w-full object-cover transition-transform duration-200 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors duration-200 flex items-center justify-center">
                <ZoomIn size={24} className="text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
              </div>
              {onDelete && (
                <button
                  type="button"
                  title="删除图片"
                  disabled={deletingImageId === img.id}
                  onClick={(event) => {
                    event.stopPropagation()
                    void handleDelete(img)
                  }}
                  className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-md bg-black/55 text-white opacity-0 transition-opacity duration-200 hover:bg-error group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
            {(img.name || img.entity_name) && (
              <div className="p-2.5">
                <div className="text-xs text-text-secondary truncate">
                  {img.name || img.entity_name}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {preview && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-8 cursor-pointer"
          onClick={() => setPreviewIndex(null)}
        >
          <button
            type="button"
            onClick={() => setPreviewIndex(null)}
            className="absolute top-4 right-4 p-2 rounded-lg bg-surface/80 text-text-primary hover:bg-elevated transition-colors duration-200"
          >
            <X size={20} />
          </button>
          {onDelete && (
            <button
              type="button"
              disabled={deletingImageId === preview.id}
              onClick={(event) => {
                event.stopPropagation()
                void handleDelete(preview)
              }}
              className="absolute right-16 top-4 inline-flex items-center gap-1.5 rounded-lg bg-surface/80 px-3 py-2 text-sm text-text-primary transition-colors duration-200 hover:bg-error hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Trash2 size={16} />
              删除
            </button>
          )}
          {canSwitchPreview && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation()
                switchPreview(-1)
              }}
              className="absolute left-4 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-surface/80 text-text-primary hover:bg-elevated"
            >
              <ChevronLeft size={24} />
            </button>
          )}
          <img
            src={preview.url}
            alt={preview.name || preview.entity_name || '预览'}
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
          {canSwitchPreview && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation()
                switchPreview(1)
              }}
              className="absolute right-4 top-1/2 inline-flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full bg-surface/80 text-text-primary hover:bg-elevated"
            >
              <ChevronRight size={24} />
            </button>
          )}
        </div>
      )}
    </>
  )
}
