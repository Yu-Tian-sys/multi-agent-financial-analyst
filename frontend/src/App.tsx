import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { HealthCheck } from './components/HealthCheck'

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

  // 轮询定时器引用
  const pollTimerRef = useRef<number | null>(null)
  // 轮询开始时间戳
  const pollStartRef = useRef<number>(0)

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
  }

  // 卸载时清理定时器
  useEffect(() => {
    return () => stopPolling()
  }, [])

  // 状态对应的颜色和文案
  const statusColor =
    task?.status === 'completed' ? '#16a34a' :
    task?.status === 'failed' ? '#dc2626' :
    task?.status === 'rejected' ? '#ea580c' :
    '#2563eb'
  const statusText =
    task?.status === 'pending' ? '等待中（pending）' :
    task?.status === 'running' ? '分析中（running）' :
    task?.status === 'completed' ? '分析完成' :
    task?.status === 'failed' ? '分析失败' :
    task?.status === 'rejected' ? '任务被拒绝' :
    '—'

  // 进度百分比
  const progressPct = task && task.total_steps > 0
    ? Math.min(100, Math.round((task.current_step / task.total_steps) * 100))
    : 0

  // 按钮是否禁用
  const submitDisabled = submitting || !topic.trim()

  return (
    <div style={{ maxWidth: 720, margin: '40px auto', padding: 24, fontFamily: 'system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif', color: '#111827' }}>
      {/* 全局样式：Markdown 报告渲染样式（限定在 .markdown-body 内） */}
      <style>{`
        .markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
          font-weight: 600;
          margin: 16px 0 8px;
          line-height: 1.4;
        }
        .markdown-body h1 { font-size: 20px; }
        .markdown-body h2 { font-size: 17px; }
        .markdown-body h3 { font-size: 15px; }
        .markdown-body h4 { font-size: 14px; }
        .markdown-body p { margin: 8px 0; }
        .markdown-body ul, .markdown-body ol { margin: 8px 0; padding-left: 24px; }
        .markdown-body li { margin: 4px 0; }
        .markdown-body table { border-collapse: collapse; width: 100%; margin: 12px 0; }
        .markdown-body th, .markdown-body td { border: 1px solid #d1d5db; padding: 6px 10px; text-align: left; font-size: 13px; }
        .markdown-body th { background: #f3f4f6; font-weight: 600; }
        .markdown-body code { background: #f3f4f6; padding: 2px 4px; border-radius: 3px; font-size: 13px; font-family: ui-monospace, "Cascadia Code", "Microsoft YaHei", monospace; }
        .markdown-body pre { background: #f3f4f6; padding: 12px; border-radius: 6px; overflow: auto; margin: 8px 0; }
        .markdown-body pre code { background: transparent; padding: 0; font-size: 13px; }
        .markdown-body blockquote { border-left: 3px solid #d1d5db; padding-left: 12px; color: #6b7280; margin: 8px 0; }
        .markdown-body a { color: #2563eb; text-decoration: underline; }
        .markdown-body hr { border: none; border-top: 1px solid #e5e7eb; margin: 16px 0; }
        .markdown-body img { max-width: 100%; }
      `}</style>
      {/* 第 1 块：标题 */}
      <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 4 }}>
        多 Agent 金融分析 Dashboard
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 24, fontSize: 14 }}>
        后端地址：http://127.0.0.1:8000
      </p>

      {/* 第 2 块：提交表单 */}
      <div style={{ padding: 16, background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 14, fontWeight: 500, marginBottom: 8 }}>
          股票代码或行业名称
        </label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="例如 AAPL 或 招商银行"
          disabled={submitting}
          style={{
            width: '100%',
            padding: '8px 12px',
            fontSize: 14,
            border: '1px solid #d1d5db',
            borderRadius: 6,
            boxSizing: 'border-box',
            outline: 'none',
          }}
        />
        <button
          onClick={submitAnalyze}
          disabled={submitDisabled}
          style={{
            marginTop: 12,
            padding: '8px 16px',
            fontSize: 14,
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: 6,
            cursor: submitDisabled ? 'not-allowed' : 'pointer',
            opacity: submitDisabled ? 0.6 : 1,
          }}
        >
          {submitting ? '提交中...' : '提交分析'}
        </button>
        {/* 提交后的 task_id */}
        {taskId && (
          <div style={{ marginTop: 12, fontSize: 13, color: '#6b7280' }}>
            task_id: <code style={{ background: '#f3f4f6', padding: '2px 6px', borderRadius: 4, color: '#111827' }}>{taskId}</code>
          </div>
        )}
        {/* 错误信息（红色） */}
        {error && !pollTimedOut && (
          <div style={{ marginTop: 12, padding: 8, background: '#fef2f2', color: '#dc2626', borderRadius: 6, fontSize: 13, whiteSpace: 'pre-wrap' }}>
            {error}
          </div>
        )}
        {/* 轮询超时提示（橙色） */}
        {pollTimedOut && (
          <div style={{ marginTop: 12, padding: 8, background: '#fffbeb', color: '#92400e', borderRadius: 6, fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>

      {/* 第 3 块：任务状态 */}
      {task && (
        <div style={{ padding: 16, background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', marginBottom: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 12 }}>
            任务状态
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: statusColor, marginBottom: 12 }}>
            {statusText}
          </div>

          {/* 进度条 */}
          {task.total_steps > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>
                进度：{task.current_step} / {task.total_steps}（{progressPct}%）
              </div>
              <div style={{ width: '100%', height: 8, background: '#e5e7eb', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ width: `${progressPct}%`, height: '100%', background: '#2563eb', transition: 'width 0.3s' }} />
              </div>
            </div>
          )}

          {/* 完成时显示 token 和成本 */}
          {task.status === 'completed' && (
            <div style={{ fontSize: 13, color: '#374151' }}>
              总 tokens：<b>{task.total_tokens}</b>，总成本：<b>{task.total_cost}</b> 元
            </div>
          )}

          {/* 失败时显示错误 */}
          {task.status === 'failed' && task.error && (
            <div style={{ marginTop: 8, padding: 8, background: '#fef2f2', color: '#dc2626', borderRadius: 6, fontSize: 13, whiteSpace: 'pre-wrap' }}>
              {task.error}
            </div>
          )}

          {/* 被拒绝时显示原因 */}
          {task.status === 'rejected' && (
            <div style={{ marginTop: 8, padding: 8, background: '#fff7ed', color: '#9a3412', borderRadius: 6, fontSize: 13, whiteSpace: 'pre-wrap' }}>
              {task.error || '任务在合规预检阶段被拒绝（可能因权限/限流/成本熔断）'}
            </div>
          )}

          {/* 重新开始按钮 */}
          <button
            onClick={reset}
            style={{
              marginTop: 16,
              padding: '6px 12px',
              fontSize: 13,
              backgroundColor: '#f3f4f6',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              cursor: 'pointer',
            }}
          >
            重新开始
          </button>
        </div>
      )}

      {/* 第 3.5 块：分析报告（仅 completed 时显示） */}
      {task?.status === 'completed' && task.final_report && (
        <div style={{ padding: 16, background: 'white', borderRadius: 8, border: '1px solid #e5e7eb', marginBottom: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 12 }}>
            分析报告
          </div>
          <div className="markdown-body" style={{
            background: 'white',
            borderRadius: 8,
            border: '1px solid #e5e7eb',
            padding: 20,
            maxHeight: 600,
            overflow: 'auto',
            fontSize: 14,
            lineHeight: 1.7,
            color: '#111827',
          }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {task.final_report}
            </ReactMarkdown>
          </div>
        </div>
      )}

      {/* 第 4 块：后端健康检查（保留参考） */}
      <HealthCheck />
    </div>
  )
}

export default App
