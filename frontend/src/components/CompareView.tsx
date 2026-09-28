import { ArrowLeft, GitCompare } from 'lucide-react'

interface CompareViewProps {
  /** 返回对话模式 */
  onBack: () => void
}

/** 对比模式视图骨架（暂未接入提交逻辑） */
export function CompareView({ onBack }: CompareViewProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: 24, gap: 16 }}>
      {/* 顶部标题栏 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <GitCompare size={20} style={{ color: '#58a6ff' }} />
          <span style={{ fontSize: 17, fontWeight: 600, color: '#e6edf3' }}>对比分析</span>
        </div>
        <button onClick={onBack} className="btn-ghost" style={{ fontSize: 13, padding: '6px 12px' }}>
          <ArrowLeft size={13} /> 返回对话
        </button>
      </div>

      {/* 双面板主体 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, flex: 1, overflow: 'hidden' }}>
        {/* 左面板：股票 A */}
        <div style={{ border: '1px solid #21262d', borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3', marginBottom: 12 }}>股票 A</span>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input type="text" placeholder="输入股票代码，例如 AAPL" className="input" style={{ flex: 1 }} />
            <button className="btn-primary" disabled style={{ flexShrink: 0 }}>分析</button>
          </div>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6e7681', fontSize: 13 }}>
            结果将显示在这里
          </div>
        </div>

        {/* 右面板：股票 B */}
        <div style={{ border: '1px solid #21262d', borderRadius: 8, padding: 16, display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#e6edf3', marginBottom: 12 }}>股票 B</span>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input type="text" placeholder="输入股票代码，例如 TSLA" className="input" style={{ flex: 1 }} />
            <button className="btn-primary" disabled style={{ flexShrink: 0 }}>分析</button>
          </div>
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6e7681', fontSize: 13 }}>
            结果将显示在这里
          </div>
        </div>
      </div>
    </div>
  )
}
