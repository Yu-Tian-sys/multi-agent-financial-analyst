import { useEffect, useState } from 'react'
import mermaid from 'mermaid'

interface MermaidChartProps {
  /** Mermaid 文本（如 sequenceDiagram / graph TD 等） */
  chart: string
}

/**
 * Mermaid 流程图渲染组件
 * 监听 chart 变化，渲染 SVG 到容器
 * 使用 state + dangerouslySetInnerHTML 而非直接操作 DOM，
 * 避免 React 18 + StrictMode 下 useEffect 重新执行时 DOM 被替换导致的渲染丢失
 */
export function MermaidChart({ chart }: MermaidChartProps) {
  const [error, setError] = useState<string>('')
  const [svg, setSvg] = useState<string>('')

  useEffect(() => {
    // 清空之前的错误状态
    setError('')
    setSvg('')

    // 空字符串：保持占位提示（由渲染逻辑显示）
    if (!chart) {
      return
    }

    let cancelled = false
    // 每次渲染生成唯一 ID（避免多实例冲突）
    const renderId = 'mermaid-svg-' + Math.random().toString(36).slice(2, 9)

    /**
     * 异步渲染：initialize + render，拿 SVG 字符串注入 state
     */
    async function render(): Promise<void> {
      try {
        // 初始化 mermaid（幂等，重复调用无害）
        mermaid.initialize({ startOnLoad: false, theme: 'default' })
        // 渲染得到 SVG 字符串
        const { svg: svgStr } = await mermaid.render(renderId, chart)
        if (!cancelled) {
          setSvg(svgStr)
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        if (!cancelled) {
          setError(`流程图渲染失败：${msg}`)
        }
      } finally {
        // 清理 mermaid 可能残留的临时 DOM 元素（错误时会出现 #d<renderId>）
        const tmpSvg = document.getElementById(renderId)
        if (tmpSvg) tmpSvg.remove()
        const tmpErr = document.getElementById('d' + renderId)
        if (tmpErr) tmpErr.remove()
      }
    }

    void render()

    // cleanup：只标记 cancelled，不清空 state（避免 StrictMode 双调用清空已渲染的 SVG）
    return () => {
      cancelled = true
    }
  }, [chart])

  return (
    <div>
      {error && (
        <div style={{
          color: '#dc2626',
          fontSize: 13,
          padding: 12,
          background: '#fef2f2',
          borderRadius: 6,
          marginBottom: 8,
          whiteSpace: 'pre-wrap',
        }}>
          {error}
        </div>
      )}
      <div
        style={{
          background: 'white',
          overflow: 'auto',
          minHeight: 200,
          padding: 12,
          textAlign: 'center',
        }}
      >
        {svg ? (
          <div dangerouslySetInnerHTML={{ __html: svg }} />
        ) : !error ? (
          <div style={{ color: '#9ca3af', fontSize: 13, padding: 20, textAlign: 'center' }}>
            {chart ? '渲染中...' : '暂无流程图'}
          </div>
        ) : null}
      </div>
    </div>
  )
}
