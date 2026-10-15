import { TYPE_COLOR, TYPE_DESCRIPTION, TYPE_ORDER } from '@/map/colors'
import type { IsolationType } from '@/types/display'

export interface TypeLegendProps {
  counts?: Partial<Record<IsolationType, number>>
  visible: ReadonlySet<IsolationType>
  onToggle: (t: IsolationType) => void
}

/** 지도 구석의 작은 범례 겸 필터 */
export function TypeLegend({ counts, visible, onToggle }: TypeLegendProps) {
  return (
    <ul className="space-y-0.5 rounded-btn border border-line bg-surface/95 p-2 text-xs shadow-card backdrop-blur" aria-label="동네 유형 범례">
      {TYPE_ORDER.map((t) => {
        const on = visible.has(t)
        return (
          <li key={t}>
            <button type="button" aria-pressed={on} onClick={() => onToggle(t)} title={TYPE_DESCRIPTION[t]} className={`flex w-full items-center gap-2 rounded px-1 py-1 text-left hover:bg-canvas ${on ? 'text-ink' : 'text-ink-3 line-through'}`}>
              <span className="inline-block size-3 shrink-0 rounded-sm" style={{ background: TYPE_COLOR[t], opacity: on ? 1 : 0.35 }} aria-hidden />
              <span className="flex-1">{t}</span>
              {counts?.[t] !== undefined && <span className="tabular-nums text-ink-3">{counts[t]}</span>}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
