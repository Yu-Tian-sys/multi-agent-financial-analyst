import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Clock, Hash, Coins, Cpu, Bot } from 'lucide-react'

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
      <div style={{ padding: 32, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
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
      {/* 事件列表 */}
      <div style={{ position: 'relative' }}>
        {/* 左侧贯穿的竖线（从第一个圆点到最后一个） */}
        {events.length > 1 && (
          <div
            style={{
              position: 'absolute',
              left: 7,
              top: 16,
              bottom: 16,
              width: 2,
              background: 'linear-gradient(180deg, #2dd4bf 0%, #1f2937 100%)',
              opacity: 0.5,
            }}
          />
        )}

        {events.map((e, idx) => {
          const isOpen = expanded.has(idx)
          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2, delay: Math.min(idx * 0.02, 0.3) }}
              style={{
                position: 'relative',
                paddingLeft: 28,
                marginBottom: 6,
              }}
            >
              {/* 圆点 */}
              <div
                style={{
                  position: 'absolute',
                  left: 2,
                  top: 12,
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: '#2dd4bf',
                  border: '2px solid #0a0e14',
                  boxShadow: '0 0 0 1px #1f2937, 0 0 8px rgba(45,212,191,0.5)',
                  zIndex: 1,
                }}
              />
              {/* 行内容 */}
              <div
                onClick={() => toggle(idx)}
                style={{
                  background: '#0f1419',
                  border: '1px solid #1f2937',
                  borderRadius: 6,
                  padding: 10,
                  cursor: 'pointer',
                  fontSize: 13,
                  lineHeight: 1.5,
                  transition: 'border-color 0.15s ease, background 0.15s ease',
                }}
                onMouseEnter={(ev) => {
                  (ev.currentTarget as HTMLDivElement).style.borderColor = '#374151'
                }}
                onMouseLeave={(ev) => {
                  (ev.currentTarget as HTMLDivElement).style.borderColor = '#1f2937'
                }}
              >
                {/* 摘要行 */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 3,
                      color: '#6b7280',
                      fontSize: 11,
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    <Hash size={10} />{idx + 1}
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontWeight: 500, color: '#e5e7eb' }}>
                    <Bot size={12} style={{ color: '#2dd4bf' }} />
                    {e.agent}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      padding: '1px 6px',
                      borderRadius: 999,
                      background: 'rgba(45,212,191,0.12)',
                      color: '#2dd4bf',
                      border: '1px solid rgba(45,212,191,0.25)',
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    {e.action}
                  </span>
                  {e.duration != null && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: '#6b7280', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
                      <Clock size={10} />{(e.duration * 1000).toFixed(0)}ms
                    </span>
                  )}
                  {e.tokens != null && e.tokens > 0 && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: '#6b7280', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
                      <Cpu size={10} />{e.tokens} tok
                    </span>
                  )}
                  {e.cost != null && e.cost > 0 && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: '#6b7280', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
                      <Coins size={10} />{e.cost.toFixed(4)}
                    </span>
                  )}
                  <span style={{ marginLeft: 'auto', color: '#6b7280', fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 2 }}>
                    <ChevronDown
                      size={12}
                      style={{
                        transition: 'transform 0.2s ease',
                        transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                      }}
                    />
                  </span>
                </div>
                {/* 展开后的 content */}
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.pre
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
                      style={{
                        margin: '8px 0 0',
                        padding: 10,
                        background: '#0a0e14',
                        border: '1px solid #1f2937',
                        borderRadius: 4,
                        fontSize: 12,
                        lineHeight: 1.5,
                        maxHeight: 300,
                        overflow: 'auto',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        color: '#9ca3af',
                        fontFamily: "'JetBrains Mono', 'Cascadia Code', monospace",
                      }}
                    >
                      {e.content || '(空内容)'}
                    </motion.pre>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
