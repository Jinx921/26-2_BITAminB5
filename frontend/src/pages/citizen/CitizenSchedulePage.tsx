import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CalendarArrowDown, ChevronLeft, Navigation, Trash2 } from 'lucide-react'
import { CitizenHeader } from '@/components/citizen/CitizenHeader'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/ui/EmptyState'
import { List, ListRow } from '@/components/ui/ListRow'
import { downloadIcs, formatWhen, isThisWeek, useSchedule } from '@/features/citizen/schedule'
import { directionsUrl } from '@/features/citizen/share'

/** 이번 주 일정 (기기에만 저장). 캘린더(.ics)로 내보낼 수 있다 */
export function CitizenSchedulePage() {
  const { items, remove } = useSchedule()
  const [now] = useState(() => new Date())
  const thisWeek = items.filter((i) => isThisWeek(i.when, now))
  const later = items.filter((i) => !isThisWeek(i.when, now) && new Date(i.when) > now)
  const readText = thisWeek.map((i) => `${formatWhen(i.when)} ${i.name}`).join('. ')

  const row = (i: (typeof items)[number]) => (
    <ListRow
      key={i.id}
      title={<span className="text-lg">{i.name}</span>}
      subtitle={<span className="text-base">{formatWhen(i.when)}</span>}
      trailing={
        <div className="flex items-center gap-1">
          <a href={directionsUrl(i.name, i.lat, i.lon)} target="_blank" rel="noreferrer" aria-label={`${i.name} 길찾기`} className="inline-flex size-11 items-center justify-center rounded-full text-green hover:bg-green-soft">
            <Navigation className="size-5" />
          </a>
          <button type="button" onClick={() => remove(i.id)} aria-label={`${i.name} 일정 지우기`} className="inline-flex size-11 items-center justify-center rounded-full text-ink-3 hover:bg-canvas">
            <Trash2 className="size-5" />
          </button>
        </div>
      }
    />
  )

  return (
    <div className="space-y-5">
      <CitizenHeader textToRead={readText || undefined} subtitle={<Link to="/citizen" className="inline-flex min-h-11 items-center gap-1 text-base text-ink-2"><ChevronLeft className="size-4" aria-hidden />물어보기로</Link>} />
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">이번 주 일정</h2>
        {items.length > 0 && (
          <Button variant="outline" size="sm" pill icon={<CalendarArrowDown className="size-4" />} onClick={() => downloadIcs(items)}>
            달력에 저장
          </Button>
        )}
      </div>
      {items.length === 0 ? (
        <EmptyState title="저장한 일정이 없어요" description="장소 카드에서 '일정 저장'을 누르면 여기에 모여요." action={<Link to="/citizen/places" className="font-semibold text-primary">갈 곳 보기</Link>} />
      ) : (
        <>
          {thisWeek.length === 0 ? <p className="text-base text-ink-3">이번 주에는 잡힌 일정이 없어요.</p> : <List>{thisWeek.map(row)}</List>}
          {later.length > 0 && (
            <>
              <h3 className="pt-2 text-base font-bold text-ink-3">다음에</h3>
              <List>{later.map(row)}</List>
            </>
          )}
        </>
      )}
    </div>
  )
}
