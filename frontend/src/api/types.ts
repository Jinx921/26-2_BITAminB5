/** 실제 API 와 목업이 똑같이 구현하는 인터페이스. 화면은 이 인터페이스만 본다. */
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
import type { RegionKey } from '@/config'
import type { FacilityCollection, GridCollection } from '@/types/geo'

export interface ApiClient {
  health(): Promise<{ status: string }>

  // 인증
  register(email: string, password: string): Promise<User>
  login(email: string, password: string): Promise<LoginResponse>

  // 질문 (display 만 돌아온다)
  askQuestion(req: QuestionRequest, signal?: AbortSignal): Promise<Display>

  // 지원 요청 (함께 가기 / 이동 도움)
  createSupportRequest(body: SupportRequestCreate): Promise<SupportRequest>
  listSupportRequests(status?: SupportRequestStatus): Promise<SupportRequest[]>
  getSupportRequest(id: number): Promise<SupportRequest>
  updateSupportRequestStatus(id: number, status: SupportRequestStatus): Promise<SupportRequest>

  // 현장 확인
  createFieldCheck(body: FieldCheckCreate): Promise<FieldCheck>
  listFieldChecks(cellId: string): Promise<FieldCheck[]>
  saveFieldCheckList(list: FieldCheckList): Promise<FieldCheckList>

  // 지도: 시설은 citizen/admin, 유형·후보·배치는 admin 전용
  getFacilitiesMap(region: RegionKey): Promise<FacilityCollection>
  getAdminTypesMap(region: RegionKey, showExcluded?: boolean): Promise<GridCollection>
  getAdminCandidatesMap(region: RegionKey): Promise<GridCollection>
  getAdminPlacementsMap(region: RegionKey, radiusM: 1000 | 3000, sites: 3): Promise<GridCollection>

  // 관리자 집계
  getDemandSignals(): Promise<DemandSignal[]>
  getFieldFeedbackSummary(): Promise<FieldFeedbackSummary[]>

  /** 관리자 목업 화면에서 목록을 공유한다. 실제 모드에서는 아직 제공하지 않는다. */
  publishFieldCheckList(list: FieldCheckList): Promise<{ stored: boolean }>
  fetchFieldCheckList(): Promise<FieldCheckList | null>
}
