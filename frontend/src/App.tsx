import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Activity,
  Loader2,
  CheckCircle2,
  XCircle,
  Ban,
  FileText,
  ListTree,
  RotateCcw,
  ArrowUp,
  AlertCircle,
  Download,
  RefreshCw,
} from 'lucide-react'
import { EventTimeline, type TraceEvent } from './components/EventTimeline'
import { HistorySidebar } from './components/HistorySidebar'
import { CompareView } from './components/CompareView'
import { ObservabilityPanel } from './components/ObservabilityPanel'
import { ErrorBanner, WarningBanner } from './components/ui'

// 任务状态枚举
type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'rejected'

interface TaskInfo {
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

interface AnalyzeResponse {
  task_id: string
  status: string
  message: string
}

const TERMINAL_STATUSES: TaskStatus[] = ['completed', 'failed', 'rejected']
const POLL_INTERVAL_MS = 2000
const POLL_MAX_MS = 5 * 60 * 1000

/** 带重试的 fetch：网络错误/5xx 退避重试，4xx 直接返回（业务错误不重试） */
async function fetchWithRetry(input: string, init: RequestInit, retries = 2): Promise<Response> {
  let lastErr: unknown
  for (let i = 0; i <= retries; i++) {
    try {
      const resp = await fetch(input, init)
      if (resp.status >= 500 && i < retries) {
        await new Promise((r) => setTimeout(r, 500 * (i + 1)))
        continue
      }
      return resp
    } catch (e) {
      lastErr = e
      if (i < retries) {
        await new Promise((r) => setTimeout(r, 500 * (i + 1)))
        continue
      }
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error('网络请求失败')
}

/** 根据 current_step 返回阶段文字 */
function stageText(currentStep?: number): string {
  if (!currentStep || currentStep <= 0) return '正在准备分析...'
  const stages = [
    '正在准备分析...',
    '正在收集数据...',
    '正在分析数据...',
    '正在验证数据...',
    '正在多空辩论...',
    '正在评估风险...',
    '正在撰写报告...',
  ]
  if (currentStep >= 7) return '正在合规审查...'
  return stages[currentStep] ?? '正在分析...'
}

/**
 * 多 Agent 金融分析 Dashboard（对话式）
 */
function App() {
  const [topic, setTopic] = useState<string>('')
  const [userId, setUserId] = useState<string>('web-user')
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [task, setTask] = useState<TaskInfo | null>(null)
  const [error, setError] = useState<string>('')
  const [pollTimedOut, setPollTimedOut] = useState<boolean>(false)
  const [traceError, setTraceError] = useState<string>('')
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([])
  const [traceMermaid, setTraceMermaid] = useState<string>('')
  // 折叠状态（纯视觉）
  const [reportOpen, setReportOpen] = useState<boolean>(false)
  const [timelineOpen, setTimelineOpen] = useState<boolean>(false)
  // 历史列表刷新触发器（变化时 HistorySidebar 重新拉 /api/tasks）
  const [historyRefreshKey, setHistoryRefreshKey] = useState<number>(0)
  // 视图模式：对话 vs 对比
  const [viewMode, setViewMode] = useState<'chat' | 'compare' | 'observability'>('chat')

  const pollTimerRef = useRef<number | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const wsTimerRef = useRef<number | null>(null)
  const pollStartRef = useRef<number>(0)
  const wsGotMsgRef = useRef<boolean>(false)
  const traceFetchedRef = useRef<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  function stopPolling(): void {
    // 关闭 WebSocket
    if (wsRef.current) {
      wsRef.current.onmessage = null
      wsRef.current.onerror = null
      wsRef.current.onclose = null
      try { wsRef.current.close() } catch { /* noop */ }
      wsRef.current = null
    }
    // 清理定时器
    if (pollTimerRef.current !== null) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
    if (wsTimerRef.current !== null) {
      clearTimeout(wsTimerRef.current)
      wsTimerRef.current = null
    }
  }

  // 降级轮询：WebSocket 不可用时回退使用
  async function pollOnce(tid: string): Promise<void> {
    const elapsed = Date.now() - pollStartRef.current
    if (elapsed > POLL_MAX_MS) {
      setPollTimedOut(true)
      setError('等待超时，请稍后手动刷新')
      return
    }

    try {
      const resp = await fetch(`/api/task/${encodeURIComponent(tid)}`)
      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({ detail: `HTTP ${resp.status} ${resp.statusText}` })) as { detail?: string }
        const msg = typeof errBody.detail === 'string' ? errBody.detail : `HTTP ${resp.status}`
        setError(`查询任务状态失败：${msg}`)
        return
      }
      const data = await resp.json() as Partial<TaskInfo>
      const merged: TaskInfo = {
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
      if (TERMINAL_STATUSES.includes(merged.status)) {
        return
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(`查询任务状态失败：${msg}`)
      return
    }

    pollTimerRef.current = window.setTimeout(() => {
      void pollOnce(tid)
    }, POLL_INTERVAL_MS)
  }

  function startPolling(tid: string): void {
    stopPolling()
    setPollTimedOut(false)
    pollStartRef.current = Date.now()
    wsGotMsgRef.current = false
    void pollOnce(tid)
  }

  // WebSocket 实时推送（主路径）：状态/进度变化即推送，终态自动关闭
  function startWs(tid: string): void {
    stopPolling()
    setPollTimedOut(false)
    wsGotMsgRef.current = false
    pollStartRef.current = Date.now()

    // 超时兜底：5 分钟未到终态则提示
    wsTimerRef.current = window.setTimeout(() => {
      setPollTimedOut(true)
      setError('等待超时，请稍后手动刷新')
      stopPolling()
    }, POLL_MAX_MS)

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    let ws: WebSocket
    try {
      ws = new WebSocket(`${proto}://${window.location.host}/ws/${encodeURIComponent(tid)}`)
    } catch {
      startPolling(tid)
      return
    }
    wsRef.current = ws

    ws.onmessage = (ev) => {
      wsGotMsgRef.current = true
      try {
        const data = JSON.parse(ev.data) as { task?: Partial<TaskInfo> }
        const t = data.task
        if (!t) return
        const merged: TaskInfo = {
          task_id: t.task_id ?? tid,
          status: (t.status as TaskStatus) ?? 'pending',
          current_step: t.current_step ?? 0,
          total_steps: t.total_steps ?? 0,
          topic: t.topic ?? '',
          final_report: t.final_report ?? '',
          error: t.error ?? '',
          total_cost: t.total_cost ?? 0,
          total_tokens: t.total_tokens ?? 0,
        }
        setTask(merged)
        if (TERMINAL_STATUSES.includes(merged.status)) {
          stopPolling()
        }
      } catch {
        // 忽略异常消息
      }
    }

    ws.onerror = () => {
      // 连接失败且未收到过消息 → 降级轮询
      if (!wsGotMsgRef.current) {
        startPolling(tid)
      }
    }
  }

  // 提交分析（接受指定 topic，供「重新分析」复用）
  async function submitWithTopic(topicStr: string): Promise<void> {
    if (!topicStr) return

    setSubmitting(true)
    setError('')
    setTask(null)
    setTaskId(null)
    setPollTimedOut(false)
    setReportOpen(false)
    setTimelineOpen(false)
    setTraceError('')
    setTraceEvents([])
    setTraceMermaid('')
    stopPolling()

    try {
      const resp = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topicStr,
          user_id: userId,
          user_role: 'user',
        }),
      })
      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({ detail: `HTTP ${resp.status} ${resp.statusText}` })) as { detail?: string }
        const msg = (errBody && typeof errBody.detail === 'string') ? errBody.detail : `提交失败 HTTP ${resp.status}`
        setError(msg)
        return
      }
      const data = await resp.json() as AnalyzeResponse
      setTaskId(data.task_id)
      setHistoryRefreshKey((k) => k + 1)
      startWs(data.task_id)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(`提交失败：${msg}`)
    } finally {
      setSubmitting(false)
    }
  }

  async function submitAnalyze(): Promise<void> {
    await submitWithTopic(topic.trim())
  }

  // 重新分析：用当前 task 的 topic 再跑一次
  function reanalyze(): void {
    const t = task?.topic || topic.trim()
    if (!t) return
    void submitWithTopic(t)
  }

  // 下载报告：把 final_report 导出为 .md 文件
  function downloadReport(): void {
    if (!task?.final_report) return
    const blob = new Blob([task.final_report], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${task.topic || 'report'}-report.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  function reset(): void {
    stopPolling()
    setTopic('')
    setTaskId(null)
    setTask(null)
    setError('')
    setPollTimedOut(false)
    setTraceError('')
    setTraceEvents([])
    setTraceMermaid('')
    setReportOpen(false)
    setTimelineOpen(false)
    traceFetchedRef.current = null
  }

  // 新对话：直接复用 reset
  function handleNewChat(): void {
    reset()
  }

  // 删除历史任务：调 DELETE 接口，成功后刷新列表；若删的是当前任务则清空右侧
  async function handleDelete(tid: string): Promise<void> {
    try {
      const resp = await fetch(`/api/tasks/${encodeURIComponent(tid)}`, { method: 'DELETE' })
      if (!resp.ok) {
        setError('删除失败')
        return
      }
      setHistoryRefreshKey((k) => k + 1)
      if (tid === taskId) {
        reset()
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(`删除失败：${msg}`)
    }
  }

  // 加载历史任务：直接展示结果，不走提交、不启动轮询
  async function loadHistory(tid: string): Promise<void> {
    stopPolling()
    setError('')
    setPollTimedOut(false)
    setTraceError('')
    setTraceEvents([])
    setTraceMermaid('')
    setReportOpen(false)
    setTimelineOpen(false)
    try {
      const resp = await fetchWithRetry(`/api/task/${encodeURIComponent(tid)}`)
      if (!resp.ok) {
        setError('加载历史失败')
        return
      }
      const data = await resp.json() as Partial<TaskInfo>
      const merged: TaskInfo = {
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
      setTaskId(tid)
    } catch {
      setError('加载历史失败')
    }
  }

  async function fetchTrace(tid: string): Promise<void> {
    try {
      const resp = await fetchWithRetry(`/api/trace/${encodeURIComponent(tid)}`)
      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({ detail: `HTTP ${resp.status} ${resp.statusText}` })) as { detail?: string }
        setTraceError(typeof errBody.detail === 'string' ? errBody.detail : `HTTP ${resp.status}`)
        return
      }
      const data = await resp.json() as { mermaid?: string; events?: TraceEvent[]; summary?: unknown }
      setTraceEvents(data.events ?? [])
      setTraceMermaid(data.mermaid ?? '')
    } catch (e) {
      setTraceError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    // 终态（含失败）都拉 trace，失败任务也能看到执行轨迹
    if (task?.status && TERMINAL_STATUSES.includes(task.status) && task.task_id && traceFetchedRef.current !== task.task_id) {
      traceFetchedRef.current = task.task_id
      void fetchTrace(task.task_id)
    }
  }, [task?.status, task?.task_id])

  useEffect(() => {
    return () => stopPolling()
  }, [])

  // 任务进入终态时刷新左侧历史列表（新提交的完成/失败后列表更新）
  useEffect(() => {
    if (task?.status && TERMINAL_STATUSES.includes(task.status)) {
      setHistoryRefreshKey((k) => k + 1)
    }
  }, [task?.status])

  // 新消息时滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [task?.status, taskId, error])

  const progressPct = task && task.total_steps > 0
    ? Math.min(100, Math.round((task.current_step / task.total_steps) * 100))
    : 0

  const submitDisabled = submitting || !topic.trim()
  const isProcessing = task?.status === 'pending' || task?.status === 'running'

  return (
    <div className="flex h-screen bg-app">
      <HistorySidebar
        currentTaskId={taskId}
        onSelect={loadHistory}
        onNew={handleNewChat}
        onCompare={() => setViewMode('compare')}
        onObservability={() => setViewMode('observability')}
        onDelete={handleDelete}
        refreshTrigger={historyRefreshKey}
      />
      <div className="flex-1 flex flex-col min-w-0">
      {/* Markdown 渲染样式 */}
      <style>{`
        .markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
          font-weight: 600;
          margin: 16px 0 8px;
          line-height: 1.4;
        }
        .markdown-body h1 { font-size: 20px; }
        .markdown-body h2 { font-size: 16px; border-bottom: 1px solid #30363d; padding-bottom: 6px; }
        .markdown-body h3 { font-size: 14px; }
        .markdown-body h4 { font-size: 14px; }
        .markdown-body p { margin: 8px 0; }
        .markdown-body ul, .markdown-body ol { margin: 8px 0; padding-left: 24px; }
        .markdown-body li { margin: 4px 0; }
        .markdown-body table { border-collapse: collapse; width: 100%; margin: 12px 0; }
        .markdown-body th, .markdown-body td { border: 1px solid #30363d; padding: 6px 10px; text-align: left; font-size: 14px; }
        .markdown-body th { background: #161b22; font-weight: 600; color: #e6edf3; }
        .markdown-body code { background: #161b22; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-family: 'JetBrains Mono', 'Cascadia Code', monospace; color: #58a6ff; }
        .markdown-body pre { background: #0d1117; padding: 16px; border: 1px solid #30363d; border-radius: 4px; overflow: auto; margin: 8px 0; }
        .markdown-body pre code { background: transparent; padding: 0; font-size: 14px; color: #e6edf3; }
        .markdown-body blockquote { border-left: 2px solid #58a6ff; padding: 4px 12px; color: #8b949e; margin: 8px 0; background: rgba(56,139,253,0.04); border-radius: 0 4px 4px 0; }
        .markdown-body a { color: #58a6ff; text-decoration: underline; text-decoration-color: rgba(56,139,253,0.4); }
        .markdown-body a:hover { text-decoration-color: #58a6ff; }
        .markdown-body hr { border: none; border-top: 1px solid #30363d; margin: 16px 0; }
        .markdown-body img { max-width: 100%; }
        .markdown-body strong { color: #e6edf3; font-weight: 600; }
      `}</style>

      {viewMode === 'compare' ? (
        <CompareView userId={userId} onBack={() => setViewMode('chat')} />
      ) : viewMode === 'observability' ? (
        <ObservabilityPanel onBack={() => setViewMode('chat')} />
      ) : (
        <>
      {/* ========== 对话流 ========== */}
      <main
        className="flex-1 overflow-y-auto p-6"
      >
        <div
          className="flex flex-col gap-4 max-w-[920px] mx-auto min-h-full justify-start"
        >
          {/* 空状态 */}
          {!task && !taskId && !error && (
            <div
              className="flex-1 flex flex-col items-center justify-center text-muted p-12 text-center"
            >
              <Activity size={40} className="text-edge mb-4" />
              <div className="text-base font-medium text-fg2 mb-1">
                输入股票代码开始分析
              </div>
              <div className="text-[13px] text-muted">
                例如 AAPL、TSLA 或 招商银行
              </div>
            </div>
          )}

          {/* 用户消息 */}
          {taskId && (
            <div className="msg-user">
              {task?.topic || topic}
            </div>
          )}

          {/* 助手消息 */}
          {(task || error) && (
            <div className="msg-assistant">
              {/* 分析中：脉动点 + 阶段文字 / 精致进度条 + 百分比 */}
              {task && isProcessing && (
                <div>
                  <div className="flex items-center gap-2.5">
                    <div
                      className="dot-pulse w-2 h-2 rounded-full bg-accent shrink-0"
                    />
                    <span className="text-[15px] text-fg font-medium">
                      {stageText(task.current_step)}
                    </span>
                  </div>
                  {task.total_steps > 0 && (
                    <div className="flex items-center gap-3 mt-4">
                      <div className="flex-1 h-1.5 rounded-full bg-divider overflow-hidden">
                        <div
                          className="h-full rounded-full bg-[linear-gradient(90deg,#58a6ff,#79c0ff)] shadow-[0_0_8px_rgba(88,166,255,0.5)]"
                          style={{
                            width: `${progressPct}%`,
                            transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                          }}
                        />
                      </div>
                      <span
                        className="stat-value text-xs text-fg2 min-w-10 text-right"
                      >
                        {progressPct}%
                      </span>
                    </div>
                  )}
                </div>
              )}

              {/* 完成 */}
              {task?.status === 'completed' && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 size={16} className="text-success" />
                    <span className="text-sm font-semibold text-fg">分析完成</span>
                  </div>

                  <div
                    className="flex gap-6 py-2 mb-3 border-b border-divider text-[13px]"
                  >
                    <div>
                      <span className="text-muted">tokens </span>
                      <span className="stat-value text-fg font-semibold">{task.total_tokens}</span>
                    </div>
                    <div>
                      <span className="text-muted">cost </span>
                      <span className="stat-value text-accent font-semibold">{task.total_cost}</span>
                      <span className="text-muted"> 元</span>
                    </div>
                  </div>

                  {/* 重新分析：用相同 topic 再跑一次（与底部「重新开始」语义不同） */}
                  <div className="mt-2">
                    <button
                      onClick={reanalyze}
                      disabled={submitting}
                      className="btn-ghost text-[13px] px-3 py-1.5"
                    >
                      <RefreshCw size={13} /> 重新分析
                    </button>
                  </div>

                  {/* 折叠：分析报告 */}
                  {task.final_report && (
                    <div>
                      <div
                        className="collapse-header"
                        onClick={() => setReportOpen((v) => !v)}
                      >
                        <FileText size={14} />
                        <span>分析报告</span>
                        <span className="ml-auto flex items-center gap-2">
                          {/* 下载报告按钮 */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              downloadReport()
                            }}
                            className="btn-ghost text-xs px-2 py-0.5"
                          >
                            <Download size={13} /> 下载 .md
                          </button>
                          <span className="text-muted">
                            {reportOpen ? '收起' : '展开'}
                          </span>
                        </span>
                      </div>
                      {reportOpen && (
                        <div
                          className="markdown-body mt-2 mb-2 p-3 bg-app border border-edge rounded-sm max-h-[500px] overflow-auto text-sm leading-relaxed text-fg"
                        >
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {task.final_report}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 折叠：事件时间线 */}
                  <div>
                    <div
                      className="collapse-header"
                      onClick={() => setTimelineOpen((v) => !v)}
                    >
                      <ListTree size={14} />
                      <span>事件时间线</span>
                      <span className="ml-auto text-muted">
                        {timelineOpen ? '收起' : '展开'}
                      </span>
                    </div>
                    {timelineOpen && (
                      <div className="mt-2 mb-2">
                        {traceError && <ErrorBanner>{traceError}</ErrorBanner>}
                        <EventTimeline events={traceEvents} />
                        {/* Mermaid 时序图源码：后端已生成，不装新依赖，展示源码 + 外链 */}
                        {traceMermaid && (
                          <div className="mt-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-muted tracking-wider uppercase font-semibold">
                                时序图 (Mermaid)
                              </span>
                              <a
                                href="https://mermaid.live/"
                                target="_blank"
                                rel="noreferrer"
                                className="text-xs text-accent"
                              >
                                打开 mermaid.live 渲染 →
                              </a>
                            </div>
                            <pre className="m-0 p-3 bg-app border border-edge rounded-sm text-xs leading-normal text-fg2 overflow-auto max-h-[240px]" style={{ fontFamily: "'JetBrains Mono', 'Cascadia Code', monospace" }}>
                              {traceMermaid}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* 重新开始 */}
                  <div className="mt-3">
                    <button onClick={reset} className="btn-ghost text-[13px] px-3 py-1.5">
                      <RotateCcw size={13} /> 重新开始
                    </button>
                  </div>
                </div>
              )}

              {/* 失败 */}
              {task?.status === 'failed' && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <XCircle size={16} className="text-danger" />
                    <span className="text-sm font-semibold text-fg">分析失败</span>
                  </div>
                  {task.error && <ErrorBanner>{task.error}</ErrorBanner>}
                  <div className="mt-3">
                    <button onClick={reset} className="btn-ghost text-[13px] px-3 py-1.5">
                      <RotateCcw size={13} /> 重新开始
                    </button>
                  </div>
                </div>
              )}

              {/* 拒绝 */}
              {task?.status === 'rejected' && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Ban size={16} className="text-fg2" />
                    <span className="text-sm font-semibold text-fg">任务被拒绝</span>
                  </div>
                  <WarningBanner>
                    {task.error || '任务在合规预检阶段被拒绝（可能因权限/限流/成本熔断）'}
                  </WarningBanner>
                  <div className="mt-3">
                    <button onClick={reset} className="btn-ghost text-[13px] px-3 py-1.5">
                      <RotateCcw size={13} /> 重新开始
                    </button>
                  </div>
                </div>
              )}

              {/* 提交/轮询错误（无 task 时） */}
              {!task && error && (
                <div>
                  <div className="flex items-start gap-2">
                    <AlertCircle size={16} className="text-danger shrink-0 mt-0.5" />
                    <div className="text-sm text-danger whitespace-pre-wrap">
                      {error}
                    </div>
                  </div>
                  <div className="mt-3">
                    <button onClick={reset} className="btn-ghost text-[13px] px-3 py-1.5">
                      <RotateCcw size={13} /> 重新开始
                    </button>
                  </div>
                </div>
              )}

              {/* 轮询超时（task 存在但超时） */}
              {task && pollTimedOut && (
                <WarningBanner>{error}</WarningBanner>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* ========== 输入区（固定底部） ========== */}
      <footer
        className="shrink-0 px-6 py-3 border-t border-divider bg-app"
      >
        <div
          className="flex gap-3 max-w-[920px] mx-auto items-end"
        >
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="用户 ID"
            disabled={submitting}
            className="input w-28 shrink-0"
          />
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !submitDisabled) {
                e.preventDefault()
                void submitAnalyze()
              }
            }}
            placeholder="输入股票代码或行业名称，例如 AAPL"
            disabled={submitting}
            className="input flex-1"
          />
          <button
            onClick={submitAnalyze}
            disabled={submitDisabled}
            className="btn-primary shrink-0"
          >
            {submitting ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <ArrowUp size={16} />
            )}
            {submitting ? '提交中' : '发送'}
          </button>
        </div>
      </footer>
        </>
      )}
      </div>
    </div>
  )
}

export default App
