import type { FacilitiesPoint } from '@/types/display'

/** 직선거리 기준 걸음 시간 (분). 80m/분 */
export function walkMinutes(m: number | null | undefined): number | null {
  if (m === null || m === undefined || !Number.isFinite(m)) return null
  return Math.max(1, Math.round(m / 80))
}

export function placeDescription(p: FacilitiesPoint): string {
  return p.highlight ? `${p.kind} · 답변에서 추천한 곳` : p.kind
}

