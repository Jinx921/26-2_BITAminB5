import { TYPE_COLOR, TYPE_DESCRIPTION, TYPE_ORDER } from '@/map/colors'
import type { IsolationType } from '@/types/display'

export interface TypeLegendProps {
  counts?: Partial<Record<IsolationType, number>>
  visible: ReadonlySet<IsolationType>
  onToggle: (t: IsolationType) => void
}

/** 유형 범례 겸 필터. 색과 이름을 함께 쓴다 */
export function TypeLegend({ counts, visible, onToggle }: TypeLegendProps) {
  return (
    <ul className="flex flex-wrap gap-2" aria-label="동네 유형 범례">
      {TYPE_ORDER.map((t) => {
        const on = visible.has(t)
        return (
          <li key={t}>
            <button
              type="button"
              aria-pressed={on}
              onClick={() => onToggle(t)}
              title={TYPE_DESCRIPTION[t]}
              className={`flex items-center gap-2 rounded-full border px-3 py-1 text-sm ${on ? 'border-slate-300 bg-white text-slate-800' : 'border-slate-200 bg-slate-100 text-slate-400 line-through'}`}
            >
              <span className="inline-block size-3 rounded-sm" style={{ background: TYPE_COLOR[t], opacity: on ? 1 : 0.4 }} aria-hidden />
              {t}
              {counts?.[t] !== undefined && <span className="tabular-nums text-slate-500">{counts[t]}</span>}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
