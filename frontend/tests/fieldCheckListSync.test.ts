import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  buildApiUrl,
  fetchFieldCheckList,
  FIELD_CHECK_LIST_PATH,
  FIELD_CHECK_LIST_QUERY_OPTIONS,
  fieldCheckListQueryKey,
  saveFieldCheckList,
} from '../src/api/fieldCheckListSync.ts'

const sampleList = {
  region: '춘천',
  headline: '테스트 목록',
  created_at: '2026-10-18T01:00:00+09:00',
  cells: [
    {
      id: '4026_7935',
      lat: 37.8546,
      lon: 127.5753,
      emd_name: '서면',
      level: '확인 필요',
      questions: ['실제로 사람이 사는 집이 있나요?'],
      order: 1,
      highlight: false,
    },
  ],
}

test('unset API base uses the deployed site origin instead of device localhost', () => {
  assert.equal(
    buildApiUrl('/api/v1/field-check-list', undefined, '', 'https://field.example.test'),
    'https://field.example.test/api/v1/field-check-list',
  )
})

test('configured API base is used for a separately deployed backend', () => {
  assert.equal(
    buildApiUrl(
      '/api/v1/field-check-list',
      undefined,
      'https://api.example.test/',
      'https://field.example.test',
    ),
    'https://api.example.test/api/v1/field-check-list',
  )
})

test('a local development API override cannot route a deployed site to each visitor device', () => {
  assert.equal(
    buildApiUrl(
      '/api/v1/field-check-list',
      undefined,
      'http://127.0.0.1:8000',
      'https://field.example.test',
    ),
    'https://field.example.test/api/v1/field-check-list',
  )
})

test('field list GET and PUT target the same backend resource', async () => {
  const calls: { path: string; method: string; body?: unknown }[] = []
  const request = async <T>(
    path: string,
    options: { method?: string; body?: unknown } = {},
  ): Promise<T> => {
    calls.push({ path, method: options.method ?? 'GET', body: options.body })
    return (options.body ?? null) as T
  }

  assert.equal(await saveFieldCheckList(request, sampleList), sampleList)
  assert.equal(await fetchFieldCheckList(request), null)
  assert.deepEqual(calls, [
    { path: FIELD_CHECK_LIST_PATH, method: 'PUT', body: sampleList },
    { path: FIELD_CHECK_LIST_PATH, method: 'GET', body: undefined },
  ])
})

test('independent login sessions share the server list and trigger a fresh GET', async () => {
  const serverLists = new Map<number, typeof sampleList>()
  const phoneCalls: string[] = []

  function sessionRequest(userId: number, calls: string[]) {
    return async <T>(
      path: string,
      options: { method?: string; body?: unknown } = {},
    ): Promise<T> => {
      calls.push(`${options.method ?? 'GET'} ${path}`)
      if (options.method === 'PUT') {
        serverLists.set(userId, options.body as typeof sampleList)
        return options.body as T
      }
      return (serverLists.get(userId) ?? null) as T
    }
  }

  const laptopRequest = sessionRequest(17, [])
  const phoneRequest = sessionRequest(17, phoneCalls)
  await saveFieldCheckList(laptopRequest, sampleList)

  assert.deepEqual(fieldCheckListQueryKey(17), ['field-check-list', 17])
  assert.deepEqual(await fetchFieldCheckList(phoneRequest), sampleList)
  assert.deepEqual(phoneCalls, [`GET ${FIELD_CHECK_LIST_PATH}`])
  assert.equal(FIELD_CHECK_LIST_QUERY_OPTIONS.staleTime, 0)
  assert.equal(FIELD_CHECK_LIST_QUERY_OPTIONS.refetchOnMount, 'always')
})

test('failed server save rejects without creating a successful local result', async () => {
  const request = async <T>(): Promise<T> => {
    throw new Error('network unavailable')
  }

  await assert.rejects(saveFieldCheckList(request, sampleList), /network unavailable/)
  await assert.rejects(fetchFieldCheckList(request), /network unavailable/)
})

test('field list query cache is isolated by authenticated user ID', () => {
  assert.notDeepEqual(fieldCheckListQueryKey(17), fieldCheckListQueryKey(28))
})
