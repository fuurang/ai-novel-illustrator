import { create } from 'zustand'
import { api } from '@/api/client'
import type { PipelineRunOptions, PipelineStatus } from '@/api/types'

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '执行失败'
}

interface PipelineState {
  runningStage: string
  stageProgress: number
  stageMessage: string
  runStage: (projectId: string, stage: string, chapterIndices?: number[], options?: PipelineRunOptions) => Promise<void>
  setStageMessage: (message: string) => void
  reset: () => void
}

export const usePipelineStore = create<PipelineState>((set) => ({
  runningStage: '',
  stageProgress: 0,
  stageMessage: '',

  runStage: async (projectId: string, stage: string, chapterIndices?: number[], options?: PipelineRunOptions) => {
    set({ runningStage: stage, stageProgress: 0, stageMessage: `正在执行: ${stage}` })

    try {
      await api.pipeline.runStage(projectId, stage, chapterIndices, options)
    } catch (error) {
      set({
        runningStage: '',
        stageProgress: 0,
        stageMessage: getErrorMessage(error),
      })
      return
    }

    const source = api.pipeline.status(projectId)

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as PipelineStatus
        const isDone = !data.is_running || data.current_stage_key === 'done' || data.current_stage_key === 'error'

        set({
          stageProgress: data.progress ?? 0,
          stageMessage: data.current_stage || data.error || stage,
          runningStage: isDone ? '' : stage,
        })

        if (isDone) {
          source.close()
        }
      } catch (error) {
        void error
      }
    }

    source.onerror = () => {
      set({ runningStage: '', stageProgress: 0, stageMessage: '连接已断开' })
      source.close()
    }
  },

  setStageMessage: (message: string) => {
    set({ stageMessage: message })
  },

  reset: () => {
    set({ runningStage: '', stageProgress: 0, stageMessage: '' })
  },
}))
