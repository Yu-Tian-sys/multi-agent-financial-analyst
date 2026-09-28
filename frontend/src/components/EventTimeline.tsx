import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

/**
 * 单个 trace 事件的结构（对应后端 traces 表字段）
 */
export interface TraceEvent {
  agent: string
  action: string
  content?: string
  metadata?: Record<string, unknown>
  duration?: number | null
  tokens?: number
  cost?: number
  created_at?: string
}

interface EventTimelineProps {
  events: TraceEvent[]
}

/**
 * trace 事件时间线
 * - 每个事件渲染为一行，左侧竖线 + 圆点，右侧内容
 * - 点击行可展开/折叠 content
 */
export function EventTimeline({ events }: EventTimelineProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  function toggle(idx: number): void {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }

  if (events.length === 0) {
    return (
      <div style={{ padding: 32, textAlign: 'center', color: '#5a6270', fontSize: 14 }}>
        暂无事件记录
      </div>
    )
  }

  const containerStyle: React.CSSProperties = {
    maxHeight: events.length > 50 ? 600 : undefined,
    overflowY: events.length > 50 ? 'auto' : undefined,
  }

  return (
    <div style={containerStyle}>
      <div style={{ position: 'relative' }}>
        {/* 左侧贯穿竖线（极淡） */}
        {events.length > 1 && (
          <div
            style={{
              position: 'absolute',
              left: 7,
              top: 16,
              bottom: 16,
              width: 1,
              background: '#141a22',
            }}
          />
        )}

        {events.map((e, idx) => {
          const isOpen = expanded.has(idx)
          return (
            <div
              key={idx}
              style={{
                position: 'relative',
                paddingLeft: 28,
                marginBottom: 8,
              }}
            >
              {/* 圆点 */}
              <div
                style={{
                  position: 'absolute',
                  left: 3,
                  top: 14,
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: '#2dd4bf',
                  border: '2px solid #0a0e14',
                  zIndex: 1,
                }}
              />
              {/* 行内容：无背景无边框 */}
              <div
                onClick={() => toggle(idx)}
                style={{
                  padding: 12,
                  cursor: 'pointer',
                  fontSize: 14,
                  lineHeight: 1.5,
                }}
              >
                {/* 摘要行 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <span
                    style={{
                      color: '#5a6270',
                      fontSize: 12,
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  <span style={{ fontWeight: 500, color: '#e5e7eb', fontSize: 14 }}>
                    {e.agent}
                  </span>
                  <span
                    style={{
                      fontSize: 12,
                      padding: '1px 6px',
                      borderRadius: 4,
                      background: 'rgba(45, 212, 191, 0.08)',
                      color: '#2dd4bf',
                      border: '1px solid rgba(45, 212, 191, 0.2)',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {e.action}
                  </span>
                  {e.duration != null && (
                    <span style={{ color: '#5a6270', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                      {(e.duration * 1000).toFixed(0)}ms
                    </span>
                  )}
                  {e.tokens != null && e.tokens > 0 && (
                    <span style={{ color: '#5a6270', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                      {e.tokens} tok
                    </span>
                  )}
                  {e.cost != null && e.cost > 0 && (
                    <span style={{ color: '#5a6270', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                      {e.cost.toFixed(4)}
                    </span>
                  )}
                  <span style={{ marginLeft: 'auto', color: '#5a6270', display: 'inline-flex', alignItems: 'center' }}>
                    <ChevronDown
                      size={14}
                      style={{
                        transition: 'transform 0.2s ease',
                        transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                      }}
                    />
                  </span>
                </div>
                {/* 展开后的 content */}
                {isOpen && (
                  <pre
                    style={{
                      margin: '8px 0 0',
                      padding: 12,
                      background: '#0a0e14',
                      border: '1px solid #141a22',
                      borderRadius: 4,
                      fontSize: 14,
                      lineHeight: 1.5,
                      maxHeight: 300,
                      overflow: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      color: '#8b929e',
                      fontFamily: "'JetBrains Mono', 'Cascadia Code', monospace",
                    }}
                  >
                    {e.content || '(空内容)'}
                  </pre>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
