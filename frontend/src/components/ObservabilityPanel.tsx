import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowLeft,
  Activity,
  DollarSign,
  BarChart3,
  FileText,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import { ErrorBanner } from './ui'

/** GET /api/metrics 返回结构 */
interface Metrics {
  total_tasks: number
  completed: number
  failed: number
  avg_tokens: number
  total_cost: number
}

/** GET /api/cost 返回结构 */
interface Cost {
  total_tokens: number
  total_cost: number
  tasks: number
  avg_cost_per_task: number
  llm_calls: number
}

interface ObservabilityPanelProps {
  /** 返回对话模式 */
  onBack: () => void
}

/**
 * 可观测性面板：聚合 /metrics /cost /overview 三个后端接口
 * 把后端已有的统计与概览数据展示给用户
 */
export function ObservabilityPanel({ onBack }: ObservabilityPanelProps) {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [cost, setCost] = useState<Cost | null>(null)
  const [overview, setOverview] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')

  async function fetchAll(): Promise<void> {
    setLoading(true)
    setError('')
    try {
      const [mResp, cResp, oResp] = await Promise.all([
        fetch('/api/metrics'),
        fetch('/api/cost'),
        fetch('/api/overview'),
      ])
      if (!mResp.ok || !cResp.ok || !oResp.ok) {
        throw new Error('部分接口返回失败')
      }
      const [m, c, o] = await Promise.all([
        mResp.json() as Promise<Metrics>,
        cResp.json() as Promise<Cost>,
        oResp.json() as Promise<{ report?: string }>,
      ])
      setMetrics(m)
      setCost(c)
      setOverview(o.report ?? '')
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(`加载可观测性数据失败：${msg}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchAll()
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 24, gap: 16, overflowY: 'auto' }}>
      {/* 顶部标题栏 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Activity size={20} style={{ color: '#58a6ff' }} />
          <span style={{ fontSize: 17, fontWeight: 600, color: '#e6edf3' }}>可观测性概览</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={fetchAll} disabled={loading} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
            {loading ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />} 刷新
          </button>
          <button onClick={onBack} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
            <ArrowLeft size={13} /> 返回对话
          </button>
        </div>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {/* 统计卡片第一行：任务概览 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <StatCard icon={<BarChart3 size={14} />} label="今日任务" value={metrics?.total_tasks ?? '-'} accent />
        <StatCard icon={<Activity size={14} />} label="成功 / 失败" value={metrics ? `${metrics.completed} / ${metrics.failed}` : '-'} />
        <StatCard icon={<FileText size={14} />} label="平均 tokens" value={metrics?.avg_tokens ?? '-'} />
        <StatCard icon={<DollarSign size={14} />} label="今日总成本(元)" value={metrics?.total_cost ?? '-'} accent />
      </div>

      {/* 统计卡片第二行：成本明细 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <StatCard label="今日总 tokens" value={cost?.total_tokens ?? '-'} />
        <StatCard label="平均每任务成本(元)" value={cost?.avg_cost_per_task ?? '-'} accent />
        <StatCard label="成本记录任务数" value={cost?.tasks ?? '-'} />
      </div>

      {/* overview Markdown 报告 */}
      {overview && (
        <div style={{ marginTop: 8, padding: 16, border: '1px solid #21262d', borderRadius: 8, background: '#0d1117' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <FileText size={16} style={{ color: '#58a6ff' }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>全局概览报告</span>
          </div>
          <div className="markdown-body" style={{ fontSize: 14, lineHeight: 1.6, color: '#e6edf3' }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{overview}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}

/** 统计卡片：图标 + 标签 + 数值 */
function StatCard({ icon, label, value, accent }: { icon?: ReactNode; label: string; value: string | number; accent?: boolean }) {
  return (
    <div style={{ padding: 12, border: '1px solid #21262d', borderRadius: 8, background: '#0d1117' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, color: '#6e7681', fontSize: 12, letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 600 }}>
        {icon}
        {label}
      </div>
      <div className="stat-value" style={{ fontSize: 24, fontWeight: 600, color: accent ? '#58a6ff' : '#e6edf3' }}>
        {value}
      </div>
    </div>
  )
}
