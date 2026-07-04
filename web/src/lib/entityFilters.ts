import { parseChapterRange } from './chapterRange'

type EntityLike = Record<string, unknown>
type SceneLike = Record<string, unknown>
type ChapterRef = number | { chapter?: unknown } | null | undefined

export const entityChapterNumbers = (entity: EntityLike) => {
  const chapters = new Set<number>()
  const add = (value: unknown) => {
    const num = Number(value)
    if (Number.isFinite(num) && num > 0) chapters.add(num)
  }

  ;((entity.source_quotes || []) as ChapterRef[]).forEach((item) => {
    add(typeof item === 'number' ? item : item?.chapter)
  })
  ;((entity.chapter_appearances || []) as ChapterRef[]).forEach((item) => {
    add(typeof item === 'number' ? item : item?.chapter)
  })
  ;((entity.source_chapters || []) as unknown[]).forEach(add)
  add(entity.first_appearance_chapter)
  parseChapterRange(entity.chapter_range || '').forEach(add)

  return chapters
}

export const entityInScene = (entity: EntityLike, scene: SceneLike | null | undefined) => {
  const sceneChapters = new Set(
    ((scene?.chapters || []) as unknown[])
      .map((chapter) => Number(chapter))
      .filter((chapter) => Number.isFinite(chapter))
  )
  if (!sceneChapters.size) {
    parseChapterRange(scene?.chapter_range || '').forEach((chapter) => sceneChapters.add(chapter))
  }
  if (!sceneChapters.size) return true
  const chapters = entityChapterNumbers(entity)
  if (!chapters.size) return false
  return [...chapters].some((chapter) => sceneChapters.has(chapter))
}

export const hasVisualAttributes = (entity: EntityLike | null | undefined) => {
  const attrs = entity?.attributes
  if (!attrs || typeof attrs !== 'object') return false
  return (JSON.stringify(attrs) as string).replace(/[{}[\]":,\s]/g, '').length > 8
}

export const taskPrefixForEntity = (entity: EntityLike) => {
  if (entity.type === 'scene') return 'scene'
  if (entity.type === 'item') return 'item'
  return 'character'
}
