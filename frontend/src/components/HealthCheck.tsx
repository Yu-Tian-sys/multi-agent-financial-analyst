import { useState } from 'react'

// 健康检查结果状态
type HealthStatus = 'idle' | 'loading' | 'success' | 'error'

interface HealthResult {
  status: HealthStatus
  payload: string // 成功时为后端 JSON 文本，失败时为错误信息
}

/**
 * 后端健康检查组件（参考用）
 * 通过 GET /api/health 验证后端是否在线，5 秒超时
 */
export function HealthCheck() {
  const [result, setResult] = useState<HealthResult>({
    status: 'idle',
    payload: '',
  })

  /**
   * 点击按钮：GET /api/health，5 秒超时
   * 通过 Vite 代理转发到 http://127.0.0.1:8000/health
   */
  async function checkHealth(): Promise<void> {
    setResult({ status: 'loading', payload: '' })

    // 用 AbortController 实现 5 秒超时
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
      // 超时会被 abort，name 为 AbortError
      const display = err instanceof DOMException && err.name === 'AbortError'
        ? '请求超时（5 秒），后端可能未启动'
        : msg
      setResult({ status: 'error', payload: display })
    } finally {
      clearTimeout(timeoutId)
    }
  }

  // 根据状态选颜色
  const color =
    result.status === 'success' ? '#22c55e' :
    result.status === 'error' ? '#ef4444' :
    '#9ca3af'

  return (
    <div style={{ marginTop: 32, padding: 16, background: '#1f2937', borderRadius: 8, border: '1px solid #1f2937' }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, color: '#9ca3af' }}>
        后端健康检查（参考）
      </h3>
      <button
        onClick={checkHealth}
        disabled={result.status === 'loading'}
        style={{
          padding: '6px 12px',
          fontSize: 13,
          backgroundColor: '#2dd4bf',
          color: '#0a0e14',
          border: 'none',
          borderRadius: 6,
          cursor: result.status === 'loading' ? 'not-allowed' : 'pointer',
          opacity: result.status === 'loading' ? 0.6 : 1,
        }}
      >
        {result.status === 'loading' ? '检查中...' : '检查后端健康状态'}
      </button>

      {result.status !== 'idle' && result.status !== 'loading' && (
        <div style={{ marginTop: 12 }}>
          <div style={{ color, fontWeight: 600, marginBottom: 8 }}>
            {result.status === 'success' ? '✓ 后端连接成功' : '✗ 后端连接失败'}
          </div>
          <pre style={{
            background: '#1f2937',
            padding: 12,
            borderRadius: 6,
            overflow: 'auto',
            fontSize: 13,
            color: '#e5e7eb',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            margin: 0,
          }}>
            {result.payload}
          </pre>
        </div>
      )}
    </div>
  )
}
