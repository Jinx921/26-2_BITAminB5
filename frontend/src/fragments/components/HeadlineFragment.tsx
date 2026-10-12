import type { FragmentProps } from '../types'

export function HeadlineFragment({ fragment, mode }: FragmentProps<string>) {
  return (
    <p className={`font-bold leading-snug text-ink ${mode === 'citizen' ? 'text-xl' : 'text-lg'}`} data-fragment="headline">
      {fragment.data}
    </p>
  )
}
