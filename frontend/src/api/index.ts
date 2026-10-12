/** VITE_USE_MOCK 에 따라 목업과 실제 구현을 고른다. 화면은 여기서 내보내는 api 만 쓴다. */
import { env } from '@/config'
import { realApi } from './endpoints'
import { mockApi } from './mock'
import type { ApiClient } from './types'

export const api: ApiClient = env.useMock ? mockApi : realApi
export const isMockMode = env.useMock

export { ApiError, describeError, isApiError } from './client'
export type { ApiClient } from './types'
