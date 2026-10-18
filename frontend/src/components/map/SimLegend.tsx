import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { SIM_COLOR } from '@/map/colors'

export type SimRadius = 1000 | 3000

export interface SimLegendProps {
  radius: SimRadius
  onRadiusChange: (r: SimRadius) => void
  covered?: number
  total?: number
  /** 범례 제목 (기본: 엔진 기본 배치 '이동형 거점 3곳') */
  title?: string
  /** 개입안 비교 답변: 안별 점 색과 거점 수 */
  options?: { label: string; color: string; count: number }[]
  /** 범례 맨 아래 안내 */
  note?: string
}

/** 배치 지도 범례 + 반경 전환 + 커버 집계(전후 비교) */
export function SimLegend({ radius, onRadiusChange, covered, total, title = '이동형 거점 3곳', options, note }: SimLegendProps) {
  const hasStats = covered !== undefined && total !== undefined && total > 0
  const pct = hasStats ? Math.round((covered / total) * 100) : 0
  return (
    <div className="space-y-2 rounded-btn border border-line bg-surface/95 p-2 text-xs shadow-card backdrop-blur" aria-label="배치 지도 범례">
      <div className="flex items-center justify-between gap-2">
        <p className="font-semibold text-ink">{title}</p>
        <SegmentedControl size="sm" aria-label="거점 반경" value={String(radius) as '1000' | '3000'} onChange={(v) => onRadiusChange(Number(v) as SimRadius)} options={[{ value: '1000', label: '1km' }, { value: '3000', label: '3km' }]} />
      </div>
      <ul className="space-y-0.5">
        <li className="flex items-center gap-2">
          <span className="inline-block size-3 shrink-0 rounded-sm" style={{ background: SIM_COLOR.covered }} aria-hidden />
          <span className="flex-1 text-ink-2">거점이 닿는 동네</span>
          {hasStats && <span className="tabular-nums text-ink-3">{covered}</span>}
        </li>
        <li className="flex items-center gap-2">
          <span className="inline-block size-3 shrink-0 rounded-sm" style={{ background: SIM_COLOR.gap }} aria-hidden />
          <span className="flex-1 text-ink-2">아직 닿지 않는 동네 (공백)</span>
          {hasStats && <span className="tabular-nums text-ink-3">{total - covered}</span>}
        </li>
      </ul>
      {hasStats && (
        <div className="border-t border-line pt-2">
          <p className="mb-1 text-ink-2">
            배치 전 공백 <span className="tabular-nums">{total}곳</span> → 후 <b className="tabular-nums text-ink">{total - covered}곳</b> <span className="text-ink-3">({pct}% 해소)</span>
          </p>
          <div className="flex h-2 overflow-hidden rounded-full bg-[#c05621]/30">
            <div className="h-full rounded-full" style={{ width: `${pct}%`, background: SIM_COLOR.covered }} aria-hidden />
          </div>
        </div>
      )}
      {options && options.length > 0 && (
        <ul className="space-y-0.5 border-t border-line pt-2">
          {options.map((o) => (
            <li key={o.label} className="flex items-center gap-2">
              <span className="inline-block size-3 shrink-0 rounded-full" style={{ background: o.color }} aria-hidden />
              <span className="flex-1 text-ink-2">{o.label}</span>
              <span className="tabular-nums text-ink-3">{o.count}곳</span>
            </li>
          ))}
        </ul>
      )}
      {note && <p className="text-ink-3">{note}</p>}
    </div>
  )
}
