import assert from 'node:assert/strict'
import { test } from 'node:test'
import { shouldUseMockApi } from '../src/api/mode.ts'

test('production always selects the real API even if mock mode is configured', () => {
  assert.equal(shouldUseMockApi(true, true), false)
  assert.equal(shouldUseMockApi(true, false), false)
})

test('development selects mock API only when explicitly enabled', () => {
  assert.equal(shouldUseMockApi(false, true), true)
  assert.equal(shouldUseMockApi(false, false), false)
})

test('importing the mock store does not read browser storage', async () => {
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    get() {
      throw new Error('localStorage was accessed during module import')
    },
  })

  const { mockStore } = await import('../src/api/mock/store.ts')
  const entries = new Map<string, string>()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key: string) => entries.get(key) ?? null,
      setItem: (key: string, value: string) => entries.set(key, value),
    },
  })
  mockStore.update((state) => { state.nextId = 5 })
  assert.equal(mockStore.nextId(), 5)
  assert.match([...entries.values()][0], /"nextId":6/)
})
