/** VITE_USE_MOCK 에 따라 목업과 실제 구현을 고른다. 화면은 여기서 내보내는 api 만 쓴다. */
import { env } from '@/config'
import { realApi } from './endpoints'
import { mockApi } from './mock'
import { shouldUseMockApi } from './mode'
import type { ApiClient } from './types'

export const isMockMode = shouldUseMockApi(import.meta.env.PROD, env.useMock)
export const api: ApiClient = isMockMode ? mockApi : realApi

export { ApiError, describeError, isApiError } from './client'
export type { ApiClient } from './types'
