import { useState } from 'react'

// 健康检查结果状态
type HealthStatus = 'idle' | 'loading' | 'success' | 'error'

interface HealthResult {
  status: HealthStatus
  payload: string // 成功时为后端 JSON 文本，失败时为错误信息
}

/**
 * 多 Agent 金融分析 Dashboard - 第 1 步：最小骨架
 * 通过 Vite 代理连接后端 /health
 */
function App() {
  const [result, setResult] = useState<HealthResult>({
    status: 'idle',
    payload: '',
  })

  /**
   * 点击按钮：请求 GET /api/health，5 秒超时
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
    result.status === 'success' ? '#16a34a' :
    result.status === 'error' ? '#dc2626' :
    '#374151'

  return (
    <div style={{ maxWidth: 720, margin: '40px auto', padding: 24, fontFamily: 'system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif' }}>
      <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>
        多 Agent 金融分析 Dashboard
      </h1>
      <p style={{ color: '#6b7280', marginBottom: 16 }}>
        后端地址：http://127.0.0.1:8000
      </p>

      <button
        onClick={checkHealth}
        disabled={result.status === 'loading'}
        style={{
          padding: '8px 16px',
          fontSize: 14,
          backgroundColor: '#2563eb',
          color: 'white',
          border: 'none',
          borderRadius: 6,
          cursor: result.status === 'loading' ? 'not-allowed' : 'pointer',
          opacity: result.status === 'loading' ? 0.6 : 1,
        }}
      >
        {result.status === 'loading' ? '检查中...' : '检查后端健康状态'}
      </button>

      {result.status !== 'idle' && result.status !== 'loading' && (
        <div style={{ marginTop: 16 }}>
          <div style={{ color, fontWeight: 600, marginBottom: 8 }}>
            {result.status === 'success' ? '✓ 后端连接成功' : '✗ 后端连接失败'}
          </div>
          <pre style={{
            background: '#f3f4f6',
            padding: 12,
            borderRadius: 6,
            overflow: 'auto',
            fontSize: 13,
            color: '#111827',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}>
            {result.payload}
          </pre>
        </div>
      )}

      <div style={{ marginTop: 32, padding: 12, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, fontSize: 13, color: '#92400e', lineHeight: 1.7 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>启动顺序：</div>
        <div>请先启动后端：</div>
        <pre style={{ background: '#fff', padding: 8, borderRadius: 4, marginTop: 4 }}>
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
        </pre>
        <div style={{ marginTop: 8 }}>再启动前端：</div>
        <pre style={{ background: '#fff', padding: 8, borderRadius: 4, marginTop: 4 }}>
cd frontend
npm run dev
        </pre>
      </div>
    </div>
  )
}

export default App
