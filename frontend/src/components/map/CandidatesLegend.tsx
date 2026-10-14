import { MONTHS_COLOR, MONTHS_ORDER } from '@/map/colors'

/** 후보 지도 범례: 지속 개월(색 진하기)과 거주 상태(테두리) */
export function CandidatesLegend({ counts, total }: { counts?: Partial<Record<number, number>>; total?: number }) {
  return (
    <div className="space-y-1.5 rounded-btn border border-line bg-surface/95 p-2 text-xs shadow-card backdrop-blur" aria-label="후보 지도 범례">
      <p className="font-semibold text-ink">
        낮 활동이 줄어든 동네{total !== undefined && <span className="ml-1 font-normal text-ink-3">{total}곳</span>}
      </p>
      <ul className="space-y-0.5">
        {MONTHS_ORDER.map((m) => (
          <li key={m} className="flex items-center gap-2">
            <span className="inline-block size-3 shrink-0 rounded-sm" style={{ background: MONTHS_COLOR[m] }} aria-hidden />
            <span className="flex-1 text-ink-2">6개월 중 {m}개월 감소</span>
            {counts?.[m] !== undefined && <span className="tabular-nums text-ink-3">{counts[m]}</span>}
          </li>
        ))}
      </ul>
      <ul className="space-y-0.5 border-t border-line pt-1.5">
        <li className="flex items-center gap-2">
          <span className="inline-block size-3 shrink-0 rounded-sm border border-[#f97316] bg-[#fdba74]/60" aria-hidden />
          <span className="text-ink-2">주거 (실선)</span>
        </li>
        <li className="flex items-center gap-2">
          <span className="inline-block size-3 shrink-0 rounded-sm border border-dashed border-[#7c2d12] bg-[#fdba74]/60" aria-hidden />
          <span className="text-ink-2">용도미상 (점선)</span>
        </li>
      </ul>
    </div>
  )
}
