import assert from 'node:assert/strict'
import { test } from 'node:test'
import { validateVercelApiBaseUrl } from '../src/config/apiBaseUrl.ts'

test('Vercel production build requires an explicit remote HTTPS API address', () => {
  assert.throws(() => validateVercelApiBaseUrl(undefined, true), /VITE_API_BASE_URL/)
  assert.throws(
    () => validateVercelApiBaseUrl('http://127.0.0.1:8000', true),
    /localhost가 아닌 HTTPS/,
  )
  assert.throws(
    () => validateVercelApiBaseUrl('http://api.example.test', true),
    /localhost가 아닌 HTTPS/,
  )
  assert.doesNotThrow(() =>
    validateVercelApiBaseUrl('https://api.example.test', true),
  )
})

test('single-container builds may keep same-origin API routing', () => {
  assert.doesNotThrow(() => validateVercelApiBaseUrl(undefined, false))
})
