import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

/** 状态种类：检测中 / 在线 / 离线 */
type HealthStatus = 'checking' | 'online' | 'offline'

/**
 * 顶部状态指示点
 * 挂载时调一次 GET /api/health，超时 5 秒
 */
export function StatusDot() {
  const [status, setStatus] = useState<HealthStatus>('checking')

  useEffect(() => {
    // AbortController：5 秒超时
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), 5000)

    fetch('/api/health', { signal: controller.signal })
      .then(async (resp) => {
        // 200 且 status === 'ok' 才算在线
        if (!resp.ok) {
          setStatus('offline')
          return
        }
        try {
          const data = (await resp.json()) as { status?: string }
          setStatus(data.status === 'ok' ? 'online' : 'offline')
        } catch {
          setStatus('offline')
        }
      })
      .catch(() => {
        // 失败 / 超时都算离线
        setStatus('offline')
      })
      .finally(() => {
        window.clearTimeout(timer)
      })

    // 卸载时取消请求
    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [])

  // 颜色与文字按状态
  const dotColor =
    status === 'online' ? '#22c55e' :
    status === 'offline' ? '#ef4444' :
    '#6b7280'
  const textColor =
    status === 'online' ? '#22c55e' :
    status === 'offline' ? '#ef4444' :
    '#9ca3af'
  const text =
    status === 'online' ? '后端在线' :
    status === 'offline' ? '后端离线' :
    '检测中...'

  // pulse 动画类（仅在线/离线时启用）
  const animClass =
    status === 'online' ? 'status-dot-online' :
    status === 'offline' ? 'status-dot-offline' :
    ''

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <motion.div
        key={status}
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 15 }}
        className={animClass}
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: dotColor,
          boxShadow: status === 'checking'
            ? 'none'
            : `0 0 8px ${status === 'online' ? 'rgba(34,197,94,0.6)' : 'rgba(239,68,68,0.5)'}`,
        }}
      />
      <span style={{ fontSize: 12, color: textColor, fontWeight: 500 }}>{text}</span>
    </div>
  )
}
