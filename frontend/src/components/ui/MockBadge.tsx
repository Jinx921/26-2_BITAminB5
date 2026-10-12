import { isMockMode } from '@/api'

/** 목업 모드임을 화면 구석에 표시한다. 실제 모드에서는 아무것도 그리지 않는다 */
export function MockBadge() {
  if (!isMockMode) return null
  return (
    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800" title="VITE_USE_MOCK=true">
      목업
    </span>
  )
}
