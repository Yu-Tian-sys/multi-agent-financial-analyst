import { useEffect, useState } from 'react'

type HealthStatus = 'checking' | 'online' | 'offline'

export function StatusDot() {
  const [status, setStatus] = useState<HealthStatus>('checking')

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), 5000)

    fetch('/api/health', { signal: controller.signal })
      .then(async (resp) => {
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
        setStatus('offline')
      })
      .finally(() => {
        window.clearTimeout(timer)
      })

    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [])

  const dotColor =
    status === 'online' ? '#3fb950' :
    status === 'offline' ? '#f85149' :
    '#6e7681'
  const textColor =
    status === 'online' ? '#8b949e' :
    status === 'offline' ? '#8b949e' :
    '#6e7681'
  const text =
    status === 'online' ? '后端在线' :
    status === 'offline' ? '后端离线' :
    '检测中...'

  const animClass =
    status === 'online' ? 'status-dot-online' :
    status === 'offline' ? 'status-dot-offline' :
    ''

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div
        className={animClass}
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: dotColor,
        }}
      />
      <span style={{ fontSize: 12, color: textColor, fontWeight: 400 }}>{text}</span>
    </div>
  )
}
