import type { CSSProperties, ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

/* ============================================================
   共享 UI 原语：分析报告风
   - 杂志风小标题
   - 数字直接铺，无背景无边框
   ============================================================ */

/** 区块标题：杂志风（小号、大字距、弱灰、图标同色） */
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
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon size={14} style={{ color: '#5a6270' }} strokeWidth={2} />
        <span style={{
          fontSize: 12,
          fontWeight: 600,
          color: '#5a6270',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
        }}>
          {title}
        </span>
        {hint && (
          <span style={{ fontSize: 12, color: '#5a6270', letterSpacing: '0.05em' }}>· {hint}</span>
        )}
      </div>
      {actions}
    </div>
  )
}

/** 大数字：无背景无边框，直接铺在页面上 */
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
        color: '#5a6270',
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
          color: accent ? '#2dd4bf' : '#e5e7eb',
        }}
      >
        {value}
      </div>
    </div>
  )
}

/** 进度条：纯青色，保留 width transition */
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
        background: '#0a0e14',
        border: '1px solid #141a22',
        borderRadius: 999,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: `${Math.min(100, Math.max(0, value))}%`,
          height: '100%',
          background: '#2dd4bf',
          borderRadius: 999,
          transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      />
    </div>
  )
}

/** 状态徽章（极简） */
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
    neutral: { bg: 'rgba(139, 146, 158, 0.08)', color: '#8b929e', border: 'rgba(139, 146, 158, 0.2)' },
    accent: { bg: 'rgba(45, 212, 191, 0.1)', color: '#2dd4bf', border: 'rgba(45, 212, 191, 0.25)' },
    success: { bg: 'rgba(34, 197, 94, 0.1)', color: '#22c55e', border: 'rgba(34, 197, 94, 0.25)' },
    error: { bg: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.25)' },
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
        marginTop: 16,
        padding: '10px 12px',
        background: 'rgba(239, 68, 68, 0.06)',
        border: '1px solid rgba(239, 68, 68, 0.2)',
        borderRadius: 4,
        fontSize: 14,
        color: '#fca5a5',
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
        marginTop: 16,
        padding: '10px 12px',
        background: 'rgba(139, 146, 158, 0.06)',
        border: '1px solid rgba(139, 146, 158, 0.2)',
        borderRadius: 4,
        fontSize: 14,
        color: '#8b929e',
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
    <div style={{ padding: 24, textAlign: 'center', color: '#5a6270', fontSize: 14 }}>
      {children}
    </div>
  )
}
