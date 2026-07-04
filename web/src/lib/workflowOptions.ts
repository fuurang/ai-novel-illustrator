export const extractionLevels = [
  { key: 'all', label: '全部' },
  { key: 'balanced', label: '适中' },
  { key: 'key', label: '关键' },
] as const

export const sceneGranularityLevels = [
  { key: 'fine', label: '细', desc: '小地图/小事件，边界变化稍明显就切换' },
  { key: 'medium', label: '中', desc: '按主要剧情阶段切换' },
  { key: 'coarse', label: '粗', desc: '大地图/副本/长行动线尽量合并' },
] as const
