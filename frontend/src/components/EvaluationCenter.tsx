import { useEffect, useState } from 'react'
import {
  ArrowLeft,
  Gauge,
  RefreshCw,
  Loader2,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Shield,
  FileCheck,
  Users,
  MessageSquare,
} from 'lucide-react'
import { ErrorBanner } from './ui'

/** 评估维度 */
interface Dimension {
  name: string
  score: number
  passed: boolean
  message: string
  details: Record<string, unknown>
}

/** 单只股票评估结果 */
interface StockResult {
  symbol: string
  market: string
  overall_score: number
  all_passed: boolean
  dimensions: Dimension[]
}

interface EvaluationCenterProps {
  onBack: () => void
}

/** 维度图标映射 */
const DIMENSION_ICONS: Record<string, typeof Gauge> = {
  财务指标准确率: TrendingUp,
  风险评级一致性: Shield,
  报告完整性: FileCheck,
  分析师共识对比: Users,
  辩论质量: MessageSquare,
}

/** 得分颜色 */
function scoreColor(score: number): string {
  if (score >= 0.8) return 'var(--success)'
  if (score >= 0.6) return 'var(--accent)'
  return 'var(--error)'
}

export function EvaluationCenter({ onBack }: EvaluationCenterProps) {
  const [results, setResults] = useState<StockResult[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [customTickers, setCustomTickers] = useState<string>('')
  const [source, setSource] = useState<string>('')

  async function runEvaluate(tickers?: string[]): Promise<void> {
    setLoading(true)
    setError('')
    try {
      const body = tickers && tickers.length > 0 ? { tickers } : { tickers: [] }
      const resp = await fetch('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!resp.ok) {
        throw new Error(`评估失败：${resp.status}`)
      }
      const data = await resp.json()
      setResults(data.results ?? [])
      setSource(data.source ?? '')
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  function handleCustomEvaluate(): void {
    const list = customTickers
      .split(/[,，\s]+/)
      .map((s) => s.trim())
      .filter(Boolean)
    if (list.length === 0) return
    void runEvaluate(list)
  }

  useEffect(() => {
    void runEvaluate()
  }, [])

  return (
    <div className="flex flex-col h-full p-6 gap-4 overflow-y-auto">
      {/* 顶部标题栏 */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Gauge size={20} className="text-accent" />
          <span className="text-[17px] font-semibold text-fg">Agent 评估中心</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <input
            type="text"
            value={customTickers}
            onChange={(e) => setCustomTickers(e.target.value)}
            placeholder="自定义标的，如 AAPL, 600519"
            className="w-[200px] px-3 py-1.5 rounded-md bg-app border border-edge text-[13px] text-fg placeholder:text-muted focus:outline-none focus:border-accent"
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCustomEvaluate()
            }}
          />
          <button
            onClick={handleCustomEvaluate}
            disabled={loading || !customTickers.trim()}
            className="btn-primary text-[13px] px-3 py-1.5"
          >
            评估
          </button>
          <button
            onClick={() => runEvaluate()}
            disabled={loading}
            className="btn-ghost text-[13px] px-3 py-1.5"
          >
            {loading ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <RefreshCw size={13} />
            )}{' '}
            评估最近分析
          </button>
          <button onClick={onBack} className="btn-ghost text-[13px] px-3 py-1.5">
            <ArrowLeft size={13} /> 返回对话
          </button>
        </div>
      </div>

      {/* 说明 */}
      <div className="text-[12px] text-muted px-1">
        {source === 'recent'
          ? '📊 当前展示的是你最近分析过的股票的五维度评估结果，可横向对比不同标的的报告质量。'
          : source === 'custom'
            ? '📊 当前展示的是自定义标的的五维度评估结果。'
            : source === 'default'
              ? '📊 暂无分析历史，当前展示默认蓝筹股的评估结果。分析股票后此处会自动切换为你的历史标的。'
              : '📊 点击"评估最近分析"查看你分析过的股票质量，或输入自定义标的进行评估。'}
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {loading && (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Loader2 size={32} className="animate-spin text-accent" />
          <span className="text-sm text-muted">
            正在运行五维度评估（财务准确率 / 风险一致性 / 报告完整性 / 分析师共识 / 辩论质量）...
          </span>
          <span className="text-xs text-muted/70">
            {source === 'custom' ? '评估自定义标的中' : '评估你最近分析过的股票中'}
          </span>
        </div>
      )}

      {!loading && results.length > 0 && (
        <>
          {/* 汇总统计 */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-inset border border-divider rounded-lg p-4">
              <div className="text-xs text-muted mb-1 tracking-wider uppercase">评估标的</div>
              <div className="text-[28px] font-semibold mono">{results.length}</div>
            </div>
            <div className="bg-inset border border-divider rounded-lg p-4">
              <div className="text-xs text-muted mb-1 tracking-wider uppercase">平均得分</div>
              <div className="text-[28px] font-semibold mono" style={{ color: 'var(--accent)' }}>
                {(
                  results.reduce((s, r) => s + r.overall_score, 0) / results.length
                ).toFixed(2)}
              </div>
            </div>
            <div className="bg-inset border border-divider rounded-lg p-4">
              <div className="text-xs text-muted mb-1 tracking-wider uppercase">全部通过</div>
              <div className="text-[28px] font-semibold mono" style={{ color: 'var(--success)' }}>
                {results.filter((r) => r.all_passed).length}
                <span className="text-[14px] text-muted"> / {results.length}</span>
              </div>
            </div>
            <div className="bg-inset border border-divider rounded-lg p-4">
              <div className="text-xs text-muted mb-1 tracking-wider uppercase">最高得分</div>
              <div className="text-[28px] font-semibold mono">
                {Math.max(...results.map((r) => r.overall_score)).toFixed(2)}
              </div>
            </div>
          </div>

          {/* 汇总表 */}
          <div className="bg-inset border border-divider rounded-lg overflow-hidden">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-divider text-muted text-xs uppercase tracking-wider">
                  <th className="text-left px-4 py-3 font-semibold">标的</th>
                  <th className="text-left px-4 py-3 font-semibold">市场</th>
                  <th className="text-center px-4 py-3 font-semibold">综合得分</th>
                  <th className="text-center px-4 py-3 font-semibold">财务</th>
                  <th className="text-center px-4 py-3 font-semibold">风险</th>
                  <th className="text-center px-4 py-3 font-semibold">共识</th>
                  <th className="text-center px-4 py-3 font-semibold">状态</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => {
                  const fin = r.dimensions.find((d) => d.name === '财务指标准确率')
                  const risk = r.dimensions.find((d) => d.name === '风险评级一致性')
                  const cons = r.dimensions.find((d) => d.name === '分析师共识对比')
                  return (
                    <tr
                      key={r.symbol}
                      className="border-b border-divider last:border-0 hover:bg-[#1c2128]"
                    >
                      <td className="px-4 py-3 font-mono font-semibold">{r.symbol}</td>
                      <td className="px-4 py-3 text-muted">{r.market}</td>
                      <td className="px-4 py-3 text-center mono font-semibold" style={{ color: scoreColor(r.overall_score) }}>
                        {r.overall_score.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-center mono" style={{ color: fin ? scoreColor(fin.score) : 'var(--muted)' }}>
                        {fin ? fin.score.toFixed(2) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center mono" style={{ color: risk ? scoreColor(risk.score) : 'var(--muted)' }}>
                        {risk ? risk.score.toFixed(2) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center mono" style={{ color: cons ? scoreColor(cons.score) : 'var(--muted)' }}>
                        {cons ? cons.score.toFixed(2) : '-'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {r.all_passed ? (
                          <CheckCircle2 size={16} style={{ color: 'var(--success)' }} />
                        ) : (
                          <XCircle size={16} style={{ color: 'var(--error)' }} />
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* 各标的详情 */}
          {results.map((r) => (
            <div key={r.symbol} className="bg-inset border border-divider rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-[15px]">{r.symbol}</span>
                  <span className="text-xs text-muted">{r.market}</span>
                </div>
                <span
                  className="text-[20px] font-semibold mono"
                  style={{ color: scoreColor(r.overall_score) }}
                >
                  {r.overall_score.toFixed(2)}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {r.dimensions.map((d) => {
                  const Icon = DIMENSION_ICONS[d.name] ?? Gauge
                  return (
                    <div
                      key={d.name}
                      className="bg-[#0d1117] border border-divider rounded-md p-3"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-1.5">
                          <Icon size={13} className="text-muted" />
                          <span className="text-[12px] text-muted">{d.name}</span>
                        </div>
                        <span
                          className="text-[14px] font-semibold mono"
                          style={{ color: scoreColor(d.score) }}
                        >
                          {d.score.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-[12px] text-fg2 leading-relaxed">{d.message}</div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
