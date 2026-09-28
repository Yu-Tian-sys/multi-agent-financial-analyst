import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Activity,
  Sparkles,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  Ban,
  FileText,
  Share2,
  ListTree,
  RotateCcw,
  ArrowRight,
  Gauge,
} from 'lucide-react'
import { HealthCheck } from './components/HealthCheck'
import { MermaidChart } from './components/MermaidChart'
import { EventTimeline, type TraceEvent } from './components/EventTimeline'
import { GlobalMetrics } from './components/GlobalMetrics'
import { StatusDot } from './components/StatusDot'
import { SectionTitle, ProgressBar, ErrorBanner, WarningBanner, Badge } from './components/ui'

// 任务状态枚举
type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'rejected'

// 后端任务详情（只取关心的字段，其他忽略）
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

// 提交响应
interface AnalyzeResponse {
  task_id: string
  status: string
  message: string
}

// 轮询终态：到达这些状态停止轮询
const TERMINAL_STATUSES: TaskStatus[] = ['completed', 'failed', 'rejected']

// 轮询间隔（毫秒）
const POLL_INTERVAL_MS = 2000

// 轮询最大时长（毫秒，5 分钟）
const POLL_MAX_MS = 5 * 60 * 1000

/**
 * 多 Agent 金融分析 Dashboard
 * 提交分析任务 + 状态轮询
 */
function App() {
  const [topic, setTopic] = useState<string>('')
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [task, setTask] = useState<TaskInfo | null>(null)
  const [error, setError] = useState<string>('')
  const [pollTimedOut, setPollTimedOut] = useState<boolean>(false)
  const [mermaidText, setMermaidText] = useState<string>('')
  const [traceError, setTraceError] = useState<string>('')
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([])

  const pollTimerRef = useRef<number | null>(null)
  const pollStartRef = useRef<number>(0)
  const traceFetchedRef = useRef<string | null>(null)

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

  async function submitAnalyze(): Promise<void> {
    const trimmed = topic.trim()
    if (!trimmed) return

    setSubmitting(true)
    setError('')
    setTask(null)
    setTaskId(null)
    setPollTimedOut(false)
    stopPolling()

    try {
      const resp = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: trimmed,
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

  function reset(): void {
    stopPolling()
    setTopic('')
    setTaskId(null)
    setTask(null)
    setError('')
    setPollTimedOut(false)
    setMermaidText('')
    setTraceError('')
    setTraceEvents([])
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
      setMermaidText(data.mermaid ?? '')
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

  const statusIcon =
    task?.status === 'completed' ? CheckCircle2 :
    task?.status === 'failed' ? XCircle :
    task?.status === 'rejected' ? Ban :
    task?.status === 'running' ? Loader2 :
    Clock
  const statusText =
    task?.status === 'pending' ? '等待中' :
    task?.status === 'running' ? '分析中' :
    task?.status === 'completed' ? '分析完成' :
    task?.status === 'failed' ? '分析失败' :
    task?.status === 'rejected' ? '任务被拒绝' :
    '—'
  const statusTone: 'accent' | 'success' | 'error' | 'neutral' =
    task?.status === 'completed' ? 'success' :
    task?.status === 'failed' ? 'error' :
    task?.status === 'rejected' ? 'neutral' :
    'accent'

  const progressPct = task && task.total_steps > 0
    ? Math.min(100, Math.round((task.current_step / task.total_steps) * 100))
    : 0

  const submitDisabled = submitting || !topic.trim()

  // 区块样式：上下大留白
  const sectionStyle: React.CSSProperties = { padding: '40px 0' }

  return (
    <div style={{ maxWidth: 1120, margin: '0 auto', padding: '48px 48px 96px', color: '#e5e7eb' }}>
      {/* Markdown 报告渲染样式 */}
      <style>{`
        .markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
          font-weight: 600;
          margin: 16px 0 8px;
          line-height: 1.4;
        }
        .markdown-body h1 { font-size: 20px; }
        .markdown-body h2 { font-size: 14px; border-bottom: 1px solid #141a22; padding-bottom: 6px; }
        .markdown-body h3 { font-size: 14px; }
        .markdown-body h4 { font-size: 14px; }
        .markdown-body p { margin: 8px 0; }
        .markdown-body ul, .markdown-body ol { margin: 8px 0; padding-left: 24px; }
        .markdown-body li { margin: 4px 0; }
        .markdown-body table { border-collapse: collapse; width: 100%; margin: 12px 0; }
        .markdown-body th, .markdown-body td { border: 1px solid #141a22; padding: 6px 10px; text-align: left; font-size: 14px; }
        .markdown-body th { background: #11151c; font-weight: 600; color: #e5e7eb; }
        .markdown-body code { background: #11151c; padding: 2px 6px; border-radius: 4px; font-size: 12px; font-family: 'JetBrains Mono', 'Cascadia Code', monospace; color: #2dd4bf; }
        .markdown-body pre { background: #0a0e14; padding: 16px; border: 1px solid #141a22; border-radius: 4px; overflow: auto; margin: 8px 0; }
        .markdown-body pre code { background: transparent; padding: 0; font-size: 14px; color: #e5e7eb; }
        .markdown-body blockquote { border-left: 2px solid #2dd4bf; padding: 4px 12px; color: #8b929e; margin: 8px 0; background: rgba(45,212,191,0.04); border-radius: 0 4px 4px 0; }
        .markdown-body a { color: #2dd4bf; text-decoration: underline; text-decoration-color: rgba(45,212,191,0.4); }
        .markdown-body a:hover { text-decoration-color: #2dd4bf; }
        .markdown-body hr { border: none; border-top: 1px solid #141a22; margin: 16px 0; }
        .markdown-body img { max-width: 100%; }
        .markdown-body strong { color: #e5e7eb; font-weight: 600; }
      `}</style>

      {/* ========== Header ========== */}
      <header style={{ paddingBottom: 40 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#11151c',
                border: '1px solid #141a22',
                borderRadius: 8,
              }}
            >
              <Activity size={20} color="#2dd4bf" strokeWidth={2} />
            </div>
            <div>
              <h1
                style={{
                  fontSize: 32,
                  fontWeight: 600,
                  margin: 0,
                  color: '#e5e7eb',
                  letterSpacing: '-0.01em',
                }}
              >
                多 Agent 金融分析 Dashboard
              </h1>
              <p style={{ color: '#5a6270', fontSize: 12, margin: '4px 0 0' }}>
                后端地址：http://127.0.0.1:8000
              </p>
            </div>
          </div>
          <StatusDot />
        </div>
      </header>

      <hr className="divider" />

      {/* ========== 提交分析任务 ========== */}
      <section style={sectionStyle}>
        <SectionTitle icon={Sparkles} title="提交分析任务" hint="股票代码或行业名称" />
        <div style={{ display: 'flex', gap: 16, alignItems: 'stretch' }}>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="例如 AAPL 或 招商银行"
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
              <>
                <Loader2 size={14} className="animate-spin" /> 提交中
              </>
            ) : (
              <>
                提交分析 <ArrowRight size={14} />
              </>
            )}
          </button>
        </div>

        {taskId && (
          <div style={{ marginTop: 16, fontSize: 12, color: '#5a6270', display: 'flex', alignItems: 'center', gap: 6 }}>
            task_id:
            <code style={{ background: '#0a0e14', padding: '2px 6px', borderRadius: 4, color: '#2dd4bf', border: '1px solid #141a22', fontSize: 12 }}>
              {taskId}
            </code>
          </div>
        )}

        {error && !pollTimedOut && <ErrorBanner>{error}</ErrorBanner>}
        {pollTimedOut && <WarningBanner>{error}</WarningBanner>}
      </section>

      <hr className="divider" />

      {/* ========== 任务状态 ========== */}
      <section style={sectionStyle}>
        <SectionTitle icon={Gauge} title="任务状态" />
        {!task ? (
          <div style={{ padding: 16, textAlign: 'center', color: '#5a6270', fontSize: 14 }}>
            尚未提交任务
          </div>
        ) : (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Badge tone={statusTone} icon={statusIcon}>
                {statusText}
              </Badge>
              {task.topic && (
                <span style={{ fontSize: 12, color: '#5a6270' }}>· {task.topic}</span>
              )}
            </div>

            {task.total_steps > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
                  <span style={{ fontSize: 12, color: '#5a6270' }}>进度</span>
                  <span className="stat-value" style={{ fontSize: 14, color: '#2dd4bf', fontWeight: 600 }}>
                    {progressPct}%
                  </span>
                </div>
                <ProgressBar value={progressPct} />
              </div>
            )}

            {task.status === 'completed' && (
              <div style={{ display: 'flex', gap: 32, fontSize: 14 }}>
                <div>
                  <span style={{ color: '#5a6270' }}>tokens </span>
                  <span className="stat-value" style={{ color: '#e5e7eb', fontWeight: 600 }}>{task.total_tokens}</span>
                </div>
                <div>
                  <span style={{ color: '#5a6270' }}>cost </span>
                  <span className="stat-value" style={{ color: '#2dd4bf', fontWeight: 600 }}>{task.total_cost}</span>
                  <span style={{ color: '#5a6270' }}> 元</span>
                </div>
              </div>
            )}

            {task.status === 'failed' && task.error && <ErrorBanner>{task.error}</ErrorBanner>}

            {task.status === 'rejected' && (
              <WarningBanner>
                {task.error || '任务在合规预检阶段被拒绝（可能因权限/限流/成本熔断）'}
              </WarningBanner>
            )}

            <div style={{ marginTop: 16 }}>
              <button onClick={reset} className="btn-ghost">
                <RotateCcw size={14} /> 重新开始
              </button>
            </div>
          </div>
        )}
      </section>

      {/* ========== 分析报告（仅 completed） ========== */}
      {task?.status === 'completed' && task.final_report && (
        <>
          <hr className="divider" />
          <section style={sectionStyle}>
            <SectionTitle icon={FileText} title="分析报告" hint="Markdown 渲染" />
            <div
              className="markdown-body"
              style={{
                fontSize: 14,
                lineHeight: 1.6,
                color: '#e5e7eb',
                maxHeight: 600,
                overflow: 'auto',
              }}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {task.final_report}
              </ReactMarkdown>
            </div>
          </section>
        </>
      )}

      {/* ========== Agent 协作流程（仅 completed） ========== */}
      {task?.status === 'completed' && (
        <>
          <hr className="divider" />
          <section style={sectionStyle}>
            <SectionTitle icon={Share2} title="Agent 协作流程" hint="Mermaid" />
            {traceError && <ErrorBanner>{traceError}</ErrorBanner>}
            <MermaidChart chart={mermaidText} />
          </section>
        </>
      )}

      {/* ========== 事件时间线（仅 completed） ========== */}
      {task?.status === 'completed' && (
        <>
          <hr className="divider" />
          <section style={sectionStyle}>
            <SectionTitle icon={ListTree} title="事件时间线" hint={`${traceEvents.length} 个事件`} />
            {traceError && <ErrorBanner>{traceError}</ErrorBanner>}
            <EventTimeline events={traceEvents} />
          </section>
        </>
      )}

      <hr className="divider" />

      {/* ========== 全局指标 ========== */}
      <section style={sectionStyle}>
        <SectionTitle icon={Gauge} title="全局指标" hint="今日" />
        <GlobalMetrics />
      </section>

      <hr className="divider" />

      {/* ========== 健康检查 ========== */}
      <section style={sectionStyle}>
        <HealthCheck />
      </section>
    </div>
  )
}

export default App
