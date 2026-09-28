import { useEffect, useState } from 'react'
import { Activity, GitCompare, Plus } from 'lucide-react'
import { StatusDot } from './StatusDot'

// 历史任务条目（GET /api/tasks 返回的单条结构）
interface HistoryTask {
  task_id: string
  topic: string
  status: string
  created_at: string
  updated_at: string
  total_cost: number
}

interface HistorySidebarProps {
  /** 当前正在看的任务 id，用于高亮 */
  currentTaskId: string | null
  /** 点击某条历史时回调 */
  onSelect: (taskId: string) => void
  /** 点击「新对话」时回调 */
  onNew: () => void
  /** 点击「对比模式」时回调 */
  onCompare: () => void
  /** 变化时重新拉取列表 */
  refreshTrigger: number
}

/** 把 ISO 时间格式化成相对时间（刚刚 / N 分钟前 / N 小时前 / 昨天 / M月D日） */
function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (isNaN(then)) return ''
  const diff = Math.floor((Date.now() - then) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 172800) return '昨天'
  const d = new Date(then)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/** 状态对应的圆点颜色 */
function statusColor(s: string): string {
  if (s === 'completed') return '#3fb950'
  if (s === 'running' || s === 'pending') return '#58a6ff'
  if (s === 'failed') return '#f85149'
  if (s === 'rejected') return '#d29922'
  return '#6e7681'
}

export function HistorySidebar({ currentTaskId, onSelect, onNew, onCompare, refreshTrigger }: HistorySidebarProps) {
  const [tasks, setTasks] = useState<HistoryTask[]>([])
  const [loading, setLoading] = useState(false)

  // refreshTrigger 变化时拉取历史列表，5 秒超时，失败静默
  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    setLoading(true)
    fetch('/api/tasks', { signal: controller.signal })
      .then((r) => r.json())
      .then((data: { tasks?: HistoryTask[] }) => {
        if (!cancelled) setTasks(data.tasks ?? [])
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false)
        window.clearTimeout(timeout)
      })
    return () => {
      cancelled = true
      controller.abort()
      window.clearTimeout(timeout)
    }
  }, [refreshTrigger])

  return (
    <div
      style={{
        width: 260,
        flexShrink: 0,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: '#0d1117',
        borderRight: '1px solid #21262d',
      }}
    >
      {/* 顶部品牌区 */}
      <div style={{ padding: 16, borderBottom: '1px solid #21262d' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Activity size={20} style={{ color: '#58a6ff' }} strokeWidth={2} />
          <span style={{ fontSize: 15, fontWeight: 600, color: '#e6edf3' }}>金融分析助手</span>
        </div>
        <div style={{ fontSize: 12, color: '#8b949e', marginTop: 4 }}>多 Agent 协作</div>
      </div>

      {/* 新对话按钮 */}
      <button onClick={onNew} className="history-new-btn">
        <Plus size={14} /> 新对话
      </button>

      {/* 对比模式按钮 */}
      <button onClick={onCompare} className="history-new-btn">
        <GitCompare size={14} /> 对比模式
      </button>

      {/* 历史列表 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
        {tasks.length === 0 && !loading && (
          <div style={{ fontSize: 12, color: '#6e7681', textAlign: 'center', padding: 24 }}>
            暂无历史记录
          </div>
        )}
        {tasks.map((t) => (
          <div
            key={t.task_id}
            onClick={() => onSelect(t.task_id)}
            className={t.task_id === currentTaskId ? 'history-item active' : 'history-item'}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: statusColor(t.status),
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontSize: 14,
                color: '#e6edf3',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                flex: 1,
              }}
            >
              {t.topic || '(未命名)'}
            </span>
            <span style={{ fontSize: 12, color: '#6e7681', flexShrink: 0 }}>
              {formatRelativeTime(t.created_at)}
            </span>
          </div>
        ))}
      </div>

      {/* 底部状态点 */}
      <div style={{ padding: 12, borderTop: '1px solid #21262d' }}>
        <StatusDot />
      </div>
    </div>
  )
}
