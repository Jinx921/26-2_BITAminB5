import type { FragmentProps } from '../types'

/** 계약서에 없는 조각. 관리자에게만 접어서 보여준다 */
export function UnknownFragment({ fragment, mode }: FragmentProps) {
  if (mode !== 'admin') return null
  return (
    <details className="text-sm text-ink-3" data-fragment="unknown">
      <summary className="cursor-pointer">표시 방법이 정해지지 않은 항목: {fragment.key}</summary>
      <pre className="mt-2 overflow-x-auto rounded-btn bg-canvas p-2 text-xs">{JSON.stringify(fragment.data, null, 2)}</pre>
    </details>
  )
}
