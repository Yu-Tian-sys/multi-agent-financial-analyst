import { useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'

interface MetricsResp {
  total_tasks: number
  completed: number
  failed: number
  avg_tokens: number
  total_cost: number
}

interface CostResp {
  total_tokens: number
  total_cost: number
  tasks: number
  avg_cost_per_task: number
  llm_calls: number
}

type LoadResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string }

interface LoadState {
  loading: boolean
  metrics: LoadResult<MetricsResp> | null
  cost: LoadResult<CostResp> | null
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

  useEffect(() => {
    void fetchAll()
  }, [])

  const m = state.metrics?.ok ? state.metrics.data : null
  const c = state.cost?.ok ? state.cost.data : null
  const o = state.overview?.ok ? state.overview.data : null

  const totalTasks = m?.total_tasks ?? c?.tasks ?? 0
  const completed = m?.completed ?? 0
  const failed = m?.failed ?? 0
  const others = Math.max(0, totalTasks - completed - failed)
  const successRate = totalTasks > 0 ? Math.round((completed / totalTasks) * 100) : 0
  const totalCost = c?.total_cost ?? m?.total_cost ?? 0
  const totalTokens = c?.total_tokens ?? 0

  const statusBars = [
    { name: 'completed', count: completed, color: '#22c55e' },
    { name: 'failed', count: failed, color: '#ef4444' },
    { name: 'others', count: others, color: '#8b929e' },
  ].filter((b) => b.count > 0)
  const maxBar = Math.max(1, ...statusBars.map((b) => b.count))

  // 数字卡片：无背景无边框，直接铺（仅重点数字用青色）
  const cards = [
    { label: '今日任务数', value: totalTasks, accent: false },
    { label: '今日成功', value: completed, accent: false },
    { label: '今日成功率', value: `${successRate}%`, accent: true },
    { label: '今日总成本', value: `¥${totalCost.toFixed(4)}`, accent: false },
    { label: '今日总 tokens', value: totalTokens.toLocaleString(), accent: false },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <button
          onClick={() => void fetchAll()}
          disabled={state.loading}
          className="btn-ghost"
          style={{ fontSize: 14, padding: '6px 12px' }}
        >
          <RefreshCw size={14} className={state.loading ? 'animate-spin' : ''} />
          {state.loading ? '加载中' : '刷新'}
        </button>
      </div>

      {state.loading && !state.metrics && !state.cost && !state.overview && (
        <div style={{ padding: 32, textAlign: 'center', color: '#5a6270', fontSize: 14 }}>
          加载中...
        </div>
      )}

      {/* 大数字：直接铺，无背景无边框 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 32, marginBottom: 32 }}>
        {cards.map((card) => (
          <div key={card.label}>
            <div style={{
              fontSize: 12,
              color: '#5a6270',
              marginBottom: 8,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              fontWeight: 600,
            }}>
              {card.label}
            </div>
            <div
              className="stat-value"
              style={{
                fontSize: 32,
                fontWeight: 600,
                color: card.accent ? '#2dd4bf' : '#e5e7eb',
              }}
            >
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* 今日状态分布 */}
      <div>
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          marginBottom: 12,
          color: '#5a6270',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
        }}>
          今日状态分布
        </div>
        {statusBars.length === 0 ? (
          <div style={{ padding: 16, color: '#5a6270', fontSize: 14, textAlign: 'center' }}>暂无数据</div>
        ) : (
          statusBars.map((bar) => (
            <div
              key={bar.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                marginBottom: 8,
                fontSize: 14,
              }}
            >
              <span style={{ width: 120, color: '#8b929e', fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                {bar.name}
              </span>
              <div style={{ flex: 1, height: 8, background: '#0a0e14', border: '1px solid #141a22', borderRadius: 999, overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${(bar.count / maxBar) * 100}%`,
                    height: '100%',
                    background: bar.color,
                    borderRadius: 999,
                  }}
                />
              </div>
              <span
                className="stat-value"
                style={{ width: 40, textAlign: 'right', color: '#e5e7eb', fontWeight: 600, fontSize: 14 }}
              >
                {bar.count}
              </span>
            </div>
          ))
        )}
      </div>

      {/* 接口失败提示 */}
      {(state.metrics && !state.metrics.ok) || (state.cost && !state.cost.ok) || (state.overview && !state.overview.ok) ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
          {state.metrics && !state.metrics.ok && (
            <div style={{ padding: '8px 12px', background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#fca5a5', borderRadius: 4, fontSize: 14 }}>
              /metrics 加载失败：{state.metrics.error}
            </div>
          )}
          {state.cost && !state.cost.ok && (
            <div style={{ padding: '8px 12px', background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#fca5a5', borderRadius: 4, fontSize: 14 }}>
              /cost 加载失败：{state.cost.error}
            </div>
          )}
          {state.overview && !state.overview.ok && (
            <div style={{ padding: '8px 12px', background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#fca5a5', borderRadius: 4, fontSize: 14 }}>
              /overview 加载失败：{state.overview.error}
            </div>
          )}
        </div>
      ) : null}

      {o && (
        <details style={{ marginTop: 16 }}>
          <summary style={{ cursor: 'pointer', color: '#5a6270', fontSize: 12, userSelect: 'none' }}>
            查看今日总览报告
          </summary>
          <pre
            style={{
              marginTop: 12,
              padding: 16,
              background: '#0a0e14',
              border: '1px solid #141a22',
              borderRadius: 4,
              fontSize: 14,
              color: '#8b929e',
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
    </div>
  )
}
