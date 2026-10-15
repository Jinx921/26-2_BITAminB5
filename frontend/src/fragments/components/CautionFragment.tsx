import { Info } from 'lucide-react'
import type { FragmentProps } from '../types'

/** 주의 문구. 박스 없이 아이콘과 옅은 글씨로 */
export function CautionFragment({ fragment, mode }: FragmentProps<string>) {
  return (
    <p className={`flex items-start gap-2 text-amber-ink ${mode === 'citizen' ? 'text-sm' : 'text-[13px]'} leading-relaxed`} data-fragment="caution">
      <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
      <span>{fragment.data}</span>
    </p>
  )
}
