import type { CSSProperties, ReactNode } from 'react'
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
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon size={14} style={{ color: '#6e7681' }} strokeWidth={2} />
        <span style={{
          fontSize: 12,
          fontWeight: 600,
          color: '#6e7681',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
        }}>
          {title}
        </span>
        {hint && (
          <span style={{ fontSize: 12, color: '#6e7681', letterSpacing: '0.05em' }}>· {hint}</span>
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
      <div style={{
        fontSize: 12,
        color: '#6e7681',
        marginBottom: 8,
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        fontWeight: 600,
      }}>
        {label}
      </div>
      <div
        className="stat-value"
        style={{
          fontSize: 32,
          fontWeight: 600,
          color: accent ? '#58a6ff' : '#e6edf3',
        }}
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
      style={{
        width: '100%',
        height,
        background: '#0d1117',
        border: '1px solid #30363d',
        borderRadius: 999,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: `${Math.min(100, Math.max(0, value))}%`,
          height: '100%',
          background: '#58a6ff',
          borderRadius: 999,
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
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        fontSize: 12,
        fontWeight: 500,
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
        borderRadius: 999,
        whiteSpace: 'nowrap',
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
      style={{
        marginTop: 12,
        padding: '10px 12px',
        background: 'rgba(248, 81, 73, 0.08)',
        border: '1px solid rgba(248, 81, 73, 0.3)',
        borderRadius: 4,
        fontSize: 14,
        color: '#f85149',
        whiteSpace: 'pre-wrap' as CSSProperties['whiteSpace'],
      }}
    >
      {children}
    </div>
  )
}

/** 警告横幅（灰底中性） */
export function WarningBanner({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        marginTop: 12,
        padding: '10px 12px',
        background: 'rgba(139, 148, 158, 0.08)',
        border: '1px solid rgba(139, 148, 158, 0.3)',
        borderRadius: 4,
        fontSize: 14,
        color: '#8b949e',
        whiteSpace: 'pre-wrap' as CSSProperties['whiteSpace'],
      }}
    >
      {children}
    </div>
  )
}

/** 空状态提示 */
export function EmptyHint({ children }: { children: ReactNode }) {
  return (
    <div style={{ padding: 24, textAlign: 'center', color: '#6e7681', fontSize: 14 }}>
      {children}
    </div>
  )
}
