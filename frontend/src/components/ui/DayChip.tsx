export interface DayChipProps {
  label: string
  /** 그 날 일정 요약 (없으면 빈 칸) */
  badge?: string
  tone?: 'green' | 'orange' | 'blue'
  active?: boolean
  onClick?: () => void
}

const TONE = { green: 'text-green', orange: 'text-orange', blue: 'text-primary' }

/** 이번 주 요일 칸. 일정 있는 날만 색 글씨, 선택된 날은 옅은 초록 배경 */
export function DayChip({ label, badge, tone = 'green', active, onClick }: DayChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`flex min-h-[4.5rem] flex-col items-center justify-center gap-1 rounded-btn border px-1 py-2 ${active ? 'border-green bg-green-soft' : 'border-line bg-surface'}`}
    >
      <span className="text-base font-semibold text-ink">{label}</span>
      <span className={`min-h-5 text-sm font-semibold ${badge ? TONE[tone] : 'text-transparent'}`}>{badge || '·'}</span>
    </button>
  )
}
