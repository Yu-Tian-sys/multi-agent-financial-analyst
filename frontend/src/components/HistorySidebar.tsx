import { useEffect, useState } from 'react'
import { Activity, BarChart3, Gauge, GitCompare, Plus, Trash2 } from 'lucide-react'
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
  /** 点击「可观测性」时回调 */
  onObservability: () => void
  /** 点击「评估中心」时回调 */
  onEvaluation: () => void
  /** 点击删除按钮时回调 */
  onDelete: (taskId: string) => void
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

export function HistorySidebar({ currentTaskId, onSelect, onNew, onCompare, onObservability, onEvaluation, onDelete, refreshTrigger }: HistorySidebarProps) {
  const [tasks, setTasks] = useState<HistoryTask[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  // 当前悬停的任务 id，只有悬停时才显示删除按钮
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  // refreshTrigger 变化时拉取历史列表，5 秒超时，失败显示错误提示
  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    setLoading(true)
    setError('')
    fetch('/api/tasks', { signal: controller.signal })
      .then((r) => r.json())
      .then((data: { tasks?: HistoryTask[] }) => {
        if (!cancelled) setTasks(data.tasks ?? [])
      })
      .catch(() => {
        if (!cancelled) setError('历史记录加载失败')
      })
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
      className="w-[260px] shrink-0 h-full flex flex-col bg-app border-r border-divider"
    >
      {/* 顶部品牌区 */}
      <div className="p-4 border-b border-divider">
        <div className="flex items-center gap-2">
          <Activity size={20} className="text-accent" strokeWidth={2} />
          <span className="text-[15px] font-semibold text-fg">金融分析助手</span>
        </div>
        <div className="text-xs text-fg2 mt-1">多 Agent 协作</div>
      </div>

      {/* 新对话按钮 */}
      <button onClick={onNew} className="history-new-btn">
        <Plus size={14} /> 新对话
      </button>

      {/* 对比模式按钮 */}
      <button onClick={onCompare} className="history-new-btn">
        <GitCompare size={14} /> 对比模式
      </button>

      {/* 可观测性按钮 */}
      <button onClick={onObservability} className="history-new-btn">
        <BarChart3 size={14} /> 可观测性
      </button>

      {/* 评估中心按钮 */}
      <button onClick={onEvaluation} className="history-new-btn">
        <Gauge size={14} /> 评估中心
      </button>

      {/* 历史列表 */}
      <div className="flex-1 overflow-y-auto p-2">
        {error && (
          <div className="text-xs text-danger text-center p-6">
            {error}
          </div>
        )}
        {tasks.length === 0 && !loading && !error && (
          <div className="text-xs text-muted text-center p-6">
            暂无历史记录
          </div>
        )}
        {tasks.map((t) => (
          <div
            key={t.task_id}
            onClick={() => onSelect(t.task_id)}
            onMouseEnter={() => setHoveredId(t.task_id)}
            onMouseLeave={() => setHoveredId(null)}
            className={t.task_id === currentTaskId ? 'history-item active' : 'history-item'}
          >
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: statusColor(t.status) }}
            />
            <span
              className="text-sm text-fg whitespace-nowrap overflow-hidden text-ellipsis flex-1"
            >
              {t.topic || '(未命名)'}
            </span>
            <span className="text-xs text-muted shrink-0">
              {formatRelativeTime(t.created_at)}
            </span>
            {hoveredId === t.task_id && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  if (window.confirm('确定删除这条分析记录吗？')) {
                    onDelete(t.task_id)
                  }
                }}
                className="bg-transparent border-none cursor-pointer p-0 ml-1 shrink-0 flex items-center text-muted"
                onMouseEnter={(e) => { e.currentTarget.style.color = '#f85149' }}
                onMouseLeave={(e) => { e.currentTarget.style.color = '#6e7681' }}
                title="删除"
              >
                <Trash2 size={13} />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* 底部状态点 */}
      <div className="p-3 border-t border-divider">
        <StatusDot />
      </div>
    </div>
  )
}
