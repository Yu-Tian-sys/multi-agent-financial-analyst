import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowLeft,
  GitCompare,
  Download,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Ban,
  ChevronDown,
  ChevronRight,
  Loader2,
  Sparkles,
} from 'lucide-react'
import { useCompareTask, type CompareTaskHook } from '../hooks/useCompareTask'

interface CompareViewProps {
  /** 返回对话模式 */
  onBack: () => void
}

/** 根据 current_step 返回阶段文字 */
function stageText(currentStep?: number): string {
  if (!currentStep || currentStep <= 0) return '正在准备分析...'
  const stages = [
    '正在准备分析...',
    '正在收集数据...',
    '正在分析数据...',
    '正在验证数据...',
    '正在多空辩论...',
    '正在评估风险...',
    '正在撰写报告...',
  ]
  if (currentStep >= 7) return '正在合规审查...'
  return stages[currentStep] ?? '正在分析...'
}

interface ComparePanelProps {
  /** 面板绑定的 hook 实例（左右各自一个，互不影响） */
  hook: CompareTaskHook
  /** 面板标签：股票 A / 股票 B */
  label: string
  /** 输入框 placeholder */
  placeholder: string
}

/** 对比模式单个面板：独立提交、轮询、显示报告 */
function ComparePanel({ hook, label, placeholder }: ComparePanelProps) {
  // 面板内部折叠状态（报告展开/收起）
  const [reportOpen, setReportOpen] = useState<boolean>(false)

  // 提交新任务时（taskId 变化）重置折叠状态，避免新报告沿用上一次展开
  useEffect(() => {
    setReportOpen(false)
  }, [hook.taskId])

  // 分析中（pending/running）时输入框和按钮都禁用
  const isProcessing = hook.task?.status === 'pending' || hook.task?.status === 'running'
  const inputDisabled = hook.submitting || isProcessing
  const submitDisabled = hook.submitting || !hook.topic.trim()

  return (
    <div style={{ border: '1px solid #21262d', borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* 顶部：标签 + 输入框 + 分析按钮 */}
      <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3', marginBottom: 12 }}>{label}</span>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input
          type="text"
          value={hook.topic}
          onChange={(e) => hook.setTopic(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !submitDisabled) {
              e.preventDefault()
              hook.submit()
            }
          }}
          placeholder={placeholder}
          disabled={inputDisabled}
          className="input"
          style={{ flex: 1 }}
        />
        <button
          onClick={hook.submit}
          disabled={submitDisabled}
          className="btn-primary"
          style={{ flexShrink: 0 }}
        >
          {hook.submitting ? <Loader2 size={16} className="animate-spin" /> : null}
          {hook.submitting ? '提交中...' : '分析'}
        </button>
      </div>

      {/* task_id 显示（提交后展示，方便核对） */}
      {hook.taskId && (
        <div style={{ fontSize: 12, color: '#6e7681', fontFamily: "'JetBrains Mono', 'Consolas', monospace", marginBottom: 8 }}>
          {hook.taskId}
        </div>
      )}

      {/* 下方结果区（滚动） */}
      <div style={{ flex: 1, overflowY: 'auto', marginTop: 4 }}>
        {/* a. 空状态：无 task 且无 error */}
        {!hook.task && !hook.error && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6e7681', fontSize: 13, minHeight: 120 }}>
            结果将显示在这里
          </div>
        )}

        {/* b. 分析中：脉动点 + 阶段文字 + 进度条 */}
        {hook.task && isProcessing && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                className="dot-pulse"
                style={{ width: 8, height: 8, borderRadius: '50%', background: '#58a6ff', flexShrink: 0 }}
              />
              <span style={{ fontSize: 15, color: '#e6edf3', fontWeight: 500 }}>
                {stageText(hook.task.current_step)}
              </span>
            </div>
            {hook.task.total_steps > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 16 }}>
                <div style={{ flex: 1, height: 6, borderRadius: 999, background: '#21262d', overflow: 'hidden' }}>
                  <div
                    style={{
                      width: `${hook.progressPct}%`,
                      height: '100%',
                      borderRadius: 999,
                      background: 'linear-gradient(90deg, #58a6ff, #79c0ff)',
                      transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                      boxShadow: '0 0 8px rgba(88, 166, 255, 0.5)',
                    }}
                  />
                </div>
                <span className="stat-value" style={{ fontSize: 12, color: '#8b949e', minWidth: 40, textAlign: 'right' }}>
                  {hook.progressPct}%
                </span>
              </div>
            )}
          </div>
        )}

        {/* c. 完成：绿色标题 + tokens/cost + 折叠报告 + 下载/重新分析 */}
        {hook.task?.status === 'completed' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <CheckCircle2 size={16} style={{ color: '#3fb950' }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>分析完成</span>
            </div>
            <div style={{ display: 'flex', gap: 24, padding: '8px 0', marginBottom: 12, borderBottom: '1px solid #21262d', fontSize: 13 }}>
              <div>
                <span style={{ color: '#6e7681' }}>tokens </span>
                <span className="stat-value" style={{ color: '#e6edf3', fontWeight: 600 }}>{hook.task.total_tokens}</span>
              </div>
              <div>
                <span style={{ color: '#6e7681' }}>cost </span>
                <span className="stat-value" style={{ color: '#58a6ff', fontWeight: 600 }}>{hook.task.total_cost}</span>
                <span style={{ color: '#6e7681' }}> 元</span>
              </div>
            </div>

            {/* 折叠报告 */}
            {hook.task.final_report && (
              <div>
                <div className="collapse-header" onClick={() => setReportOpen((v) => !v)}>
                  {reportOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <span>分析报告</span>
                  <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                    {/* 下载报告：stopPropagation 避免触发折叠 */}
                    <button
                      onClick={(e) => { e.stopPropagation(); hook.downloadReport() }}
                      className="btn-ghost"
                      style={{ fontSize: 12, padding: '2px 8px' }}
                    >
                      <Download size={13} /> 下载 .md
                    </button>
                    <span style={{ color: '#6e7681' }}>{reportOpen ? '收起' : '展开'}</span>
                  </span>
                </div>
                {reportOpen && (
                  <div
                    className="markdown-body"
                    style={{
                      marginTop: 8,
                      marginBottom: 8,
                      padding: 12,
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: 4,
                      maxHeight: 400,
                      overflow: 'auto',
                      fontSize: 14,
                      lineHeight: 1.7,
                      color: '#e6edf3',
                    }}
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {hook.task.final_report}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            )}

            {/* 重新分析：用相同 topic 再跑一次 */}
            <div style={{ marginTop: 12 }}>
              <button onClick={hook.submit} disabled={hook.submitting} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
                <RefreshCw size={13} /> 重新分析
              </button>
            </div>
          </div>
        )}

        {/* d. 失败：红色标题 + 错误信息 + 重新分析 */}
        {hook.task?.status === 'failed' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <XCircle size={16} style={{ color: '#f85149' }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>分析失败</span>
            </div>
            {hook.task.error && (
              <div style={{ fontSize: 13, color: '#f85149', whiteSpace: 'pre-wrap' }}>{hook.task.error}</div>
            )}
            <div style={{ marginTop: 12 }}>
              <button onClick={hook.submit} disabled={hook.submitting} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
                <RefreshCw size={13} /> 重新分析
              </button>
            </div>
          </div>
        )}

        {/* e. 拒绝：橙色标题 + 错误信息 + 重新分析 */}
        {hook.task?.status === 'rejected' && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Ban size={16} style={{ color: '#d29922' }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>任务被拒绝</span>
            </div>
            {hook.task.error && (
              <div style={{ fontSize: 13, color: '#d29922', whiteSpace: 'pre-wrap' }}>{hook.task.error}</div>
            )}
            <div style={{ marginTop: 12 }}>
              <button onClick={hook.submit} disabled={hook.submitting} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
                <RefreshCw size={13} /> 重新分析
              </button>
            </div>
          </div>
        )}

        {/* f. 错误信息（提交/轮询失败，无 task 时） */}
        {hook.error && !hook.task && (
          <div style={{ fontSize: 13, color: '#f85149', whiteSpace: 'pre-wrap' }}>{hook.error}</div>
        )}
      </div>
    </div>
  )
}

/** 对比模式视图：左右两个面板独立分析 */
export function CompareView({ onBack }: CompareViewProps) {
  // 两次调用 hook，左右面板各自独立
  const left = useCompareTask()
  const right = useCompareTask()

  // AI 对比结论相关 state
  const [compareResult, setCompareResult] = useState<{ summary: string; tokens: number; cost: number } | null>(null)
  const [compareLoading, setCompareLoading] = useState<boolean>(false)
  const [compareError, setCompareError] = useState<string>('')

  // 生成对比结论：两边都完成后可调，POST /api/compare 让 LLM 对比两份报告
  async function generateCompare(): Promise<void> {
    if (!left.taskId || !right.taskId) return
    setCompareLoading(true)
    setCompareError('')
    try {
      const resp = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id_a: left.taskId,
          task_id_b: right.taskId,
        }),
      })
      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` })) as { detail?: string }
        const msg = typeof errBody.detail === 'string' ? errBody.detail : `HTTP ${resp.status}`
        setCompareError(`生成对比结论失败：${msg}`)
        return
      }
      const data = await resp.json()
      setCompareResult(data)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setCompareError(`生成对比结论失败：${msg}`)
    } finally {
      setCompareLoading(false)
    }
  }

  // 仅当两边都完成时才显示对比结论区
  const bothCompleted = left.task?.status === 'completed' && right.task?.status === 'completed'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 24, gap: 16 }}>
      {/* 顶部标题栏 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <GitCompare size={20} style={{ color: '#58a6ff' }} />
          <span style={{ fontSize: 17, fontWeight: 600, color: '#e6edf3' }}>对比分析</span>
        </div>
        <button onClick={onBack} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
          <ArrowLeft size={13} /> 返回对话
        </button>
      </div>

      {/* 双面板主体：左右等宽 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, flex: 1, overflow: 'hidden' }}>
        <ComparePanel hook={left} label="股票 A" placeholder="例如 AAPL" />
        <ComparePanel hook={right} label="股票 B" placeholder="例如 TSLA" />
      </div>

      {/* AI 对比结论区：仅当两边都完成时显示 */}
      {bothCompleted && (
        <div style={{ marginTop: 16, padding: 16, border: '1px solid #21262d', borderRadius: 8, background: '#0d1117' }}>
          {/* 顶部标题 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <Sparkles size={16} style={{ color: '#58a6ff' }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3' }}>AI 对比结论</span>
          </div>

          {/* 无结果且不在加载：显示生成按钮 */}
          {!compareResult && !compareLoading && (
            <button onClick={generateCompare} className="btn-primary" style={{ fontSize: 13, padding: '6px 12px' }}>
              <Sparkles size={13} /> 生成对比结论
            </button>
          )}

          {/* 加载中：脉动点 + 提示 */}
          {compareLoading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="dot-pulse" style={{ width: 8, height: 8, borderRadius: '50%', background: '#58a6ff', flexShrink: 0 }} />
              <span style={{ fontSize: 14, color: '#8b949e' }}>AI 正在对比两份报告...</span>
            </div>
          )}

          {/* 有结果：显示总结 + tokens/cost + 重新生成 */}
          {compareResult && !compareLoading && (
            <div>
              <div style={{ fontSize: 14, lineHeight: 1.7, color: '#e6edf3', whiteSpace: 'pre-wrap' }}>
                {compareResult.summary}
              </div>
              <div style={{ fontSize: 12, color: '#6e7681', fontFamily: "'JetBrains Mono', 'Consolas', monospace", marginTop: 8 }}>
                本次对比：{compareResult.tokens} tokens · {compareResult.cost} 元
              </div>
              <div style={{ marginTop: 8 }}>
                <button onClick={generateCompare} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
                  <RefreshCw size={13} /> 重新生成
                </button>
              </div>
            </div>
          )}

          {/* 错误信息 */}
          {compareError && !compareLoading && (
            <div>
              <div style={{ fontSize: 13, color: '#f85149', whiteSpace: 'pre-wrap' }}>{compareError}</div>
              <div style={{ marginTop: 8 }}>
                <button onClick={generateCompare} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
                  <RefreshCw size={13} /> 重试
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
