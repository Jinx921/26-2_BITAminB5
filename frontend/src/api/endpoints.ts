/** docs/api-contract.md 그대로 호출하는 실제 구현 */
import { request } from './client'
import type { ApiClient } from './types'
import type {
  DemandSignal,
  FieldCheck,
  FieldCheckCreate,
  FieldCheckList,
  FieldFeedbackSummary,
  LoginResponse,
  QuestionRequest,
  SupportRequest,
  SupportRequestCreate,
  SupportRequestStatus,
  User,
} from '@/types/api'
import type { Display } from '@/types/display'

const FIELD_LIST_KEY = 'bitamin.fieldCheckList.local'

export const realApi: ApiClient = {
  health: () => request<{ status: string }>('/health', { auth: false }),

  register: (email, password) =>
    request<User>('/api/v1/auth/register', { method: 'POST', body: { email, password }, auth: false }),

  login: (email, password) =>
    request<LoginResponse>('/api/v1/auth/login', { method: 'POST', body: { email, password }, auth: false }),

  askQuestion: (req: QuestionRequest, signal) =>
    request<Display>('/api/v1/questions', { method: 'POST', body: req, signal }),

  createSupportRequest: (body: SupportRequestCreate) =>
    request<SupportRequest>('/api/v1/support-requests', { method: 'POST', body }),

  listSupportRequests: (status?: SupportRequestStatus) =>
    request<SupportRequest[]>('/api/v1/support-requests', { query: { status } }),

  getSupportRequest: (id) => request<SupportRequest>(`/api/v1/support-requests/${id}`),

  updateSupportRequestStatus: (id, status) =>
    request<SupportRequest>(`/api/v1/support-requests/${id}/status`, { method: 'PATCH', body: { status } }),

  createFieldCheck: (body: FieldCheckCreate) =>
    request<FieldCheck>('/api/v1/field-checks', { method: 'POST', body }),

  listFieldChecks: (cellId) => request<FieldCheck[]>('/api/v1/field-checks', { query: { cell_id: cellId } }),

  getDemandSignals: () => request<DemandSignal[]>('/api/v1/admin/demand-signals'),

  getFieldFeedbackSummary: () => request<FieldFeedbackSummary[]>('/api/v1/admin/field-feedback-summary'),

  // TODO(backend): 현장 확인 목록 전달 API 가 생기면 아래 두 함수를 request() 로 바꾼다.
  // 지금은 같은 브라우저 안에서만 보이도록 localStorage 에 두고, 화면은 복사·내려받기를 기본으로 안내한다.
  publishFieldCheckList: async (list: FieldCheckList) => {
    try {
      localStorage.setItem(FIELD_LIST_KEY, JSON.stringify(list))
    } catch {
      /* ignore */
    }
    return { stored: false }
  },
  fetchFieldCheckList: async () => {
    try {
      const raw = localStorage.getItem(FIELD_LIST_KEY)
      return raw ? (JSON.parse(raw) as FieldCheckList) : null
    } catch {
      return null
    }
  },
}
