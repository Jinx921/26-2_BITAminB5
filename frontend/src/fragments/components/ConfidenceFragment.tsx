import type { Confidence } from '@/types/display'
import type { FragmentProps } from '../types'

const STYLE: Record<string, string> = {
  높음: 'bg-green-soft text-green',
  보통: 'bg-amber-50 text-amber-ink',
  낮음: 'bg-red-50 text-danger',
}

/** 신뢰도: 작은 배지 + 한 줄 설명. 관리자만 */
export function ConfidenceFragment({ fragment, mode }: FragmentProps<Confidence>) {
  if (mode !== 'admin') return null
  const { label, note } = fragment.data
  return (
    <p className="flex flex-wrap items-center gap-2 text-sm text-ink-3" data-fragment="confidence">
      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STYLE[label] ?? 'bg-canvas text-ink-2'}`}>신뢰도 {label}</span>
      {note && <span>{note}</span>}
    </p>
  )
}
