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
import { StatusDot } from './components/StatusDot'
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
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [task, setTask] = useState<TaskInfo | null>(null)
  const [error, setError] = useState<string>('')
  const [pollTimedOut, setPollTimedOut] = useState<boolean>(false)
  const [traceError, setTraceError] = useState<string>('')
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([])
  // 折叠状态（纯视觉）
  const [reportOpen, setReportOpen] = useState<boolean>(false)
  const [timelineOpen, setTimelineOpen] = useState<boolean>(false)

  const pollTimerRef = useRef<number | null>(null)
  const pollStartRef = useRef<number>(0)
  const traceFetchedRef = useRef<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  function stopPolling(): void {
    if (pollTimerRef.current !== null) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  async function pollOnce(tid: string): Promise<void> {
    const elapsed = Date.now() - pollStartRef.current
    if (elapsed > POLL_MAX_MS) {
      setPollTimedOut(true)
      setError('轮询超时，请稍后手动刷新')
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
    void pollOnce(tid)
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
    stopPolling()

    try {
      const resp = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topicStr,
          user_id: 'web-user',
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
      startPolling(data.task_id)
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
    setReportOpen(false)
    setTimelineOpen(false)
    traceFetchedRef.current = null
  }

  async function fetchTrace(tid: string): Promise<void> {
    try {
      const resp = await fetch(`/api/trace/${encodeURIComponent(tid)}`)
      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({ detail: `HTTP ${resp.status} ${resp.statusText}` })) as { detail?: string }
        setTraceError(typeof errBody.detail === 'string' ? errBody.detail : `HTTP ${resp.status}`)
        return
      }
      const data = await resp.json() as { mermaid?: string; events?: TraceEvent[]; summary?: unknown }
      setTraceEvents(data.events ?? [])
    } catch (e) {
      setTraceError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    if (task?.status === 'completed' && task.task_id && traceFetchedRef.current !== task.task_id) {
      traceFetchedRef.current = task.task_id
      void fetchTrace(task.task_id)
    }
  }, [task?.status, task?.task_id])

  useEffect(() => {
    return () => stopPolling()
  }, [])

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
    <>
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

      {/* ========== Header ========== */}
      <header
        style={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 24px',
          borderBottom: '1px solid #21262d',
          background: '#0d1117',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 32,
              height: 32,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: 8,
            }}
          >
            <Activity size={18} color="#58a6ff" strokeWidth={2} />
          </div>
          <div>
            <h1
              style={{
                fontSize: 16,
                fontWeight: 600,
                margin: 0,
                color: '#e6edf3',
                lineHeight: 1.2,
              }}
            >
              金融分析助手
            </h1>
            <p style={{ color: '#6e7681', fontSize: 12, margin: '2px 0 0' }}>
              多 Agent 协作
            </p>
          </div>
        </div>
        <StatusDot />
      </header>

      {/* ========== 对话流 ========== */}
      <main
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '24px',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            maxWidth: 920,
            margin: '0 auto',
            minHeight: '100%',
            justifyContent: 'flex-start',
          }}
        >
          {/* 空状态 */}
          {!task && !taskId && !error && (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#6e7681',
                padding: 48,
                textAlign: 'center',
              }}
            >
              <Activity size={40} style={{ color: '#30363d', marginBottom: 16 }} />
              <div style={{ fontSize: 16, fontWeight: 500, color: '#8b949e', marginBottom: 4 }}>
                输入股票代码开始分析
              </div>
              <div style={{ fontSize: 13, color: '#6e7681' }}>
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
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div
                      className="dot-pulse"
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: '#58a6ff',
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontSize: 15, color: '#e6edf3', fontWeight: 500 }}>
                      {stageText(task.current_step)}
                    </span>
                  </div>
                  {task.total_steps > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16 }}>
                      <div style={{ flex: 1, height: 6, borderRadius: 999, background: '#21262d', overflow: 'hidden' }}>
                        <div
                          style={{
                            width: `${progressPct}%`,
                            height: '100%',
                            borderRadius: 999,
                            background: 'linear-gradient(90deg, #58a6ff, #79c0ff)',
                            transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                            boxShadow: '0 0 8px rgba(88, 166, 255, 0.5)',
                          }}
                        />
                      </div>
                      <span
                        className="stat-value"
                        style={{
                          fontSize: 12,
                          color: '#8b949e',
                          minWidth: 40,
                          textAlign: 'right',
                        }}
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
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                    <CheckCircle2 size={16} style={{ color: '#3fb950' }} />
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>分析完成</span>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      gap: 24,
                      padding: '8px 0',
                      marginBottom: 12,
                      borderBottom: '1px solid #21262d',
                      fontSize: 13,
                    }}
                  >
                    <div>
                      <span style={{ color: '#6e7681' }}>tokens </span>
                      <span className="stat-value" style={{ color: '#e6edf3', fontWeight: 600 }}>{task.total_tokens}</span>
                    </div>
                    <div>
                      <span style={{ color: '#6e7681' }}>cost </span>
                      <span className="stat-value" style={{ color: '#58a6ff', fontWeight: 600 }}>{task.total_cost}</span>
                      <span style={{ color: '#6e7681' }}> 元</span>
                    </div>
                  </div>

                  {/* 重新分析：用相同 topic 再跑一次（与底部「重新开始」语义不同） */}
                  <div style={{ marginTop: 8 }}>
                    <button
                      onClick={reanalyze}
                      disabled={submitting}
                      className="btn-ghost"
                      style={{ fontSize: 13, padding: '6px 12px' }}
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
                        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                          {/* 下载报告按钮 */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              downloadReport()
                            }}
                            className="btn-ghost"
                            style={{ fontSize: 12, padding: '2px 8px' }}
                          >
                            <Download size={13} /> 下载 .md
                          </button>
                          <span style={{ color: '#6e7681' }}>
                            {reportOpen ? '收起' : '展开'}
                          </span>
                        </span>
                      </div>
                      {reportOpen && (
                        <div
                          className="markdown-body"
                          style={{
                            marginTop: 8,
                            marginBottom: 8,
                            padding: 12,
                            background: '#0d1117',
                            border: '1px solid #30363d',
                            borderRadius: 4,
                            maxHeight: 500,
                            overflow: 'auto',
                            fontSize: 14,
                            lineHeight: 1.6,
                            color: '#e6edf3',
                          }}
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
                      <span style={{ marginLeft: 'auto', color: '#6e7681' }}>
                        {timelineOpen ? '收起' : '展开'}
                      </span>
                    </div>
                    {timelineOpen && (
                      <div style={{ marginTop: 8, marginBottom: 8 }}>
                        {traceError && <ErrorBanner>{traceError}</ErrorBanner>}
                        <EventTimeline events={traceEvents} />
                      </div>
                    )}
                  </div>

                  {/* 重新开始 */}
                  <div style={{ marginTop: 12 }}>
                    <button onClick={reset} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
                      <RotateCcw size={13} /> 重新开始
                    </button>
                  </div>
                </div>
              )}

              {/* 失败 */}
              {task?.status === 'failed' && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <XCircle size={16} style={{ color: '#f85149' }} />
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>分析失败</span>
                  </div>
                  {task.error && <ErrorBanner>{task.error}</ErrorBanner>}
                  <div style={{ marginTop: 12 }}>
                    <button onClick={reset} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
                      <RotateCcw size={13} /> 重新开始
                    </button>
                  </div>
                </div>
              )}

              {/* 拒绝 */}
              {task?.status === 'rejected' && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <Ban size={16} style={{ color: '#8b949e' }} />
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>任务被拒绝</span>
                  </div>
                  <WarningBanner>
                    {task.error || '任务在合规预检阶段被拒绝（可能因权限/限流/成本熔断）'}
                  </WarningBanner>
                  <div style={{ marginTop: 12 }}>
                    <button onClick={reset} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
                      <RotateCcw size={13} /> 重新开始
                    </button>
                  </div>
                </div>
              )}

              {/* 提交/轮询错误（无 task 时） */}
              {!task && error && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                    <AlertCircle size={16} style={{ color: '#f85149', flexShrink: 0, marginTop: 2 }} />
                    <div style={{ fontSize: 14, color: '#f85149', whiteSpace: 'pre-wrap' }}>
                      {error}
                    </div>
                  </div>
                  <div style={{ marginTop: 12 }}>
                    <button onClick={reset} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
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
        style={{
          flexShrink: 0,
          padding: '12px 24px',
          borderTop: '1px solid #21262d',
          background: '#0d1117',
        }}
      >
        <div
          style={{
            display: 'flex',
            gap: 12,
            maxWidth: 920,
            margin: '0 auto',
            alignItems: 'flex-end',
          }}
        >
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
            className="input"
            style={{ flex: 1 }}
          />
          <button
            onClick={submitAnalyze}
            disabled={submitDisabled}
            className="btn-primary"
            style={{ flexShrink: 0 }}
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
  )
}

export default App
