import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { StatusDot } from '../components/StatusDot'

// 构造最小 Response 片段，满足组件的 resp.ok / resp.json() 调用
function mockResponse(ok: boolean, body: unknown): Response {
  return {
    ok,
    json: async () => body,
  } as Response
}

describe('StatusDot', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('初始显示「检测中...」', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}))
    render(<StatusDot />)
    expect(screen.getByText('检测中...')).toBeInTheDocument()
  })

  it('后端返回 ok 时显示「后端在线」', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse(true, { status: 'ok' }))
    render(<StatusDot />)
    await waitFor(() => {
      expect(screen.getByText('后端在线')).toBeInTheDocument()
    })
  })

  it('后端返回非 ok 状态时显示「后端离线」', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse(true, { status: 'error' }))
    render(<StatusDot />)
    await waitFor(() => {
      expect(screen.getByText('后端离线')).toBeInTheDocument()
    })
  })

  it('HTTP 非 2xx 时显示「后端离线」', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse(false, {}))
    render(<StatusDot />)
    await waitFor(() => {
      expect(screen.getByText('后端离线')).toBeInTheDocument()
    })
  })

  it('fetch 抛错时显示「后端离线」', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network'))
    render(<StatusDot />)
    await waitFor(() => {
      expect(screen.getByText('后端离线')).toBeInTheDocument()
    })
  })
})
