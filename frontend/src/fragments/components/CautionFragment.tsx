import type { FragmentProps } from '../types'

export function CautionFragment({ fragment, mode }: FragmentProps<string>) {
  const big = mode === 'citizen'
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900" data-fragment="caution">
      <p className="mb-1 text-sm font-semibold uppercase tracking-wide">{big ? '알아두세요' : '확인할 점'}</p>
      <p className={big ? 'text-lg leading-relaxed' : 'leading-relaxed'}>{fragment.data}</p>
    </div>
  )
}
