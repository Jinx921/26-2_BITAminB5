/**
 * 현장 확인 항목. 키와 값은 engine/현장기록_규격.md 3절을 따른다 (문구가 바뀌어도 키는 유지).
 * 에이전트 질문 문구 → 키 매칭은 핵심 단어로 한다.
 */
import type { ChecklistAnswer, FieldChecklist, SupportNeededAnswer } from '@/types/api'

export type ChecklistKey = Exclude<keyof FieldChecklist, 'support_needed'>

export const CHECKLIST_ITEMS: { key: ChecklistKey; label: string; match: string[] }[] = [
  { key: 'has_residents', label: '실제로 사람이 사는 집이 있나요?', match: ['사는 집', '사람이 사', '거주'] },
  { key: 'social_hard_to_reach', label: '가까운 경로당·마을회관까지 실제로 걸어가기 어려운가요?', match: ['경로당', '마을회관', '걸어가'] },
  { key: 'health_hard_to_reach', label: '보건소·보건진료소까지 실제로 가기 어려운가요?', match: ['보건'] },
  { key: 'seniors_out_daytime', label: '낮에 어르신이 밖에 나오시나요?', match: ['낮에', '밖에 나오'] },
]

export const SUPPORT_NEEDED_LABEL = '(종합) 이 동네에 지원이 필요해 보이나요?'

export const ANSWER_OPTIONS: { value: ChecklistAnswer; label: string }[] = [
  { value: 'yes', label: '예' },
  { value: 'no', label: '아니오' },
  { value: 'unknown', label: '모름' },
]
export const SUPPORT_OPTIONS: { value: SupportNeededAnswer; label: string }[] = [
  { value: 'needed', label: '필요해 보임' },
  { value: 'not_needed', label: '필요 없어 보임' },
  { value: 'unsure', label: '판단 어려움' },
]

/** 에이전트 질문 문구 → 저장 키. 못 찾으면 null (메모로만 남긴다) */
export function keyForQuestion(question: string): ChecklistKey | null {
  for (const item of CHECKLIST_ITEMS) if (item.match.some((m) => question.includes(m))) return item.key
  return null
}

/** 묻지 않은 항목은 unknown 으로 채운 완전한 checklist */
export function buildChecklist(answers: Partial<Record<ChecklistKey, ChecklistAnswer>>, support: SupportNeededAnswer): FieldChecklist {
  return {
    has_residents: answers.has_residents ?? 'unknown',
    social_hard_to_reach: answers.social_hard_to_reach ?? 'unknown',
    health_hard_to_reach: answers.health_hard_to_reach ?? 'unknown',
    seniors_out_daytime: answers.seniors_out_daytime ?? 'unknown',
    support_needed: support,
  }
}

export const ANSWER_LABEL: Record<string, string> = {
  yes: '예',
  no: '아니오',
  unknown: '모름',
  needed: '필요해 보임',
  not_needed: '필요 없어 보임',
  unsure: '판단 어려움',
}
