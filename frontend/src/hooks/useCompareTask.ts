import { useEffect, useRef, useState } from 'react'

// 任务状态枚举
type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'rejected'

/** 任务信息（对应后端 GET /api/task/{id} 返回字段） */
export interface CompareTaskInfo {
  task_id: string
  status: TaskStatus
  current_step: number
  total_steps: number
  topic: string
  final_report: string
  error: string
  total_cost: number
  total_tokens: number
}

/** 提交响应（对应 POST /api/analyze 返回） */
interface AnalyzeResponse {
  task_id: string
  status: string
  message: string
}

// 终态集合：进入这些状态后停止轮询
const TERMINAL_STATUSES: TaskStatus[] = ['completed', 'failed', 'rejected']
const POLL_INTERVAL_MS = 2000        // 轮询间隔 2 秒
const POLL_MAX_MS = 5 * 60 * 1000    // 轮询累计超时 5 分钟

/** hook 对外暴露的形状 */
export interface CompareTaskHook {
  topic: string
  setTopic: (s: string) => void
  submitting: boolean
  taskId: string | null
  task: CompareTaskInfo | null
  error: string
  progressPct: number
  submit: () => void
  reset: () => void
  downloadReport: () => void
}

/**
 * 对比模式单任务生命周期 hook
 * 封装：提交 → 轮询 → 终态停止 → 清理；外加下载报告
 * 两个面板各调用一次，互不影响
 */
export function useCompareTask(): CompareTaskHook {
  const [topic, setTopic] = useState<string>('')
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [task, setTask] = useState<CompareTaskInfo | null>(null)
  const [error, setError] = useState<string>('')

  // 用 ref 保存 timer id 与轮询起始时间，避免重新渲染时丢失
  const pollTimerRef = useRef<number | null>(null)
  const pollStartRef = useRef<number>(0)

  /** 停止轮询：清掉当前 timer */
  function stopPolling(): void {
    if (pollTimerRef.current !== null) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  /** 单次轮询：拉取任务状态；终态则停，否则安排 2 秒后再拉一次 */
  function pollOnce(tid: string): void {
    const elapsed = Date.now() - pollStartRef.current
    if (elapsed > POLL_MAX_MS) {
      setError('轮询超时')
      return
    }

    fetch(`/api/task/${encodeURIComponent(tid)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: Partial<CompareTaskInfo>) => {
        // 合并后端返回的字段，缺字段用默认值兜底
        const merged: CompareTaskInfo = {
          task_id: data.task_id ?? tid,
          status: (data.status as TaskStatus) ?? 'pending',
          current_step: data.current_step ?? 0,
          total_steps: data.total_steps ?? 0,
          topic: data.topic ?? '',
          final_report: data.final_report ?? '',
          error: data.error ?? '',
          total_cost: data.total_cost ?? 0,
          total_tokens: data.total_tokens ?? 0,
        }
        setTask(merged)
        // 终态：停止轮询
        if (TERMINAL_STATUSES.includes(merged.status)) return
        // 非终态：2 秒后再拉一次
        pollTimerRef.current = window.setTimeout(() => pollOnce(tid), POLL_INTERVAL_MS)
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : String(e)
        setError(`查询任务状态失败：${msg}`)
      })
  }

  /** 启动轮询：先清旧 timer，再记录起始时间，立即拉一次 */
  function startPolling(tid: string): void {
    stopPolling()
    pollStartRef.current = Date.now()
    pollOnce(tid)
  }

  /** 提交分析：POST /api/analyze，拿到 task_id 后启动轮询 */
  function submit(): void {
    const t = topic.trim()
    if (!t) return

    setSubmitting(true)
    setError('')
    setTask(null)
    setTaskId(null)
    stopPolling()

    fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: t,
        user_id: 'web-user',
        user_role: 'user',
      }),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data: AnalyzeResponse) => {
        setTaskId(data.task_id)
        startPolling(data.task_id)
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : String(e)
        setError(`提交失败：${msg}`)
      })
      .finally(() => setSubmitting(false))
  }

  /** 重置：清空所有状态，停止轮询 */
  function reset(): void {
    stopPolling()
    setTopic('')
    setTaskId(null)
    setTask(null)
    setError('')
  }

  /** 下载报告：把 final_report 导出为 .md 文件 */
  function downloadReport(): void {
    if (!task?.final_report) return
    const blob = new Blob([task.final_report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${task.topic || 'report'}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // 组件卸载时清理 timer，避免内存泄漏
  useEffect(() => {
    return () => stopPolling()
  }, [])

  // 进度百分比：total_steps > 0 才算，否则 0
  const progressPct = task && task.total_steps > 0
    ? Math.min(100, Math.round((task.current_step / task.total_steps) * 100))
    : 0

  return {
    topic,
    setTopic,
    submitting,
    taskId,
    task,
    error,
    progressPct,
    submit,
    reset,
    downloadReport,
  }
}
