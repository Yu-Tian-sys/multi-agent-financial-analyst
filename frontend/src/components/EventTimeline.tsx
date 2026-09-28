import { useState } from 'react'
import { ChevronDown } from 'lucide-react'

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
      <div style={{ padding: 24, textAlign: 'center', color: '#6e7681', fontSize: 14 }}>
        暂无事件记录
      </div>
    )
  }

  const containerStyle: React.CSSProperties = {
    maxHeight: events.length > 50 ? 500 : undefined,
    overflowY: events.length > 50 ? 'auto' : undefined,
  }

  return (
    <div style={containerStyle}>
      <div style={{ position: 'relative' }}>
        {events.length > 1 && (
          <div
            style={{
              position: 'absolute',
              left: 7,
              top: 16,
              bottom: 16,
              width: 1,
              background: '#30363d',
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
              <div
                style={{
                  position: 'absolute',
                  left: 3,
                  top: 14,
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: '#58a6ff',
                  border: '2px solid #0d1117',
                  zIndex: 1,
                }}
              />
              <div
                onClick={() => toggle(idx)}
                style={{
                  padding: 12,
                  cursor: 'pointer',
                  fontSize: 14,
                  lineHeight: 1.5,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <span
                    style={{
                      color: '#6e7681',
                      fontSize: 12,
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  <span style={{ fontWeight: 500, color: '#e6edf3', fontSize: 14 }}>
                    {e.agent}
                  </span>
                  <span
                    style={{
                      fontSize: 12,
                      padding: '1px 6px',
                      borderRadius: 4,
                      background: 'rgba(56, 139, 253, 0.12)',
                      color: '#58a6ff',
                      border: '1px solid rgba(56, 139, 253, 0.3)',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {e.action}
                  </span>
                  {e.duration != null && (
                    <span style={{ color: '#6e7681', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                      {(e.duration * 1000).toFixed(0)}ms
                    </span>
                  )}
                  {e.tokens != null && e.tokens > 0 && (
                    <span style={{ color: '#6e7681', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                      {e.tokens} tok
                    </span>
                  )}
                  {e.cost != null && e.cost > 0 && (
                    <span style={{ color: '#6e7681', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                      {e.cost.toFixed(4)}
                    </span>
                  )}
                  <span style={{ marginLeft: 'auto', color: '#6e7681', display: 'inline-flex', alignItems: 'center' }}>
                    <ChevronDown
                      size={14}
                      style={{
                        transition: 'transform 0.2s ease',
                        transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                      }}
                    />
                  </span>
                </div>
                {isOpen && (
                  <pre
                    style={{
                      margin: '8px 0 0',
                      padding: 12,
                      background: '#0d1117',
                      border: '1px solid #30363d',
                      borderRadius: 4,
                      fontSize: 14,
                      lineHeight: 1.5,
                      maxHeight: 300,
                      overflow: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      color: '#8b949e',
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
