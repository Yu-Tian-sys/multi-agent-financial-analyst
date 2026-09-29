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
  /** 当前用户 ID（从 App 传入，避免硬编码） */
  userId: string
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
    <div className="border border-divider rounded-lg p-4 flex flex-col overflow-hidden">
      {/* 顶部：标签 + 输入框 + 分析按钮 */}
      <span className="text-sm font-semibold text-fg mb-3">{label}</span>
      <div className="flex gap-2 mb-2">
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
          className="input flex-1"
        />
        <button
          onClick={hook.submit}
          disabled={submitDisabled}
          className="btn-primary shrink-0"
        >
          {hook.submitting ? <Loader2 size={16} className="animate-spin" /> : null}
          {hook.submitting ? '提交中...' : '分析'}
        </button>
      </div>

      {/* task_id 显示（提交后展示，方便核对） */}
      {hook.taskId && (
        <div className="text-xs text-muted mb-2" style={{ fontFamily: "'JetBrains Mono', 'Consolas', monospace" }}>
          {hook.taskId}
        </div>
      )}

      {/* 下方结果区（滚动） */}
      <div className="flex-1 overflow-y-auto mt-1">
        {/* a. 空状态：无 task 且无 error */}
        {!hook.task && !hook.error && (
          <div className="flex items-center justify-center text-muted text-[13px] min-h-[120px]">
            结果将显示在这里
          </div>
        )}

        {/* b. 分析中：脉动点 + 阶段文字 + 进度条 */}
        {hook.task && isProcessing && (
          <div>
            <div className="flex items-center gap-2.5">
              <div
                className="dot-pulse w-2 h-2 rounded-full bg-accent shrink-0"
              />
              <span className="text-[15px] text-fg font-medium">
                {stageText(hook.task.current_step)}
              </span>
            </div>
            {hook.task.total_steps > 0 && (
              <div className="flex items-center gap-3 mt-4">
                <div className="flex-1 h-1.5 rounded-full bg-divider overflow-hidden">
                  <div
                    className="h-full rounded-full bg-[linear-gradient(90deg,#58a6ff,#79c0ff)] shadow-[0_0_8px_rgba(88,166,255,0.5)]"
                    style={{
                      width: `${hook.progressPct}%`,
                      transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                    }}
                  />
                </div>
                <span className="stat-value text-xs text-fg2 min-w-10 text-right">
                  {hook.progressPct}%
                </span>
              </div>
            )}
          </div>
        )}

        {/* c. 完成：绿色标题 + tokens/cost + 折叠报告 + 下载/重新分析 */}
        {hook.task?.status === 'completed' && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 size={16} className="text-success" />
              <span className="text-sm font-semibold text-fg">分析完成</span>
            </div>
            <div className="flex gap-6 py-2 mb-3 border-b border-divider text-[13px]">
              <div>
                <span className="text-muted">tokens </span>
                <span className="stat-value text-fg font-semibold">{hook.task.total_tokens}</span>
              </div>
              <div>
                <span className="text-muted">cost </span>
                <span className="stat-value text-accent font-semibold">{hook.task.total_cost}</span>
                <span className="text-muted"> 元</span>
              </div>
            </div>

            {/* 折叠报告 */}
            {hook.task.final_report && (
              <div>
                <div className="collapse-header" onClick={() => setReportOpen((v) => !v)}>
                  {reportOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <span>分析报告</span>
                  <span className="ml-auto flex items-center gap-2">
                    {/* 下载报告：stopPropagation 避免触发折叠 */}
                    <button
                      onClick={(e) => { e.stopPropagation(); hook.downloadReport() }}
                      className="btn-ghost text-xs px-2 py-0.5"
                    >
                      <Download size={13} /> 下载 .md
                    </button>
                    <span className="text-muted">{reportOpen ? '收起' : '展开'}</span>
                  </span>
                </div>
                {reportOpen && (
                  <div
                    className="markdown-body mt-2 mb-2 p-3 bg-app border border-edge rounded-sm max-h-[400px] overflow-auto text-sm leading-[1.7] text-fg"
                  >
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {hook.task.final_report}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            )}

            {/* 重新分析：用相同 topic 再跑一次 */}
            <div className="mt-3">
              <button onClick={hook.submit} disabled={hook.submitting} className="btn-ghost text-[13px] px-3 py-1.5">
                <RefreshCw size={13} /> 重新分析
              </button>
            </div>
          </div>
        )}

        {/* d. 失败：红色标题 + 错误信息 + 重新分析 */}
        {hook.task?.status === 'failed' && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <XCircle size={16} className="text-danger" />
              <span className="text-sm font-semibold text-fg">分析失败</span>
            </div>
            {hook.task.error && (
              <div className="text-[13px] text-danger whitespace-pre-wrap">{hook.task.error}</div>
            )}
            <div className="mt-3">
              <button onClick={hook.submit} disabled={hook.submitting} className="btn-ghost text-[13px] px-3 py-1.5">
                <RefreshCw size={13} /> 重新分析
              </button>
            </div>
          </div>
        )}

        {/* e. 拒绝：橙色标题 + 错误信息 + 重新分析 */}
        {hook.task?.status === 'rejected' && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Ban size={16} className="text-[#d29922]" />
              <span className="text-sm font-semibold text-fg">任务被拒绝</span>
            </div>
            {hook.task.error && (
              <div className="text-[13px] text-[#d29922] whitespace-pre-wrap">{hook.task.error}</div>
            )}
            <div className="mt-3">
              <button onClick={hook.submit} disabled={hook.submitting} className="btn-ghost text-[13px] px-3 py-1.5">
                <RefreshCw size={13} /> 重新分析
              </button>
            </div>
          </div>
        )}

        {/* f. 错误信息（提交/轮询失败，无 task 时） */}
        {hook.error && !hook.task && (
          <div className="text-[13px] text-danger whitespace-pre-wrap">{hook.error}</div>
        )}
      </div>
    </div>
  )
}

/** 对比模式视图：左右两个面板独立分析 */
export function CompareView({ userId, onBack }: CompareViewProps) {
  // 两次调用 hook，左右面板各自独立
  const left = useCompareTask(userId)
  const right = useCompareTask(userId)

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
    <div className="flex flex-col h-full p-6 gap-4">
      {/* 顶部标题栏 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <GitCompare size={20} className="text-accent" />
          <span className="text-[17px] font-semibold text-fg">对比分析</span>
        </div>
        <button onClick={onBack} className="btn-ghost text-[13px] px-3 py-1.5">
          <ArrowLeft size={13} /> 返回对话
        </button>
      </div>

      {/* 双面板主体：左右等宽 */}
      <div className="grid grid-cols-2 gap-4 flex-1 overflow-hidden">
        <ComparePanel hook={left} label="股票 A" placeholder="例如 AAPL" />
        <ComparePanel hook={right} label="股票 B" placeholder="例如 TSLA" />
      </div>

      {/* AI 对比结论区：仅当两边都完成时显示 */}
      {bothCompleted && (
        <div className="mt-4 p-4 border border-divider rounded-lg bg-app">
          {/* 顶部标题 */}
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={16} className="text-accent" />
            <span className="text-sm font-semibold text-fg">AI 对比结论</span>
          </div>

          {/* 无结果且不在加载：显示生成按钮 */}
          {!compareResult && !compareLoading && (
            <button onClick={generateCompare} className="btn-primary text-[13px] px-3 py-1.5">
              <Sparkles size={13} /> 生成对比结论
            </button>
          )}

          {/* 加载中：脉动点 + 提示 */}
          {compareLoading && (
            <div className="flex items-center gap-2.5">
              <div className="dot-pulse w-2 h-2 rounded-full bg-accent shrink-0" />
              <span className="text-sm text-fg2">AI 正在对比两份报告...</span>
            </div>
          )}

          {/* 有结果：显示总结 + tokens/cost + 重新生成 */}
          {compareResult && !compareLoading && (
            <div>
              <div className="text-sm leading-[1.7] text-fg whitespace-pre-wrap">
                {compareResult.summary}
              </div>
              <div className="text-xs text-muted mt-2" style={{ fontFamily: "'JetBrains Mono', 'Consolas', monospace" }}>
                本次对比：{compareResult.tokens} tokens · {compareResult.cost} 元
              </div>
              <div className="mt-2">
                <button onClick={generateCompare} className="btn-ghost text-[13px] px-3 py-1.5">
                  <RefreshCw size={13} /> 重新生成
                </button>
              </div>
            </div>
          )}

          {/* 错误信息 */}
          {compareError && !compareLoading && (
            <div>
              <div className="text-[13px] text-danger whitespace-pre-wrap">{compareError}</div>
              <div className="mt-2">
                <button onClick={generateCompare} className="btn-ghost text-[13px] px-3 py-1.5">
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
