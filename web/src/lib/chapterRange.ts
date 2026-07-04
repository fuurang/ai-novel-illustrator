export const parseChapterRange = (value: unknown) => {
  const chapters: number[] = []
  String(value || '').split(',').forEach((part) => {
    const trimmed = part.trim()
    if (!trimmed) return
    const range = trimmed.match(/^(\d+)\s*-\s*(\d+)$/)
    if (range) {
      const start = Number(range[1])
      const end = Number(range[2])
      for (let chapter = start; chapter <= end; chapter += 1) chapters.push(chapter)
      return
    }
    const single = Number(trimmed)
    if (Number.isFinite(single)) chapters.push(single)
  })
  return chapters
}
