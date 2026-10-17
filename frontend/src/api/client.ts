/** fetch 래퍼. 토큰 첨부, 공통 오류 형식 파싱, Retry-After 처리를 한 곳에서 한다. */
import { env } from '@/config'
import type { ApiErrorBody } from '@/types/api'
import { buildApiUrl } from './fieldCheckListSync'

export class ApiError extends Error {
  status: number
  code: string
  requestId: string | undefined
  /** 429·503 일 때 서버가 알려준 재시도 대기 초 */
  retryAfter: number | undefined
  details: unknown

  constructor(status: number, code: string, message: string, extra?: { requestId?: string; retryAfter?: number; details?: unknown }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = extra?.requestId
    this.retryAfter = extra?.retryAfter
    this.details = extra?.details
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError
}

const TOKEN_KEY = 'bitamin.auth'

export interface StoredAuth {
  token: string
  /** epoch ms. 지나면 토큰을 버리고 다시 로그인한다 */
  expiresAt: number
}

/** 토큰은 sessionStorage 에만 둔다 (탭을 닫으면 사라짐). 저장 실패는 무시한다 */
export const tokenStore = {
  get(): StoredAuth | null {
    try {
      const raw = sessionStorage.getItem(TOKEN_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw) as StoredAuth
      if (!parsed.token || Date.now() >= parsed.expiresAt) {
        sessionStorage.removeItem(TOKEN_KEY)
        return null
      }
      return parsed
    } catch {
      return null
    }
  },
  set(auth: StoredAuth) {
    try {
      sessionStorage.setItem(TOKEN_KEY, JSON.stringify(auth))
    } catch {
      /* 저장 불가 환경 */
    }
  },
  clear() {
    try {
      sessionStorage.removeItem(TOKEN_KEY)
    } catch {
      /* ignore */
    }
  },
}

/** 401 이 나면 로그인 화면으로 보내기 위해 AuthProvider 가 등록한다 */
let onUnauthorized: (() => void) | null = null
export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  query?: Record<string, string | number | boolean | undefined | null>
  /** 기본 true. 로그인·가입처럼 토큰이 없어도 되는 요청은 false */
  auth?: boolean
  signal?: AbortSignal
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  return buildApiUrl(path, query, env.apiBaseUrl, window.location.origin)
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  if (opts.auth !== false) {
    const stored = tokenStore.get()
    if (stored) headers.Authorization = `Bearer ${stored.token}`
  }

  let res: Response
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: opts.signal,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new ApiError(0, 'network_error', '서버에 연결할 수 없습니다. 백엔드가 켜져 있는지 확인해 주세요.')
  }

  if (res.status === 204) return undefined as T

  const text = await res.text()
  let json: unknown = null
  if (text) {
    try {
      json = JSON.parse(text)
    } catch {
      json = null
    }
  }

  if (!res.ok) {
    const body = (json ?? {}) as Partial<ApiErrorBody>
    const code = body.error?.code ?? `http_${res.status}`
    const message = body.error?.message ?? res.statusText ?? '요청에 실패했습니다'
    const retryHeader = res.headers.get('Retry-After')
    const retryAfter = retryHeader ? Number(retryHeader) : undefined
    const err = new ApiError(res.status, code, message, {
      requestId: body.request_id,
      retryAfter: Number.isFinite(retryAfter) ? retryAfter : undefined,
      details: body.error?.details,
    })
    if (res.status === 401 && opts.auth !== false) {
      tokenStore.clear()
      onUnauthorized?.()
    }
    throw err
  }
  return json as T
}

/** 사용자에게 보여줄 오류 문장 */
export function describeError(e: unknown): string {
  if (isApiError(e)) {
    switch (e.code) {
      case 'invalid_credentials':
        return '이메일 또는 비밀번호가 맞지 않습니다.'
      case 'unauthorized':
        return '로그인이 필요합니다.'
      case 'forbidden':
        return '이 화면을 볼 권한이 없습니다.'
      case 'rate_limit_exceeded':
        return `질문이 너무 잦습니다. ${e.retryAfter ?? 60}초 뒤에 다시 시도해 주세요.`
      case 'question_capacity_exceeded':
        return '지금 질문이 많아 잠시 기다려야 합니다. 잠시 후 다시 시도해 주세요.'
      case 'validation_error':
        return '입력 내용을 다시 확인해 주세요. 이메일 형식과 비밀번호 길이(12자 이상)를 확인하세요.'
      case 'account_unavailable':
      case 'conflict':
        return '이 이메일로는 계정을 만들 수 없습니다. 이미 가입했다면 로그인해 주세요.'
      case 'network_error':
        return e.message
      case 'internal_server_error':
        return '서버에서 답을 만들지 못했습니다. 백엔드 로그와 에이전트 API 키(agent/.env) 설정을 확인해 주세요.'
      default:
        return e.message || '요청에 실패했습니다.'
    }
  }
  if (e instanceof Error) return e.message
  return '알 수 없는 오류가 발생했습니다.'
}
