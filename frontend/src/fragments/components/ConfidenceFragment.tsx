import type { Confidence } from '@/types/display'
import type { FragmentProps } from '../types'

/** 신뢰도 등급. 상태색은 라벨 글자와 함께 쓴다 (색만으로 뜻을 전하지 않음) */
const STYLE: Record<string, string> = {
  높음: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  보통: 'bg-amber-50 text-amber-800 border-amber-200',
  낮음: 'bg-red-50 text-red-800 border-red-200',
}

export function ConfidenceFragment({ fragment, mode }: FragmentProps<Confidence>) {
  if (mode !== 'admin') return null // 시민 화면에는 신뢰도를 보여주지 않는다
  const { label, note } = fragment.data
  return (
    <div className={`flex flex-wrap items-center gap-2 rounded-xl border px-3 py-2 ${STYLE[label] ?? 'bg-slate-50 text-slate-800 border-slate-200'}`} data-fragment="confidence">
      <span className="text-sm font-semibold">신뢰도 {label}</span>
      {note && <span className="text-sm">· {note}</span>}
    </div>
  )
}
