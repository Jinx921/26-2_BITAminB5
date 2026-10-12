import type { FragmentProps } from '../types'

/** 계약서에 없는 조각. 화면을 깨뜨리지 않고 내용을 접어 보여준다 (관리자만) */
export function UnknownFragment({ fragment, mode }: FragmentProps) {
  if (mode !== 'admin') return null
  return (
    <details className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-3 text-sm text-slate-600" data-fragment="unknown">
      <summary className="cursor-pointer">표시 방법이 정해지지 않은 항목: {fragment.key}</summary>
      <pre className="mt-2 overflow-x-auto text-xs">{JSON.stringify(fragment.data, null, 2)}</pre>
    </details>
  )
}
