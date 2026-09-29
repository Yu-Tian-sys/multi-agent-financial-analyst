import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// 每个用例后自动卸载组件，避免 DOM 残留
afterEach(() => {
  cleanup()
})
