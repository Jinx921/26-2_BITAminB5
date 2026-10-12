import type { Display } from '@/types/display'
import { FragmentBoundary } from './FragmentBoundary'
import { resolveFragment } from './registry'
import { toFragments } from './toFragments'
import type { FragmentContext, Mode } from './types'

export interface FragmentRendererProps {
  display: Display | null | undefined
  mode: Mode
  context: FragmentContext
  className?: string
}

/** display 를 조각 배열로 바꿔 등록된 컴포넌트로 순서대로 그린다 */
export function FragmentRenderer({ display, mode, context, className = 'space-y-4' }: FragmentRendererProps) {
  const fragments = toFragments(display, mode)
  if (fragments.length === 0) return null
  return (
    <div className={className}>
      {fragments.map((f) => {
        const Comp = resolveFragment(f.type)
        if (!Comp) return null
        return (
          <FragmentBoundary key={f.key} name={f.key}>
            <Comp fragment={f} mode={mode} context={context} />
          </FragmentBoundary>
        )
      })}
    </div>
  )
}
