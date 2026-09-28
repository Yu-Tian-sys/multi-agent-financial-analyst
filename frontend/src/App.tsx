import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
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
import { TopProgressBar } from './components/TopProgressBar'
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

// 卡片入场动画（framer-motion，克制：淡入 + 上滑 8px）
const cardVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.04, duration: 0.35, ease: [0.22, 1, 0.36, 1] as const },
  }),
}

/**
 * 多 Agent 金融分析 Dashboard
 * 提交分析任务 + 状态轮询
 */
function App() {
  // 表单输入
  const [topic, setTopic] = useState<string>('')
  // 提交中
  const [submitting, setSubmitting] = useState<boolean>(false)
  // 当前 task_id
  const [taskId, setTaskId] = useState<string | null>(null)
  // 任务详情
  const [task, setTask] = useState<TaskInfo | null>(null)
  // 错误信息（提交或轮询）
  const [error, setError] = useState<string>('')
  // 轮询超时标记
  const [pollTimedOut, setPollTimedOut] = useState<boolean>(false)
  // Mermaid 流程图文本（来自 /trace 接口）
  const [mermaidText, setMermaidText] = useState<string>('')
  // 拉取 trace 失败的错误信息
  const [traceError, setTraceError] = useState<string>('')
  // trace 事件列表（来自 /trace 接口，用于时间线渲染）
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([])
  // 任务刚完成标记（用于触发卡片闪光动画，1.5s 后自动关闭）
  const [justCompleted, setJustCompleted] = useState<boolean>(false)

  // 轮询定时器引用
  const pollTimerRef = useRef<number | null>(null)
  // 轮询开始时间戳
  const pollStartRef = useRef<number>(0)
  // 已拉取过 trace 的 task_id（避免重复拉取）
  const traceFetchedRef = useRef<string | null>(null)

  /**
   * 停止轮询（清理定时器）
   */
  function stopPolling(): void {
    if (pollTimerRef.current !== null) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  /**
   * 轮询单次：查询任务状态
   * 终态停止；非终态安排下一次
   */
  async function pollOnce(tid: string): Promise<void> {
    // 超时检查
    const elapsed = Date.now() - pollStartRef.current
    if (elapsed > POLL_MAX_MS) {
      setPollTimedOut(true)
      setError('轮询超时，请稍后手动刷新')
      return
    }

    try {
      const resp = await fetch(`/api/task/${encodeURIComponent(tid)}`)
      if (!resp.ok) {
        // 尝试解析 JSON 错误体，失败则用状态码
        const errBody = await resp.json().catch(() => ({ detail: `HTTP ${resp.status} ${resp.statusText}` })) as { detail?: string }
        const msg = typeof errBody.detail === 'string' ? errBody.detail : `HTTP ${resp.status}`
        setError(`查询任务状态失败：${msg}`)
        return
      }
      const data = await resp.json() as Partial<TaskInfo>
      // 合并到 state（缺失字段填默认值）
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
      // 终态停止
      if (TERMINAL_STATUSES.includes(merged.status)) {
        return
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(`查询任务状态失败：${msg}`)
      return
    }

    // 安排下一次
    pollTimerRef.current = window.setTimeout(() => {
      void pollOnce(tid)
    }, POLL_INTERVAL_MS)
  }

  /**
   * 启动轮询
   */
  function startPolling(tid: string): void {
    stopPolling()
    setPollTimedOut(false)
    pollStartRef.current = Date.now()
    void pollOnce(tid)
  }

  /**
   * 提交分析任务
   */
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
        // 尝试解析后端错误 detail，失败则用状态码
        const errBody = await resp.json().catch(() => ({ detail: `HTTP ${resp.status} ${resp.statusText}` })) as { detail?: string }
        const msg = (errBody && typeof errBody.detail === 'string') ? errBody.detail : `提交失败 HTTP ${resp.status}`
        setError(msg)
        return
      }
      const data = await resp.json() as AnalyzeResponse
      setTaskId(data.task_id)
      // 立即开始轮询
      startPolling(data.task_id)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(`提交失败：${msg}`)
    } finally {
      setSubmitting(false)
    }
  }

  /**
   * 重新开始：清空所有状态并停止轮询
   */
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

  /**
   * 拉取任务追踪（仅 completed 时调一次）
   * 读 /api/trace/{task_id} 的 mermaid 字段
   */
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

  // 任务完成时自动拉取一次 trace（只调一次，用 ref 去重）
  useEffect(() => {
    if (task?.status === 'completed' && task.task_id && traceFetchedRef.current !== task.task_id) {
      traceFetchedRef.current = task.task_id
      void fetchTrace(task.task_id)
    }
  }, [task?.status, task?.task_id])

  // 卸载时清理定时器
  useEffect(() => {
    return () => stopPolling()
  }, [])

  // 任务进入 completed 时触发卡片闪光动画（1.5s 后关闭）
  useEffect(() => {
    if (task?.status === 'completed') {
      setJustCompleted(true)
      const t = window.setTimeout(() => setJustCompleted(false), 1500)
      return () => window.clearTimeout(t)
    }
  }, [task?.status])

  // 状态对应的颜色、文案、图标
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
  const statusTone: 'accent' | 'success' | 'error' | 'warning' =
    task?.status === 'completed' ? 'success' :
    task?.status === 'failed' ? 'error' :
    task?.status === 'rejected' ? 'warning' :
    'accent'

  // 进度百分比
  const progressPct = task && task.total_steps > 0
    ? Math.min(100, Math.round((task.current_step / task.total_steps) * 100))
    : 0

  // 按钮是否禁用
  const submitDisabled = submitting || !topic.trim()

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '32px 32px 64px', color: '#e5e7eb' }}>
      {/* 顶部 indeterminate 进度线：提交中或 running 时显示 */}
      <TopProgressBar active={submitting || task?.status === 'running'} />
      {/* 全局样式：Markdown 报告渲染样式（限定在 .markdown-body 内） */}
      <style>{`
        .markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
          font-weight: 600;
          margin: 16px 0 8px;
          line-height: 1.4;
        }
        .markdown-body h1 { font-size: 20px; }
        .markdown-body h2 { font-size: 17px; border-bottom: 1px solid #1f2937; padding-bottom: 6px; }
        .markdown-body h3 { font-size: 15px; }
        .markdown-body h4 { font-size: 14px; }
        .markdown-body p { margin: 8px 0; }
        .markdown-body ul, .markdown-body ol { margin: 8px 0; padding-left: 24px; }
        .markdown-body li { margin: 4px 0; }
        .markdown-body table { border-collapse: collapse; width: 100%; margin: 12px 0; }
        .markdown-body th, .markdown-body td { border: 1px solid #374151; padding: 6px 10px; text-align: left; font-size: 13px; }
        .markdown-body th { background: #1f2937; font-weight: 600; color: #e5e7eb; }
        .markdown-body code { background: #1f2937; padding: 2px 5px; border-radius: 4px; font-size: 12.5px; font-family: 'JetBrains Mono', 'Cascadia Code', monospace; color: #2dd4bf; }
        .markdown-body pre { background: #0f1419; padding: 12px; border: 1px solid #1f2937; border-radius: 6px; overflow: auto; margin: 8px 0; }
        .markdown-body pre code { background: transparent; padding: 0; font-size: 13px; color: #e5e7eb; }
        .markdown-body blockquote { border-left: 3px solid #2dd4bf; padding-left: 12px; color: #9ca3af; margin: 8px 0; background: rgba(45,212,191,0.04); padding: 6px 12px; border-radius: 0 4px 4px 0; }
        .markdown-body a { color: #2dd4bf; text-decoration: underline; text-decoration-color: rgba(45,212,191,0.4); }
        .markdown-body a:hover { text-decoration-color: #2dd4bf; }
        .markdown-body hr { border: none; border-top: 1px solid #1f2937; margin: 16px 0; }
        .markdown-body img { max-width: 100%; }
        .markdown-body strong { color: #f3f4f6; font-weight: 600; }
      `}</style>

      {/* ========== Header：品牌区 + StatusDot ========== */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingBottom: 24,
          marginBottom: 24,
          borderBottom: '1px solid #1f2937',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Logo */}
          <div
            style={{
              width: 40,
              height: 40,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'linear-gradient(135deg, #2dd4bf 0%, #22d3ee 100%)',
              borderRadius: 10,
              boxShadow: '0 4px 12px rgba(45, 212, 191, 0.25), 0 1px 0 rgba(255,255,255,0.2) inset',
            }}
          >
            <Activity size={22} color="#0a0e14" strokeWidth={2.5} />
          </div>
          <div>
            <h1
              style={{
                fontSize: 22,
                fontWeight: 700,
                margin: 0,
                letterSpacing: '-0.01em',
                background: 'linear-gradient(135deg, #ffffff 0%, #2dd4bf 100%)',
                WebkitBackgroundClip: 'text',
                backgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              } as React.CSSProperties}
            >
              多 Agent 金融分析 Dashboard
            </h1>
            <p style={{ color: '#6b7280', fontSize: 13, margin: '4px 0 0' }}>
              后端地址：http://127.0.0.1:8000
            </p>
          </div>
        </div>
        <StatusDot />
      </motion.div>

      {/* ========== 主区域栅格（12 列） ========== */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: 20 }}>

        {/* ---------- Row 1：提交表单（7/12） + 任务状态（5/12） ---------- */}
        <motion.div className="card" custom={0} variants={cardVariants} initial="hidden" animate="visible" style={{ gridColumn: 'span 7', marginBottom: 0 }}>
          <SectionTitle icon={Sparkles} title="提交分析任务" hint="股票代码或行业名称" />
          <div style={{ display: 'flex', gap: 12, alignItems: 'stretch' }}>
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

          {/* 提交后的 task_id */}
          {taskId && (
            <div style={{ marginTop: 12, fontSize: 12, color: '#6b7280', display: 'flex', alignItems: 'center', gap: 6 }}>
              task_id:
              <code style={{ background: '#0f1419', padding: '2px 6px', borderRadius: 4, color: '#2dd4bf', border: '1px solid #1f2937', fontSize: 12 }}>
                {taskId}
              </code>
            </div>
          )}

          {/* 错误信息 */}
          {error && !pollTimedOut && (
            <ErrorBanner>{error}</ErrorBanner>
          )}
          {/* 轮询超时提示 */}
          {pollTimedOut && (
            <WarningBanner>{error}</WarningBanner>
          )}
        </motion.div>

        <motion.div
          className={justCompleted ? 'card card-flash' : 'card'}
          custom={1}
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          style={{ gridColumn: 'span 5', marginBottom: 0 }}
        >
          <SectionTitle icon={Gauge} title="任务状态" />
          {!task ? (
            <div style={{ padding: 16, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
              尚未提交任务
            </div>
          ) : (
            <div>
              {/* 状态徽章 + 文案 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                <Badge tone={statusTone} icon={statusIcon}>
                  {statusText}
                </Badge>
                {task.topic && (
                  <span style={{ fontSize: 12, color: '#6b7280' }}>· {task.topic}</span>
                )}
              </div>

              {/* 进度条 */}
              {task.total_steps > 0 && (
                <div style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                    <span style={{ fontSize: 12, color: '#6b7280' }}>进度</span>
                    <span className="stat-value" style={{ fontSize: 13, color: '#2dd4bf', fontWeight: 600 }}>
                      {progressPct}%
                    </span>
                  </div>
                  <ProgressBar value={progressPct} />
                </div>
              )}

              {/* 完成时显示 token 和成本 */}
              {task.status === 'completed' && (
                <div style={{ display: 'flex', gap: 16, padding: '10px 12px', background: '#0f1419', border: '1px solid #1f2937', borderRadius: 6, fontSize: 12 }}>
                  <div>
                    <span style={{ color: '#6b7280' }}>tokens </span>
                    <span className="stat-value" style={{ color: '#e5e7eb', fontWeight: 600 }}>{task.total_tokens}</span>
                  </div>
                  <div>
                    <span style={{ color: '#6b7280' }}>cost </span>
                    <span className="stat-value" style={{ color: '#2dd4bf', fontWeight: 600 }}>{task.total_cost}</span>
                    <span style={{ color: '#6b7280' }}> 元</span>
                  </div>
                </div>
              )}

              {/* 失败时显示错误 */}
              {task.status === 'failed' && task.error && (
                <ErrorBanner>{task.error}</ErrorBanner>
              )}

              {/* 被拒绝时显示原因 */}
              {task.status === 'rejected' && (
                <WarningBanner>
                  {task.error || '任务在合规预检阶段被拒绝（可能因权限/限流/成本熔断）'}
                </WarningBanner>
              )}

              {/* 重新开始按钮 */}
              <div style={{ marginTop: 14 }}>
                <button onClick={reset} className="btn-ghost">
                  <RotateCcw size={13} /> 重新开始
                </button>
              </div>
            </div>
          )}
        </motion.div>

        {/* ---------- Row 2：分析报告（7/12） + Mermaid 流程（5/12） ---------- */}
        <AnimatePresence>
          {task?.status === 'completed' && task.final_report && (
            <motion.div
              key="report"
              className="card"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              style={{ gridColumn: 'span 7', marginBottom: 0 }}
            >
              <SectionTitle icon={FileText} title="分析报告" hint="Markdown 渲染" />
              <div
                className="markdown-body panel"
                style={{
                  background: '#0f1419',
                  borderRadius: 8,
                  padding: 20,
                  maxHeight: 600,
                  overflow: 'auto',
                  fontSize: 14,
                  lineHeight: 1.75,
                  color: '#e5e7eb',
                }}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {task.final_report}
                </ReactMarkdown>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {task?.status === 'completed' && (
            <motion.div
              key="mermaid"
              className="card"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.35, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
              style={{ gridColumn: 'span 5', marginBottom: 0 }}
            >
              <SectionTitle icon={Share2} title="Agent 协作流程" hint="Mermaid" />
              {traceError && (
                <ErrorBanner>{traceError}</ErrorBanner>
              )}
              <MermaidChart chart={mermaidText} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ---------- Row 3：事件时间线（全宽） ---------- */}
        <AnimatePresence>
          {task?.status === 'completed' && (
            <motion.div
              key="timeline"
              className="card"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.35, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
              style={{ gridColumn: 'span 12', marginBottom: 0 }}
            >
              <SectionTitle icon={ListTree} title="事件时间线" hint={`${traceEvents.length} 个事件`} />
              {traceError && (
                <ErrorBanner>{traceError}</ErrorBanner>
              )}
              <EventTimeline events={traceEvents} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ---------- Row 4：全局指标（全宽） ---------- */}
        <motion.div
          className="card"
          custom={4}
          variants={cardVariants}
          initial="hidden"
          animate="visible"
          style={{ gridColumn: 'span 12', marginBottom: 0 }}
        >
          <SectionTitle icon={Gauge} title="全局指标" hint="今日" />
          <GlobalMetrics />
        </motion.div>

        {/* ---------- Row 5：健康检查（折叠保留） ---------- */}
        <div style={{ gridColumn: 'span 12' }}>
          <HealthCheck />
        </div>
      </div>
    </div>
  )
}

export default App
