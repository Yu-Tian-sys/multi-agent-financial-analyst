import { useEffect, useState } from 'react'

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

  // 数字卡片定义
  const cards = [
    { label: '今日任务数', value: totalTasks },
    { label: '今日成功', value: completed },
    { label: '今日成功率', value: `${successRate}%` },
    { label: '今日总成本(元)', value: totalCost.toFixed(6) },
    { label: '今日总 tokens', value: totalTokens },
  ]

  return (
    <div>
      {/* 顶部：刷新按钮 */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <button
          onClick={() => void fetchAll()}
          disabled={state.loading}
          style={{
            padding: '4px 12px',
            fontSize: 12,
            backgroundColor: state.loading ? '#1f2937' : '#1f2937',
            color: '#9ca3af',
            border: '1px solid #374151',
            borderRadius: 4,
            cursor: state.loading ? 'not-allowed' : 'pointer',
          }}
        >
          {state.loading ? '加载中...' : '刷新'}
        </button>
      </div>

      {/* 加载中 */}
      {state.loading && !state.metrics && !state.cost && !state.overview && (
        <div style={{ color: '#9ca3af', fontSize: 13, padding: 20, textAlign: 'center' }}>
          加载中...
        </div>
      )}

      {/* 大数字卡片 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        {cards.map((card) => (
          <div
            key={card.label}
            style={{
              flex: 1,
              minWidth: 120,
              padding: 16,
              background: '#131820',
              border: '1px solid #1f2937',
              borderRadius: 8,
            }}
          >
            <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 4 }}>
              {card.label}
            </div>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#e5e7eb' }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* 今日状态分布 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8, color: '#e5e7eb' }}>今日状态分布</div>
        {statusBars.length === 0 ? (
          <div style={{ color: '#9ca3af', fontSize: 13, padding: 8 }}>暂无数据</div>
        ) : (
          statusBars.map((bar) => (
            <div
              key={bar.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 4,
                fontSize: 13,
              }}
            >
              <span style={{ width: 200, color: '#9ca3af' }}>{bar.name}</span>
              <div style={{ flex: 1, height: 12, background: '#1f2937', borderRadius: 6, overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${(bar.count / maxBar) * 100}%`,
                    height: '100%',
                    background: bar.color,
                    transition: 'width 0.3s',
                  }}
                />
              </div>
              <span style={{ width: 30, textAlign: 'right', color: '#e5e7eb', fontWeight: 500 }}>
                {bar.count}
              </span>
            </div>
          ))
        )}
      </div>

      {/* 接口失败提示 */}
      {(state.metrics && !state.metrics.ok) || (state.cost && !state.cost.ok) || (state.overview && !state.overview.ok) ? (
        <div style={{ marginBottom: 12 }}>
          {state.metrics && !state.metrics.ok && (
            <div style={{ padding: 6, background: 'rgba(239,68,68,0.1)', color: '#ef4444', borderRadius: 4, fontSize: 12, marginBottom: 4 }}>
              /metrics 加载失败：{state.metrics.error}
            </div>
          )}
          {state.cost && !state.cost.ok && (
            <div style={{ padding: 6, background: 'rgba(239,68,68,0.1)', color: '#ef4444', borderRadius: 4, fontSize: 12, marginBottom: 4 }}>
              /cost 加载失败：{state.cost.error}
            </div>
          )}
          {state.overview && !state.overview.ok && (
            <div style={{ padding: 6, background: 'rgba(239,68,68,0.1)', color: '#ef4444', borderRadius: 4, fontSize: 12, marginBottom: 4 }}>
              /overview 加载失败：{state.overview.error}
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
