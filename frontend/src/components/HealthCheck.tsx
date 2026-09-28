import { useState } from 'react'
import { HeartPulse, ChevronDown, CheckCircle2, XCircle } from 'lucide-react'

type HealthStatus = 'idle' | 'loading' | 'success' | 'error'

interface HealthResult {
  status: HealthStatus
  payload: string
}

/**
 * 后端健康检查组件（参考用）
 * 通过 GET /api/health 验证后端是否在线，5 秒超时
 * 折叠式：默认收起，点击展开
 */
export function HealthCheck() {
  const [result, setResult] = useState<HealthResult>({
    status: 'idle',
    payload: '',
  })
  const [expanded, setExpanded] = useState<boolean>(false)

  async function checkHealth(): Promise<void> {
    setResult({ status: 'loading', payload: '' })

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)

    try {
      const resp = await fetch('/api/health', { signal: controller.signal })
      if (!resp.ok) {
        setResult({
          status: 'error',
          payload: `HTTP ${resp.status} ${resp.statusText}`,
        })
        return
      }
      const data: unknown = await resp.json()
      setResult({
        status: 'success',
        payload: JSON.stringify(data, null, 2),
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      const display = err instanceof DOMException && err.name === 'AbortError'
        ? '请求超时（5 秒），后端可能未启动'
        : msg
      setResult({ status: 'error', payload: display })
    } finally {
      clearTimeout(timeoutId)
    }
  }

  const color =
    result.status === 'success' ? '#22c55e' :
    result.status === 'error' ? '#ef4444' :
    '#8b929e'

  return (
    <div>
      {/* 头部：可点击折叠，底部用极淡分隔线 */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 0 16px',
          background: 'transparent',
          border: 'none',
          borderBottom: '1px solid #141a22',
          color: '#8b929e',
          cursor: 'pointer',
          fontSize: 14,
          fontWeight: 500,
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <HeartPulse size={14} style={{ color: '#5a6270' }} />
          后端健康检查（参考）
        </span>
        <ChevronDown
          size={14}
          style={{
            transition: 'transform 0.2s ease',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
          }}
        />
      </button>

      {expanded && (
        <div style={{ paddingTop: 16 }}>
          <button
            onClick={checkHealth}
            disabled={result.status === 'loading'}
            className="btn-ghost"
            style={{ fontSize: 14 }}
          >
            {result.status === 'loading' ? '检查中...' : '检查后端健康状态'}
          </button>

          {result.status !== 'idle' && result.status !== 'loading' && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  color,
                  fontWeight: 600,
                  marginBottom: 12,
                  fontSize: 14,
                }}
              >
                {result.status === 'success' ? (
                  <CheckCircle2 size={14} />
                ) : (
                  <XCircle size={14} />
                )}
                {result.status === 'success' ? '后端连接成功' : '后端连接失败'}
              </div>
              <pre
                style={{
                  background: '#0a0e14',
                  border: '1px solid #141a22',
                  padding: 16,
                  borderRadius: 4,
                  overflow: 'auto',
                  fontSize: 14,
                  fontFamily: "'JetBrains Mono', 'Cascadia Code', monospace",
                  color: '#e5e7eb',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  margin: 0,
                  lineHeight: 1.5,
                }}
              >
                {result.payload}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
