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
      <div className="p-6 text-center text-muted text-sm">
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
      <div className="relative">
        {events.length > 1 && (
          <div
            className="absolute left-[7px] top-4 bottom-4 w-px bg-edge"
          />
        )}

        {events.map((e, idx) => {
          const isOpen = expanded.has(idx)
          return (
            <div
              key={idx}
              className="relative pl-7 mb-2"
            >
              <div
                className="absolute left-[3px] top-3.5 w-2 h-2 rounded-full bg-accent border-2 border-app z-[1]"
              />
              <div
                onClick={() => toggle(idx)}
                className="p-3 cursor-pointer text-sm leading-normal"
              >
                <div className="flex items-center gap-3 flex-wrap">
                  <span
                    className="text-muted text-xs"
                    style={{ fontFamily: "'JetBrains Mono', monospace" }}
                  >
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  <span className="font-medium text-fg text-sm">
                    {e.agent}
                  </span>
                  <span
                    className="text-xs px-1.5 py-px rounded-sm bg-[rgba(56,139,253,0.12)] text-accent border border-[rgba(56,139,253,0.3)]"
                    style={{ fontFamily: "'JetBrains Mono', monospace" }}
                  >
                    {e.action}
                  </span>
                  {e.duration != null && (
                    <span className="text-muted text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      {(e.duration * 1000).toFixed(0)}ms
                    </span>
                  )}
                  {e.tokens != null && e.tokens > 0 && (
                    <span className="text-muted text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      {e.tokens} tok
                    </span>
                  )}
                  {e.cost != null && e.cost > 0 && (
                    <span className="text-muted text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                      {e.cost.toFixed(4)}
                    </span>
                  )}
                  <span className="ml-auto text-muted inline-flex items-center">
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
                    className="mt-2 p-3 bg-app border border-edge rounded-sm text-sm leading-normal max-h-[300px] overflow-auto whitespace-pre-wrap [word-break:break-word] text-fg2"
                    style={{ fontFamily: "'JetBrains Mono', 'Cascadia Code', monospace" }}
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
