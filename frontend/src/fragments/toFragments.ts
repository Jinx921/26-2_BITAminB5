import type { Display, Fragment, FragmentType } from '@/types/display'
import type { Mode } from './types'

/**
 * display 객체 → 조각 배열. 모드별로 보여줄 키와 순서가 다르다.
 * 시민 모드는 confidence·chart 를 절대 그리지 않는다 (낙인 방지, agent/README 7절).
 * 계약서에 없는 키는 관리자 화면에서만 unknown 조각으로 대체 표시하고, 시민 화면에서는 건너뛴다.
 */
export const FRAGMENT_ORDER: Record<Mode, FragmentType[]> = {
  admin: ['headline', 'confidence', 'map', 'chart', 'details', 'caution', 'document'],
  citizen: ['headline', 'map', 'details', 'caution'],
}

const KNOWN_KEYS = new Set<string>(['headline', 'details', 'caution', 'confidence', 'map', 'chart', 'document'])

function isEmpty(v: unknown): boolean {
  if (v === null || v === undefined) return true
  if (typeof v === 'string') return v.trim() === ''
  if (Array.isArray(v)) return v.length === 0
  return false
}

export function toFragments(display: Display | null | undefined, mode: Mode): Fragment[] {
  if (!display || typeof display !== 'object') return []
  const record = display as unknown as Record<string, unknown>
  const out: Fragment[] = []

  for (const type of FRAGMENT_ORDER[mode]) {
    const data = record[type]
    if (isEmpty(data)) continue
    out.push({ type, key: type, data })
  }

  if (mode === 'admin') {
    for (const key of Object.keys(record)) {
      if (KNOWN_KEYS.has(key) || isEmpty(record[key])) continue
      out.push({ type: 'unknown', key, data: record[key] })
    }
  }
  return out
}
