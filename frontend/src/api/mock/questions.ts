/**
 * 질문 목업. 2단계에서 agent/out/examples 의 화면조각 display 를 fixtures 로 넣고 키워드 매칭한다.
 * 지금은 형식만 맞춘 기본 응답을 돌려준다.
 */
import type { QuestionRequest } from '@/types/api'
import type { Display } from '@/types/display'

export const EMPTY_DISPLAY: Display = {
  headline: '',
  details: [],
  caution: '',
  confidence: null,
  map: null,
  chart: null,
  document: null,
}

export function mockAnswer(req: QuestionRequest, role: 'admin' | 'citizen'): Display {
  if (role === 'citizen' && !req.location) {
    return {
      ...EMPTY_DISPLAY,
      headline:
        '어느 동네 주변을 찾아볼까요? 지도에서 동네를 고르거나 주소를 입력해 주세요. 지금 계신 곳 주변을 찾으려면 위치 사용을 허용해 주세요.',
    }
  }
  return {
    ...EMPTY_DISPLAY,
    headline: role === 'admin' ? '목업 응답입니다. 2단계에서 예시 데이터로 교체됩니다.' : '목업 응답이에요. 곧 실제 예시로 바뀌어요.',
    details: [`질문: ${req.question}`],
    confidence: role === 'admin' ? { label: '보통', note: '목업' } : null,
  }
}
