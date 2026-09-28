import type { CSSProperties, ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

/* ============================================================
   共享 UI 原语
   - 不含业务逻辑，纯视觉
   - 用 CSS 变量与 .card/.panel/.input 等类
   ============================================================ */

/** 卡片标题区：左侧图标 + 标题，右侧可选操作 */
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
        <Icon size={16} style={{ color: '#2dd4bf' }} strokeWidth={2} />
        <span style={{ fontSize: 14, fontWeight: 600, color: '#e5e7eb' }}>{title}</span>
        {hint && (
          <span style={{ fontSize: 12, color: '#6b7280' }}>· {hint}</span>
        )}
      </div>
      {actions}
    </div>
  )
}

/** 大数字卡片（label + value） */
export function Stat({
  label,
  value,
  accent = false,
}: {
  label: string
  value: string | number
  /** 是否高亮成青色（关键指标） */
  accent?: boolean
}) {
  return (
    <div
      style={{
        padding: 14,
        background: '#0f1419',
        border: '1px solid #1f2937',
        borderRadius: 8,
        transition: 'border-color 0.2s ease',
      }}
    >
      <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 6, letterSpacing: '0.02em', textTransform: 'uppercase' }}>
        {label}
      </div>
      <div
        className={`stat-value ${accent ? 'stat-glow' : ''}`}
        style={{
          fontSize: 22,
          fontWeight: 600,
          color: accent ? '#2dd4bf' : '#e5e7eb',
        }}
      >
        {value}
      </div>
    </div>
  )
}

/** 进度条：精致圆角 + 渐变 + 光泽 */
export function ProgressBar({
  value,
  height = 8,
}: {
  /** 0-100 */
  value: number
  height?: number
}) {
  return (
    <div
      style={{
        width: '100%',
        height,
        background: '#0f1419',
        border: '1px solid #1f2937',
        borderRadius: 999,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: `${Math.min(100, Math.max(0, value))}%`,
          height: '100%',
          background: 'linear-gradient(90deg, #2dd4bf 0%, #22d3ee 100%)',
          borderRadius: 999,
          transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: '0 0 8px rgba(45, 212, 191, 0.4)',
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
  tone?: 'neutral' | 'accent' | 'success' | 'error' | 'warning' | 'info'
  icon?: LucideIcon
}) {
  const styles: Record<string, { bg: string; color: string; border: string }> = {
    neutral: { bg: 'rgba(156, 163, 175, 0.1)', color: '#9ca3af', border: 'rgba(156, 163, 175, 0.25)' },
    accent: { bg: 'rgba(45, 212, 191, 0.12)', color: '#2dd4bf', border: 'rgba(45, 212, 191, 0.3)' },
    success: { bg: 'rgba(34, 197, 94, 0.12)', color: '#22c55e', border: 'rgba(34, 197, 94, 0.3)' },
    error: { bg: 'rgba(239, 68, 68, 0.12)', color: '#ef4444', border: 'rgba(239, 68, 68, 0.3)' },
    warning: { bg: 'rgba(245, 158, 11, 0.12)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' },
    info: { bg: 'rgba(59, 130, 246, 0.12)', color: '#3b82f6', border: 'rgba(59, 130, 246, 0.3)' },
  }
  const s = styles[tone]
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        fontSize: 11,
        fontWeight: 500,
        background: s.bg,
        color: s.color,
        border: `1px solid ${s.border}`,
        borderRadius: 999,
        whiteSpace: 'nowrap',
      }}
    >
      {Icon && <Icon size={11} strokeWidth={2.2} />}
      {children}
    </span>
  )
}

/** 错误横幅（柔和红色） */
export function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        marginTop: 12,
        padding: '10px 12px',
        background: 'rgba(239, 68, 68, 0.08)',
        border: '1px solid rgba(239, 68, 68, 0.25)',
        borderRadius: 8,
        fontSize: 13,
        color: '#fca5a5',
        whiteSpace: 'pre-wrap' as CSSProperties['whiteSpace'],
      }}
    >
      {children}
    </div>
  )
}

/** 警告横幅（柔和橙色，用于超时/拒绝等） */
export function WarningBanner({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        marginTop: 12,
        padding: '10px 12px',
        background: 'rgba(245, 158, 11, 0.08)',
        border: '1px solid rgba(245, 158, 11, 0.25)',
        borderRadius: 8,
        fontSize: 13,
        color: '#fbbf24',
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
    <div style={{ padding: 24, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
      {children}
    </div>
  )
}
