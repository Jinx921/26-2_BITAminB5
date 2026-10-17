import type { FieldCheckList } from '@/types/api'

export const FIELD_CHECK_LIST_PATH = '/api/v1/field-check-list'
export const FIELD_CHECK_LIST_QUERY_OPTIONS = {
  staleTime: 0,
  refetchOnMount: 'always',
} as const

export function fieldCheckListQueryKey(userId: number | undefined) {
  return ['field-check-list', userId] as const
}

export function buildApiUrl(
  path: string,
  query: Record<string, string | number | boolean | undefined | null> | undefined,
  apiBaseUrl: string,
  origin: string,
): string {
  const pageUrl = new URL(origin)
  const configuredApiUrl = apiBaseUrl ? new URL(apiBaseUrl, origin) : null
  const loopbackHosts = new Set(['localhost', '127.0.0.1', '[::1]'])
  const pointsToDevice = configuredApiUrl
    && loopbackHosts.has(configuredApiUrl.hostname)
    && !loopbackHosts.has(pageUrl.hostname)
  const base = (pointsToDevice ? origin : apiBaseUrl || origin).replace(/\/+$/, '')
  const url = new URL(path.startsWith('/') ? `${base}${path}` : path)
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    }
  }
  return url.toString()
}

type FieldCheckListRequest = <T>(
  path: string,
  options?: { method?: 'GET' | 'PUT'; body?: unknown },
) => Promise<T>

export function fetchFieldCheckList(
  request: FieldCheckListRequest,
): Promise<FieldCheckList | null> {
  return request<FieldCheckList | null>(FIELD_CHECK_LIST_PATH)
}

export function saveFieldCheckList(
  request: FieldCheckListRequest,
  list: FieldCheckList,
): Promise<FieldCheckList> {
  return request<FieldCheckList>(FIELD_CHECK_LIST_PATH, {
    method: 'PUT',
    body: list,
  })
}
