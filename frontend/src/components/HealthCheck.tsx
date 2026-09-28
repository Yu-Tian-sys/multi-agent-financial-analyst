import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HeartPulse, ChevronDown, CheckCircle2, XCircle } from 'lucide-react'

// 健康检查结果状态
type HealthStatus = 'idle' | 'loading' | 'success' | 'error'

interface HealthResult {
  status: HealthStatus
  payload: string // 成功时为后端 JSON 文本，失败时为错误信息
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
  // 折叠状态：默认收起
  const [expanded, setExpanded] = useState<boolean>(false)

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
    <div
      style={{
        marginTop: 20,
        background: 'linear-gradient(180deg, #161b24 0%, #131820 100%)',
        borderRadius: 12,
        border: '1px solid #1f2937',
        overflow: 'hidden',
      }}
    >
      {/* 头部：可点击折叠 */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          background: 'transparent',
          border: 'none',
          color: '#9ca3af',
          cursor: 'pointer',
          fontSize: 13,
          fontWeight: 500,
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <HeartPulse size={14} style={{ color: '#6b7280' }} />
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

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ padding: '0 16px 16px' }}>
              <button
                onClick={checkHealth}
                disabled={result.status === 'loading'}
                className="btn-ghost"
                style={{ fontSize: 12 }}
              >
                {result.status === 'loading' ? '检查中...' : '检查后端健康状态'}
              </button>

              {result.status !== 'idle' && result.status !== 'loading' && (
                <div style={{ marginTop: 12 }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      color,
                      fontWeight: 600,
                      marginBottom: 8,
                      fontSize: 13,
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
                      background: '#0f1419',
                      border: '1px solid #1f2937',
                      padding: 12,
                      borderRadius: 6,
                      overflow: 'auto',
                      fontSize: 12,
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
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
