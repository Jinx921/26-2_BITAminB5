import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { DayChip } from '@/components/ui/DayChip'
import { DAY_LABEL, formatWhen, useSchedule } from '@/features/citizen/schedule'

const WEEKDAYS = [1, 2, 3, 4, 5] // 월~금

function badgeFor(kind: string): { text: string; tone: 'green' | 'orange' | 'blue' } {
  if (kind === '보건') return { text: '상담', tone: 'green' }
  if (kind === '경로당') return { text: '모임', tone: 'orange' }
  return { text: '방문', tone: 'blue' }
}

/** 이번 주 월~금 5칸. 일정 있는 날만 색 글씨, 선택한 날은 옅은 초록 배경 + 그 날 일정 한 줄 */
export function WeekStrip() {
  const { items } = useSchedule()
  const [now] = useState(() => new Date())
  const monday = useMemo(() => {
    const d = new Date(now)
    d.setHours(0, 0, 0, 0)
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7))
    return d
  }, [now])
  const byDay = useMemo(() => {
    const m = new Map<number, typeof items>()
    for (const it of items) {
      const d = new Date(it.when)
      const diff = Math.floor((d.getTime() - monday.getTime()) / 86400000)
      if (diff >= 0 && diff < 7) m.set(d.getDay(), [...(m.get(d.getDay()) ?? []), it])
    }
    return m
  }, [items, monday])
  const [active, setActive] = useState<number>(() => {
    const today = now.getDay()
    return WEEKDAYS.includes(today) ? today : 1
  })
  const todays = byDay.get(active) ?? []

  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-lg font-bold text-ink">이번 주 일정</h2>
        <Link to="/citizen/schedule" className="text-sm font-semibold text-primary">
          모두 보기
        </Link>
      </div>
      <div className="grid grid-cols-5 gap-2">
        {WEEKDAYS.map((d) => {
          const first = byDay.get(d)?.[0]
          const b = first ? badgeFor(first.kind) : null
          return <DayChip key={d} label={DAY_LABEL[d]} badge={b?.text} tone={b?.tone} active={active === d} onClick={() => setActive(d)} />
        })}
      </div>
      {todays.length > 0 ? (
        <ul className="mt-2 space-y-1 text-sm text-ink-2">
          {todays.map((t) => (
            <li key={t.id}>
              {formatWhen(t.when).replace(/^.*\) /, '')} · {t.name}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-ink-3">{DAY_LABEL[active]}요일에는 잡힌 일정이 없어요. 장소 카드에서 일정을 저장할 수 있어요.</p>
      )}
    </section>
  )
}
