import type { FragmentProps } from '../types'

export function HeadlineFragment({ fragment, mode }: FragmentProps<string>) {
  return (
    <p className={`font-bold leading-snug text-slate-900 ${mode === 'citizen' ? 'text-2xl' : 'text-xl'}`} data-fragment="headline">
      {fragment.data}
    </p>
  )
}
