import { useState } from 'react'
import { Link } from 'react-router-dom'
import { A11yBar } from '@/components/citizen/A11yBar'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { downloadIcs, formatWhen, isThisWeek, useSchedule } from '@/features/citizen/schedule'
import { directionsUrl } from '@/features/citizen/share'
import { FACILITY_KIND_ICON } from '@/map/colors'

/** 이번 주 일정 (기기에만 저장). 캘린더(.ics)로 내보낼 수 있다 */
export function CitizenSchedulePage() {
  const { items, remove } = useSchedule()
  const [now] = useState(() => new Date())
  const thisWeek = items.filter((i) => isThisWeek(i.when, now))
  const later = items.filter((i) => !isThisWeek(i.when, now) && new Date(i.when) > now)
  const readText = thisWeek.map((i) => `${formatWhen(i.when)} ${i.name}`).join('. ')

  function Row({ id, name, kind, when, lat, lon }: (typeof items)[number]) {
    return (
      <li className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4">
        <span className="text-3xl" aria-hidden>
          {FACILITY_KIND_ICON[kind] ?? '📍'}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xl font-bold">{name}</p>
          <p className="text-lg text-slate-600">{formatWhen(when)}</p>
        </div>
        <a href={directionsUrl(name, lat, lon)} target="_blank" rel="noreferrer" className="inline-flex min-h-12 items-center rounded-xl border border-slate-300 px-4 text-lg font-semibold">
          길찾기
        </a>
        <Button variant="ghost" size="lg" onClick={() => remove(id)} aria-label={`${name} 일정 지우기`}>
          지우기
        </Button>
      </li>
    )
  }

  return (
    <div className="space-y-4">
      <A11yBar textToRead={readText || undefined} />
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">이번 주 일정</h1>
        {items.length > 0 && (
          <Button variant="secondary" size="lg" onClick={() => downloadIcs(items)}>
            달력에 저장(.ics)
          </Button>
        )}
      </div>
      {items.length === 0 ? (
        <EmptyState
          title="저장한 일정이 없어요"
          description="갈 곳 카드에서 '일정 저장'을 누르면 여기에 모여요."
          action={
            <Link to="/citizen/places" className="text-lg font-semibold text-blue-700 underline">
              갈 곳 보기
            </Link>
          }
        />
      ) : (
        <>
          {thisWeek.length === 0 && <p className="text-lg text-slate-600">이번 주에는 잡힌 일정이 없어요.</p>}
          <ul className="space-y-3">{thisWeek.map((i) => <Row key={i.id} {...i} />)}</ul>
          {later.length > 0 && (
            <>
              <h2 className="pt-2 text-xl font-bold text-slate-700">다음에</h2>
              <ul className="space-y-3">{later.map((i) => <Row key={i.id} {...i} />)}</ul>
            </>
          )}
        </>
      )}
    </div>
  )
}
