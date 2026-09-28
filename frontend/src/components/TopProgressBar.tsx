interface TopProgressBarProps {
  /** 是否激活（提交中 / running 时为 true） */
  active: boolean
}

/**
 * 顶部 indeterminate 进度线
 * active 时显示一条固定在页面顶部的青色光线，循环从左滑到右
 */
export function TopProgressBar({ active }: TopProgressBarProps) {
  if (!active) return null

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 2,
        zIndex: 9999,
        overflow: 'hidden',
        pointerEvents: 'none',
        background: 'rgba(45, 212, 191, 0.08)',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '40%',
          height: '100%',
          background: 'linear-gradient(90deg, transparent, #2dd4bf, #22d3ee, #2dd4bf, transparent)',
          boxShadow: '0 0 8px rgba(45, 212, 191, 0.6)',
          animation: 'progress-slide 1.4s ease-in-out infinite',
        }}
      />
    </div>
  )
}
