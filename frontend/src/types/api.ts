/** docs/api-contract.md 의 요청·응답 형식. 백엔드와 1:1 로 맞춘다. */
import type { ChecksPoint } from './display'

export type Role = 'citizen' | 'admin' | 'field_worker'

export interface User {
  id: number
  email: string
  role: Role
  created_at?: string
}

export interface LoginResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}

/** 공통 오류 응답 */
export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown }
  request_id?: string
}

export interface QuestionLocation {
  lat: number
  lon: number
}

export interface QuestionRequest {
  /** 호환용으로 남아 있고 실제 모드는 로그인 계정 역할로 정해진다 */
  mode: 'citizen' | 'admin'
  question: string
  /** 시민만 보낼 수 있다. 관리자가 보내면 422 */
  location?: QuestionLocation
}

export type SupportRequestType = 'companion' | 'mobility'
export type SupportRequestStatus = 'pending' | 'approved' | 'rejected' | 'completed'

export interface SupportRequestCreate {
  facility_id: string
  requester_name: string
  contact?: string | null
  contact_consent: boolean
  requested_at: string
  request_type: SupportRequestType
  note?: string
}

export interface SupportRequest extends SupportRequestCreate {
  id: number
  status: SupportRequestStatus
  created_at: string
}

/** engine/현장기록_규격.md 의 고정 키. 묻지 않은 항목은 unknown 으로 보낸다 */
export type ChecklistAnswer = 'yes' | 'no' | 'unknown'
export type SupportNeededAnswer = 'needed' | 'not_needed' | 'unsure'

export interface FieldChecklist {
  has_residents: ChecklistAnswer
  social_hard_to_reach: ChecklistAnswer
  health_hard_to_reach: ChecklistAnswer
  seniors_out_daytime: ChecklistAnswer
  support_needed: SupportNeededAnswer
}

export interface FieldCheckCreate {
  cell_id: string
  checklist: FieldChecklist
  checked_at: string
  note?: string
}

export interface FieldCheck extends FieldCheckCreate {
  id: number
  created_at: string
}

export interface DemandSignal {
  facility_id: string
  request_type: SupportRequestType
  status: SupportRequestStatus
  count: number
}

/** 실제 백엔드 응답 키는 checklist_responses (계약서 본문에는 키 이름이 없어 실측으로 맞춤) */
export interface FieldFeedbackSummary {
  cell_id: string
  checked_count: number
  checklist_responses: { item_index: number; response_count: number }[]
}

/**
 * 관리자가 현장 담당자에게 보내는 확인 목록.
 * 백엔드 API 가 아직 없어 목업에서는 공유 저장소, 실제 모드에서는 복사·내려받기로 전달한다.
 */
export interface FieldCheckList {
  region: string | null
  headline: string
  created_at: string
  cells: ChecksPoint[]
}
