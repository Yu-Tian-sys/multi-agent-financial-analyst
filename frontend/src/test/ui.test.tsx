import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ProgressBar, Badge, Stat, ErrorBanner, EmptyHint } from '../components/ui'

describe('ProgressBar', () => {
  it('按 value 渲染宽度', () => {
    const { container } = render(<ProgressBar value={50} />)
    const bar = container.querySelector('.h-full') as HTMLElement
    expect(bar.style.width).toBe('50%')
  })

  it('超过 100 时夹紧到 100%', () => {
    const { container } = render(<ProgressBar value={150} />)
    const bar = container.querySelector('.h-full') as HTMLElement
    expect(bar.style.width).toBe('100%')
  })

  it('负值夹紧到 0%', () => {
    const { container } = render(<ProgressBar value={-10} />)
    const bar = container.querySelector('.h-full') as HTMLElement
    expect(bar.style.width).toBe('0%')
  })
})

describe('Badge', () => {
  it('渲染 children 文本', () => {
    render(<Badge>已完成</Badge>)
    expect(screen.getByText('已完成')).toBeInTheDocument()
  })

  it('默认 neutral tone 使用灰色背景', () => {
    const { container } = render(<Badge>默认</Badge>)
    const span = container.firstChild as HTMLElement
    expect(span.style.background).toContain('139, 148, 158')
  })

  it('success tone 使用绿色', () => {
    const { container } = render(<Badge tone="success">成功</Badge>)
    const span = container.firstChild as HTMLElement
    expect(span.style.color).toBe('rgb(63, 185, 80)')
  })
})

describe('Stat', () => {
  it('渲染 label 和 value', () => {
    render(<Stat label="任务数" value={42} />)
    expect(screen.getByText('任务数')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('accent=true 时数值为蓝色', () => {
    const { container } = render(<Stat label="x" value="1" accent />)
    const val = container.querySelector('.stat-value') as HTMLElement
    expect(val.style.color).toBe('rgb(88, 166, 255)')
  })

  it('accent=false 时数值为前景色', () => {
    const { container } = render(<Stat label="x" value="1" />)
    const val = container.querySelector('.stat-value') as HTMLElement
    expect(val.style.color).toBe('rgb(230, 237, 243)')
  })
})

describe('ErrorBanner', () => {
  it('渲染错误文本', () => {
    render(<ErrorBanner>出错了</ErrorBanner>)
    expect(screen.getByText('出错了')).toBeInTheDocument()
  })
})

describe('EmptyHint', () => {
  it('渲染空状态提示', () => {
    render(<EmptyHint>暂无数据</EmptyHint>)
    expect(screen.getByText('暂无数据')).toBeInTheDocument()
  })
})
