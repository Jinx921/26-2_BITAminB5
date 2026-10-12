/**
 * 질문 목업. agent/out/examples 의 화면조각(display)을 fixtures 로 두고 질문 키워드와 지역으로 고른다.
 * 실제 API 와 같은 display 형식이라 스위치만 바꾸면 그대로 동작한다.
 */
import { REGION_KEYS, regionOf, type RegionKey } from '@/config'
import type { QuestionRequest } from '@/types/api'
import type { Display } from '@/types/display'

interface Fixture {
  id: string
  mode: 'admin' | 'citizen'
  question: string | null
  region: string | null
  display: Display
}

const modules = import.meta.glob<{ default: Fixture }>('./fixtures/*_*.json', { eager: true })
const FIXTURES = new Map<string, Fixture>()
for (const m of Object.values(modules)) {
  const f = m.default
  if (f && f.id && f.display) FIXTURES.set(f.id, f)
}

export const EMPTY_DISPLAY: Display = {
  headline: '',
  details: [],
  caution: '',
  confidence: null,
  map: null,
  chart: null,
  document: null,
}

function pick(id: string): Display {
  const f = FIXTURES.get(id)
  if (f) return structuredClone(f.display)
  return { ...EMPTY_DISPLAY, headline: `목업 예시(${id})를 찾지 못했습니다.` }
}

function has(q: string, ...words: string[]): boolean {
  return words.some((w) => q.includes(w))
}

const OTHER_CITIES = ['부산', '대구', '인천', '광주', '대전', '울산', '세종', '수원', '원주', '강릉', '제주']

function regionInText(q: string): RegionKey | 'other' | null {
  for (const r of REGION_KEYS) if (q.includes(r)) return r
  if (OTHER_CITIES.some((c) => q.includes(c))) return 'other'
  return null
}

export function mockAdminAnswer(q: string): Display {
  const region = regionInText(q)
  if (region === 'other') return pick('admin_14_서비스지역밖')
  const r: RegionKey = region ?? '춘천'

  if (has(q, '현장 확인', '확인 목록', '체크리스트')) return pick('admin_06_현장확인목록')
  if (has(q, '믿어도', '신뢰', '확실')) return pick('admin_05_믿어도돼')
  if (has(q, '제안서')) return pick('admin_09_제안서')
  if (has(q, '현황', '보고서')) return pick('admin_10_현황보고')
  if (has(q, '안내문', '알리는')) return pick('admin_11_주민안내문')
  if (has(q, '비교', '뭐가 나아', '어떤 방식', '중 뭐') || (has(q, '이동형') && has(q, '경로당')))
    return pick(r === '강남' ? 'admin_08_개입안비교_강남' : 'admin_07_개입안비교_춘천')
  if (has(q, '문을 닫', '폐쇄', '없어지', '사라지')) return pick('admin_04_경로당폐쇄')
  if (has(q, '이동형', '배치', '거점', '어디가 좋')) return pick('admin_03_이동형배치')
  if (has(q, '어디부터', '우선', '먼저', '어디서', '어디를')) return pick(r === '강남' ? 'admin_02_어디부터_강남' : 'admin_01_어디부터_춘천')
  if (q.trim().length <= 6 && has(q, '안녕', '하이', '반가')) return pick('admin_12_인사')
  if (region) return pick(r === '강남' ? 'admin_02_어디부터_강남' : 'admin_01_어디부터_춘천')
  return pick('admin_13_관계없는질문')
}

export function mockCitizenAnswer(req: QuestionRequest): Display {
  if (!req.location) return pick('citizen_03_위치없음')
  const region = regionOf(req.location.lat, req.location.lon)
  if (!region) return pick('citizen_04_서비스지역밖')
  if (has(req.question, '시간표', '프로그램', '몇 시', '언제 열')) return pick('citizen_05_데이터없는질문')
  return pick(region === '강남' ? 'citizen_02_강남' : 'citizen_01_춘천')
}

export function mockAnswer(req: QuestionRequest, role: 'admin' | 'citizen'): Display {
  return role === 'admin' ? mockAdminAnswer(req.question) : mockCitizenAnswer(req)
}

/** 화면에 보여줄 예시 질문 (목업·실제 공통으로 쓸 수 있는 문장) */
export const SAMPLE_QUESTIONS = {
  admin: [...FIXTURES.values()].filter((f) => f.mode === 'admin' && f.question && !f.id.match(/1[234]_/)).map((f) => f.question!),
  citizen: [...FIXTURES.values()].filter((f) => f.mode === 'citizen' && f.question && f.region).map((f) => f.question!),
}
