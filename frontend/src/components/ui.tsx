import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

/* ============================================================
   共享 UI 原语：Codex 风（GitHub Dark）
   ============================================================ */

/** 区块标题：杂志风 */
export function SectionTitle({
  icon: Icon,
  title,
  hint,
  actions,
}: {
  icon: LucideIcon
  title: string
  hint?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <Icon size={14} className="text-muted" strokeWidth={2} />
        <span className="text-xs font-semibold text-muted tracking-wider uppercase">
          {title}
        </span>
        {hint && (
          <span className="text-xs text-muted tracking-wider">· {hint}</span>
        )}
      </div>
      {actions}
    </div>
  )
}

/** 大数字 */
export function Stat({
  label,
  value,
  accent = false,
}: {
  label: string
  value: string | number
  accent?: boolean
}) {
  return (
    <div>
      <div className="text-xs text-muted mb-2 tracking-wider uppercase font-semibold">
        {label}
      </div>
      <div
        className="stat-value text-[32px] font-semibold"
        style={{ color: accent ? '#58a6ff' : '#e6edf3' }}
      >
        {value}
      </div>
    </div>
  )
}

/** 进度条：蓝色，保留 width transition */
export function ProgressBar({
  value,
  height = 8,
}: {
  value: number
  height?: number
}) {
  return (
    <div
      className="w-full bg-app border border-edge rounded-full overflow-hidden"
      style={{ height }}
    >
      <div
        className="h-full bg-accent rounded-full"
        style={{
          width: `${Math.min(100, Math.max(0, value))}%`,
          transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      />
    </div>
  )
}

/** 状态徽章 */
export function Badge({
  children,
  tone = 'neutral',
  icon: Icon,
}: {
  children: ReactNode
  tone?: 'neutral' | 'accent' | 'success' | 'error'
  icon?: LucideIcon
}) {
  const styles: Record<string, { bg: string; color: string; border: string }> = {
    neutral: { bg: 'rgba(139, 148, 158, 0.1)', color: '#8b949e', border: 'rgba(139, 148, 158, 0.3)' },
    accent: { bg: 'rgba(56, 139, 253, 0.12)', color: '#58a6ff', border: 'rgba(56, 139, 253, 0.4)' },
    success: { bg: 'rgba(63, 185, 80, 0.12)', color: '#3fb950', border: 'rgba(63, 185, 80, 0.4)' },
    error: { bg: 'rgba(248, 81, 73, 0.12)', color: '#f85149', border: 'rgba(248, 81, 73, 0.4)' },
  }
  const s = styles[tone]
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full whitespace-nowrap"
      style={{
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
      }}
    >
      {Icon && <Icon size={12} strokeWidth={2} />}
      {children}
    </span>
  )
}

/** 错误横幅 */
export function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <div
      className="mt-3 px-3 py-2.5 bg-[rgba(248,81,73,0.08)] border border-[rgba(248,81,73,0.3)] rounded-sm text-sm text-danger whitespace-pre-wrap"
    >
      {children}
    </div>
  )
}

/** 警告横幅（灰底中性） */
export function WarningBanner({ children }: { children: ReactNode }) {
  return (
    <div
      className="mt-3 px-3 py-2.5 bg-[rgba(139,148,158,0.08)] border border-[rgba(139,148,158,0.3)] rounded-sm text-sm text-fg2 whitespace-pre-wrap"
    >
      {children}
    </div>
  )
}

/** 空状态提示 */
export function EmptyHint({ children }: { children: ReactNode }) {
  return (
    <div className="p-6 text-center text-muted text-sm">
      {children}
    </div>
  )
}
