import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { RefreshCw, TrendingUp, CheckCircle2, Percent, Coins, Cpu, AlertTriangle } from 'lucide-react'

/**
 * /metrics 接口返回结构
 */
interface MetricsResp {
  /** 今日任务总数 */
  total_tasks: number
  /** 今日完成数 */
  completed: number
  /** 今日失败数 */
  failed: number
  /** 平均 tokens */
  avg_tokens: number
  /** 今日总成本 */
  total_cost: number
}

/**
 * /cost 接口返回结构
 */
interface CostResp {
  /** 今日总 tokens */
  total_tokens: number
  /** 今日总成本 */
  total_cost: number
  /** 任务数 */
  tasks: number
  /** 平均每任务成本 */
  avg_cost_per_task: number
  /** 兼容旧字段（语义为"有成本记录的任务数"） */
  llm_calls: number
}

/**
 * 单条加载结果：成功（带数据）或失败
 */
type LoadResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string }

/** 加载状态 */
interface LoadState {
  /** 是否在加载中 */
  loading: boolean
  /** /metrics 结果 */
  metrics: LoadResult<MetricsResp> | null
  /** /cost 结果 */
  cost: LoadResult<CostResp> | null
  /** /overview 结果（Markdown 字符串） */
  overview: LoadResult<string> | null
}

/**
 * 全局指标 + 成本概览
 * 内部 fetch /api/metrics、/api/cost、/api/overview
 */
export function GlobalMetrics() {
  const [state, setState] = useState<LoadState>({
    loading: false,
    metrics: null,
    cost: null,
    overview: null,
  })

  /**
   * 拉取 3 个接口，用 Promise.all 并发
   * 任一接口失败不影响其他接口的展示
   */
  async function fetchAll(): Promise<void> {
    setState((s) => ({ ...s, loading: true }))
    const [metricsP, costP, overviewP] = [
      fetch('/api/metrics').then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const data = (await r.json()) as MetricsResp
        return { ok: true as const, data }
      }).catch((e: unknown): LoadResult<MetricsResp> => ({
        ok: false,
        error: e instanceof Error ? e.message : String(e),
      })),
      fetch('/api/cost').then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const data = (await r.json()) as CostResp
        return { ok: true as const, data }
      }).catch((e: unknown): LoadResult<CostResp> => ({
        ok: false,
        error: e instanceof Error ? e.message : String(e),
      })),
      fetch('/api/overview').then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        const data = (await r.json()) as { report?: string }
        return { ok: true as const, data: data.report ?? '' }
      }).catch((e: unknown): LoadResult<string> => ({
        ok: false,
        error: e instanceof Error ? e.message : String(e),
      })),
    ]
    const [metrics, cost, overview] = await Promise.all([metricsP, costP, overviewP])
    setState({ loading: false, metrics, cost, overview })
  }

  // 挂载时自动拉一次
  useEffect(() => {
    void fetchAll()
  }, [])

  // 派生展示数据
  const m = state.metrics?.ok ? state.metrics.data : null
  const c = state.cost?.ok ? state.cost.data : null
  const o = state.overview?.ok ? state.overview.data : null

  // 今日任务数（优先 /metrics，次之 /cost）
  const totalTasks = m?.total_tasks ?? c?.tasks ?? 0
  // 今日成功任务数
  const completed = m?.completed ?? 0
  // 今日失败任务数
  const failed = m?.failed ?? 0
  // 其他状态（running/pending/rejected 等，/metrics 未细分）
  const others = Math.max(0, totalTasks - completed - failed)
  // 成功率
  const successRate = totalTasks > 0 ? Math.round((completed / totalTasks) * 100) : 0
  // 今日总成本（/metrics 和 /cost 都有，取 /cost 优先）
  const totalCost = c?.total_cost ?? m?.total_cost ?? 0
  // 今日总 tokens
  const totalTokens = c?.total_tokens ?? 0

  // 状态分布条形图数据
  const statusBars = [
    { name: 'completed', count: completed, color: '#22c55e' },
    { name: 'failed', count: failed, color: '#ef4444' },
    { name: 'running/pending/rejected', count: others, color: '#9ca3af' },
  ].filter((b) => b.count > 0)
  const maxBar = Math.max(1, ...statusBars.map((b) => b.count))

  // 数字卡片定义（带图标 + accent 高亮关键指标）
  const cards = [
    { label: '今日任务数', value: totalTasks, icon: TrendingUp, accent: false },
    { label: '今日成功', value: completed, icon: CheckCircle2, accent: false },
    { label: '今日成功率', value: `${successRate}%`, icon: Percent, accent: true },
    { label: '今日总成本', value: `¥${totalCost.toFixed(4)}`, icon: Coins, accent: false },
    { label: '今日总 tokens', value: totalTokens.toLocaleString(), icon: Cpu, accent: false },
  ]

  return (
    <div>
      {/* 顶部：刷新按钮 */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
        <button
          onClick={() => void fetchAll()}
          disabled={state.loading}
          className="btn-ghost"
          style={{ fontSize: 12, padding: '6px 12px' }}
        >
          <RefreshCw size={12} className={state.loading ? 'spin' : ''} />
          {state.loading ? '加载中' : '刷新'}
        </button>
      </div>

      {/* 加载中（首次） */}
      {state.loading && !state.metrics && !state.cost && !state.overview && (
        <div style={{ padding: 32, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
          加载中...
        </div>
      )}

      {/* 大数字卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, marginBottom: 18 }}>
        {cards.map((card, idx) => {
          const Icon = card.icon
          return (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: idx * 0.04 }}
              style={{
                padding: 14,
                background: '#0f1419',
                border: '1px solid #1f2937',
                borderRadius: 8,
                transition: 'border-color 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: '#6b7280', letterSpacing: '0.03em', textTransform: 'uppercase' }}>
                  {card.label}
                </span>
                <Icon size={14} style={{ color: card.accent ? '#2dd4bf' : '#374151' }} />
              </div>
              <div
                className="stat-value"
                style={{
                  fontSize: 22,
                  fontWeight: 600,
                  color: card.accent ? '#2dd4bf' : '#e5e7eb',
                  letterSpacing: '-0.02em',
                }}
              >
                {card.value}
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* 今日状态分布 */}
      <div>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 10, color: '#9ca3af', letterSpacing: '0.03em', textTransform: 'uppercase' }}>
          今日状态分布
        </div>
        {statusBars.length === 0 ? (
          <div style={{ padding: 12, color: '#6b7280', fontSize: 13, textAlign: 'center' }}>暂无数据</div>
        ) : (
          statusBars.map((bar) => (
            <div
              key={bar.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                marginBottom: 6,
                fontSize: 13,
              }}
            >
              <span style={{ width: 200, color: '#9ca3af', fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                {bar.name}
              </span>
              <div style={{ flex: 1, height: 10, background: '#0f1419', border: '1px solid #1f2937', borderRadius: 999, overflow: 'hidden' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(bar.count / maxBar) * 100}%` }}
                  transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                  style={{
                    height: '100%',
                    background: `linear-gradient(90deg, ${bar.color}, ${bar.color}dd)`,
                    borderRadius: 999,
                    boxShadow: `0 0 6px ${bar.color}55`,
                  }}
                />
              </div>
              <span
                className="stat-value"
                style={{ width: 36, textAlign: 'right', color: '#e5e7eb', fontWeight: 600, fontSize: 13 }}
              >
                {bar.count}
              </span>
            </div>
          ))
        )}
      </div>

      {/* 接口失败提示 */}
      {(state.metrics && !state.metrics.ok) || (state.cost && !state.cost.ok) || (state.overview && !state.overview.ok) ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 12 }}>
          {state.metrics && !state.metrics.ok && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#fca5a5', borderRadius: 6, fontSize: 12 }}>
              <AlertTriangle size={12} /> /metrics 加载失败：{state.metrics.error}
            </div>
          )}
          {state.cost && !state.cost.ok && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#fca5a5', borderRadius: 6, fontSize: 12 }}>
              <AlertTriangle size={12} /> /cost 加载失败：{state.cost.error}
            </div>
          )}
          {state.overview && !state.overview.ok && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#fca5a5', borderRadius: 6, fontSize: 12 }}>
              <AlertTriangle size={12} /> /overview 加载失败：{state.overview.error}
            </div>
          )}
        </div>
      ) : null}

      {/* overview 报告（如果有） */}
      {o && (
        <details style={{ marginTop: 14 }}>
          <summary style={{ cursor: 'pointer', color: '#6b7280', fontSize: 12, userSelect: 'none' }}>
            查看今日总览报告
          </summary>
          <pre
            style={{
              marginTop: 8,
              padding: 12,
              background: '#0f1419',
              border: '1px solid #1f2937',
              borderRadius: 6,
              fontSize: 12,
              color: '#9ca3af',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              margin: 0,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {o}
          </pre>
        </details>
      )}

      <style>{`
        .spin { animation: spin 0.9s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}
