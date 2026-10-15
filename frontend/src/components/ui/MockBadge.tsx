import { isMockMode } from '@/api'

/** 목업 모드 표시. 개발 모드에서만 보인다 */
export function MockBadge() {
  if (!isMockMode || !import.meta.env.DEV) return null
  return (
    <span className="rounded-full bg-orange-soft px-2 py-0.5 text-[11px] font-semibold text-orange" title="VITE_USE_MOCK=true">
      목업
    </span>
  )
}
