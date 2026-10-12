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

  // 관리자 집계
  getDemandSignals(): Promise<DemandSignal[]>
  getFieldFeedbackSummary(): Promise<FieldFeedbackSummary[]>

  /**
   * 현장 확인 목록 전달. 백엔드 엔드포인트가 아직 없다.
   * 목업: 브라우저 공유 저장소에 저장. 실제: 저장하지 않고 null 을 돌려주며 화면은 복사·내려받기로 대체한다.
   * 엔드포인트가 생기면 이 두 함수만 바꾼다.
   */
  publishFieldCheckList(list: FieldCheckList): Promise<{ stored: boolean }>
  fetchFieldCheckList(): Promise<FieldCheckList | null>
}
