/** docs/api-contract.md 그대로 호출하는 실제 구현 */
import { ApiError, request } from './client'
import type { RegionKey } from '@/config'
import type { ApiClient } from './types'
import type {
  DemandSignal,
  FieldCheck,
  FieldCheckCreate,
  FieldFeedbackSummary,
  LoginResponse,
  QuestionRequest,
  SupportRequest,
  SupportRequestCreate,
  SupportRequestStatus,
  User,
} from '@/types/api'
import type { Display } from '@/types/display'
import type { FacilityCollection, GridCollection } from '@/types/geo'

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

  getFacilitiesMap: (region: RegionKey) =>
    request<FacilityCollection>('/api/v1/maps/facilities', { query: { region } }),

  getAdminTypesMap: (region: RegionKey, showExcluded = false) =>
    request<GridCollection>('/api/v1/admin/maps/types', { query: { region, show_excluded: showExcluded } }),

  getAdminCandidatesMap: (region: RegionKey) =>
    request<GridCollection>('/api/v1/admin/maps/candidates', { query: { region } }),

  getAdminPlacementsMap: (region: RegionKey, radiusM: 1000 | 3000, sites: 3) =>
    request<GridCollection>('/api/v1/admin/maps/placements', { query: { region, radius_m: radiusM, sites } }),

  getDemandSignals: () => request<DemandSignal[]>('/api/v1/admin/demand-signals'),

  getFieldFeedbackSummary: () => request<FieldFeedbackSummary[]>('/api/v1/admin/field-feedback-summary'),

  publishFieldCheckList: async () => {
    throw new ApiError(501, 'integration_pending', '현장 확인 목록 전달 API가 백엔드에 아직 없습니다.')
  },

  fetchFieldCheckList: async () => {
    throw new ApiError(501, 'integration_pending', '현장 확인 목록 조회 API가 백엔드에 아직 없습니다.')
  },
}
