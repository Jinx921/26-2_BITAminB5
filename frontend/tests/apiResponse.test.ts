import assert from 'node:assert/strict'
import { test } from 'node:test'
import { parseSuccessfulJson } from '../src/api/response.ts'

test('successful API JSON response is parsed including the valid null response', () => {
  assert.deepEqual(parseSuccessfulJson('{"saved":true}'), { saved: true })
  assert.equal(parseSuccessfulJson('null'), null)
})

test('successful HTML fallback response is rejected instead of looking like a save', () => {
  assert.throws(
    () => parseSuccessfulJson('<!doctype html><html><body>app</body></html>'),
    /JSON이 아닌 응답/,
  )
  assert.throws(() => parseSuccessfulJson(''), /비어 있는 응답/)
})
