import { useState } from 'react'

/**
 * 单个 trace 事件的结构（对应后端 traces 表字段）
 */
export interface TraceEvent {
  /** Agent 名称 */
  agent: string
  /** 动作类型（start / end / llm_call / error 等） */
  action: string
  /** 内容或输出（可能为空字符串或很长） */
  content?: string
  /** 元数据（已反序列化的 dict，前端按未知结构忽略） */
  metadata?: Record<string, unknown>
  /** 耗时（秒，浮点；start 事件可能为 null） */
  duration?: number | null
  /** tokens 数 */
  tokens?: number
  /** 成本 */
  cost?: number
  /** 创建时间戳（ISO 字符串） */
  created_at?: string
}

interface EventTimelineProps {
  /** 事件列表，按时间顺序 */
  events: TraceEvent[]
}

/**
 * trace 事件时间线
 * - 每个事件渲染为一行，左侧竖线 + 圆点，右侧内容
 * - 点击行可展开/折叠 content
 */
export function EventTimeline({ events }: EventTimelineProps) {
  // 已展开的事件索引集合
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  /** 切换某个事件的展开状态 */
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

  // 空列表占位
  if (events.length === 0) {
    return (
      <div style={{ color: '#9ca3af', fontSize: 13, padding: 20, textAlign: 'center' }}>
        暂无事件记录
      </div>
    )
  }

  // 事件超过 50 个时容器限高滚动
  const containerStyle: React.CSSProperties = {
    maxHeight: events.length > 50 ? 600 : undefined,
    overflowY: events.length > 50 ? 'auto' : undefined,
  }

  return (
    <div style={containerStyle}>
      {/* 顶部统计 */}
      <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 12 }}>
        共 {events.length} 个事件
      </div>

      {/* 事件列表 */}
      <div style={{ position: 'relative' }}>
        {/* 左侧贯穿的竖线（从第一个圆点到最后一个） */}
        {events.length > 1 && (
          <div
            style={{
              position: 'absolute',
              left: 7,
              top: 20,
              bottom: 20,
              width: 2,
              background: '#374151',
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
                  left: 2,
                  top: 10,
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: '#2dd4bf',
                  border: '2px solid #0a0e14',
                  boxShadow: '0 0 0 1px #374151',
                  zIndex: 1,
                }}
              />
              {/* 行内容 */}
              <div
                onClick={() => toggle(idx)}
                style={{
                  background: '#1f2937',
                  border: '1px solid #1f2937',
                  borderRadius: 6,
                  padding: 8,
                  cursor: 'pointer',
                  fontSize: 13,
                  lineHeight: 1.5,
                }}
              >
                {/* 摘要行 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ color: '#9ca3af', fontSize: 12, minWidth: 28 }}>
                    #{idx + 1}
                  </span>
                  <span style={{ fontWeight: 500, color: '#e5e7eb' }}>
                    {e.agent}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      padding: '1px 6px',
                      borderRadius: 3,
                      background: 'rgba(45,212,191,0.15)',
                      color: '#2dd4bf',
                    }}
                  >
                    {e.action}
                  </span>
                  {e.duration != null && (
                    <span style={{ color: '#9ca3af', fontSize: 12 }}>
                      {(e.duration * 1000).toFixed(0)}ms
                    </span>
                  )}
                  {e.tokens != null && e.tokens > 0 && (
                    <span style={{ color: '#9ca3af', fontSize: 12 }}>
                      {e.tokens} tok
                    </span>
                  )}
                  <span style={{ marginLeft: 'auto', color: '#9ca3af', fontSize: 12 }}>
                    {isOpen ? '收起 ▲' : '展开 ▼'}
                  </span>
                </div>
                {/* 展开后的 content */}
                {isOpen && (
                  <pre
                    style={{
                      margin: '8px 0 0',
                      padding: 8,
                      background: '#0a0e14',
                      border: '1px solid #374151',
                      borderRadius: 4,
                      fontSize: 12,
                      lineHeight: 1.4,
                      maxHeight: 300,
                      overflow: 'auto',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      color: '#9ca3af',
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
